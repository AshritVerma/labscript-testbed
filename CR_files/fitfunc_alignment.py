# This code is designed for realigning AOD (Acousto-Optic Deflector) and SLM (Spatial Light Modulator) laser spots.
## fitfunc_realignment.py

###############################################################################
# IMPORTS AND SETUP
###############################################################################
import numpy as np
from scipy.ndimage import gaussian_filter, label, find_objects
from scipy.optimize import curve_fit
from scipy.ndimage.measurements import center_of_mass
import matplotlib.pyplot as plt
from PIL import Image
from scipy.spatial import distance
from sklearn.decomposition import PCA
import json
import os
import h5py
from pathlib import Path
from datetime import datetime
import shutil
import sys
import argparse

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Important conversion factors:
# 1 MHz : 1 µm
# 1 pixel : 3.45 µm

# Toggle for visualization output
SHOW_VISUALIZATIONS = True

# Add to global parameters section near the top
ALIGNMENT_ITERATIONS = 3  # Default number of iterations

###############################################################################
# HELPER FUNCTIONS
###############################################################################

# write_aod_params_to_json():
# - Takes AOD parameters and saves them to a JSON file
# - Used to store the updated alignment parameters

def write_aod_params_to_json(params):
    json_path = os.path.join(SCRIPT_DIR, 'updated_aod_params.json')
    print(f"[INFO] Writing AOD parameters to: {json_path}")
    with open(json_path, 'w') as f:
        json.dump(params, f, indent=4)

def write_previous_aod_params_to_json(params):
    """Save the parameters read from HDF5 to a JSON file for comparison"""
    json_path = os.path.join(SCRIPT_DIR, 'previous_aod_params.json')
    print(f"[INFO] Writing previous AOD parameters to: {json_path}")
    with open(json_path, 'w') as f:
        json.dump(params, f, indent=4)

def check_grid_spacing(pos1, pos2):
    """
    Verify that relative distances between spots are preserved during translation
    
    Args:
        pos1: Original AOD spot positions
        pos2: New AOD spot positions after translation
    """
    print("[INFO] Verifying grid spacing is preserved...")
    for i in range(len(pos1)-1):
        for j in range(i+1, len(pos1)):
            d1 = np.linalg.norm(pos1[i] - pos1[j])
            d2 = np.linalg.norm(pos2[i] - pos2[j])
            if abs(d1 - d2) > 1e-10:  # numerical precision threshold
                print(f"[WARN] Grid spacing changed between spots {i} and {j}")
                print(f"       Original distance: {d1:.3f}, New distance: {d2:.3f}")


###############################################################################
# SIMULATION FUNCTIONS 
###############################################################################

# generate_simulated_bmp():
# - Creates a synthetic BMP image with Gaussian spots representing laser beams
# - Takes parameters like:
#   * Image dimensions
#   * SLM and AOD spot positions 
#   * Spot amplitudes and sizes
#   * Noise level
# - Used to visualize expected results after alignment

def generate_simulated_bmp(
    filename,
    image_shape=(400, 400),
    slm_positions=None,  # List of (x,y) positions for SLM spots
    aod_positions=None,  # List of (x,y) positions for AOD spots
    slm_amplitude=100,   # Dimmer
    aod_amplitude=255,   # Brighter
    sigma=2.0,          # Spot size
    noise_level=1
):
    """Generate a synthetic BMP file with multiple Gaussian beams"""
    height, width = image_shape
    
    # Create black background
    image_array = np.zeros((height, width))
    
    # Coordinates for Gaussian calculation
    y = np.arange(height)
    x = np.arange(width)
    X, Y = np.meshgrid(x, y)
    
    # Add SLM spots (dimmer)
    for x_slm, y_slm in slm_positions:
        spot = slm_amplitude * np.exp(
            -(((X - x_slm)**2 + (Y - y_slm)**2) / (2 * sigma**2))
        )
        image_array += spot
    
    # Add AOD spots (brighter)
    for x_aod, y_aod in aod_positions:
        spot = aod_amplitude * np.exp(
            -(((X - x_aod)**2 + (Y - y_aod)**2) / (2 * sigma**2))
        )
        image_array += spot
    
    # Add minimal noise
    if noise_level > 0:
        image_array += noise_level * np.random.randn(height, width)
    
    # Normalize and convert to uint8
    image_array = np.clip(image_array, 0, 255)
    image_array_uint8 = image_array.astype(np.uint8)
    
    # Save as BMP
    img = Image.fromarray(image_array_uint8, mode='L')
    img.save(filename, format='BMP')
    print(f"[INFO] Saved simulated BMP to: {filename}")

def run_iterative_alignment(num_iterations=ALIGNMENT_ITERATIONS):
    """
    Run multiple iterations of alignment using simulated outputs as next inputs
    """
    print(f"\n[INFO] Starting iterative alignment sequence ({num_iterations} iterations)...")
    
    # Store history of alignments
    alignment_history = []
    
    # Initial setup - use original image first
    input_file_name = "6x6_rotated.bmp"
    current_image_path = os.path.join(SCRIPT_DIR, "test_images", input_file_name)
    
    # Try to get HDF5 path, use None if not available
    try:
        h5_path = get_latest_shot_path()
        current_params = read_previous_aod_params(h5_path)
    except:
        h5_path = None
        current_params = None
    
    if current_params is None:
        print("[WARN] Using default AOD params")
        current_params = {
            "X_OFFSET":  0.0,
            "X_MIN_AOD": 97.0,
            "X_MAX_AOD": 107.0,
            "Y_OFFSET":  0.0,
            "Y_MIN_AOD": 90.0,
            "Y_MAX_AOD": 100.0
        }
    
    for iteration in range(num_iterations):
        print(f"\n{'='*80}")
        print(f"Starting Iteration {iteration + 1}/{num_iterations}")
        print(f"{'='*80}")
        
        # Analyze current image
        aod_positions, slm_positions, params, full_image = find_and_separate_two_grids_intensity(
            current_image_path,
            spot_size=3,
            threshold=0.1,
            max_distance=2
        )
        
        # Calculate corrections
        center_slm = np.mean(slm_positions, axis=0)
        center_aod = np.mean(aod_positions, axis=0)
        dx_pixels = center_slm[0] - center_aod[0]
        dy_pixels = center_slm[1] - center_aod[1]
        
        dx_um = dx_pixels * 3.45
        dy_um = dy_pixels * 3.45
        dx_mhz = dx_um
        dy_mhz = dy_um
        
        # Update parameters
        new_params = current_params.copy()
        new_params["X_OFFSET"]  += dx_mhz
        new_params["X_MIN_AOD"] += dx_mhz
        new_params["X_MAX_AOD"] += dx_mhz
        new_params["Y_OFFSET"]  += dy_mhz
        new_params["Y_MIN_AOD"] += dy_mhz
        new_params["Y_MAX_AOD"] += dy_mhz
        
        # Save iteration results
        alignment_history.append({
            'iteration': iteration + 1,
            'dx_pixels': dx_pixels,
            'dy_pixels': dy_pixels,
            'total_offset': np.sqrt(dx_pixels**2 + dy_pixels**2),
            'params': new_params.copy()
        })
        
        # Generate simulated image for next iteration
        aod_positions_new = np.array(aod_positions) + [dx_pixels, dy_pixels]
        next_image_path = os.path.join(SCRIPT_DIR, f'simulated_iteration_{iteration + 1}.bmp')
        
        generate_simulated_bmp(
            filename=next_image_path,
            image_shape=full_image.shape,
            slm_positions=slm_positions,
            aod_positions=aod_positions_new,
            slm_amplitude=100,
            aod_amplitude=255,
            sigma=2.0,
            noise_level=1
        )
        
        # Save parameters
        write_aod_params_to_json(new_params)
        if h5_path is not None:
            h5_path = write_new_aod_params_to_h5(h5_path, new_params)
        
        # Show visualization after each iteration
        if SHOW_VISUALIZATIONS:
            print(f"\n[INFO] Displaying results for iteration {iteration + 1}...")
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
            
            # Original Image
            ax1.imshow(full_image, cmap='gray')
            # Plot SLM spots as circles
            for pos in slm_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='red', fill=False, linestyle='-')
                ax1.add_patch(circle)
            ax1.plot([], [], 'rx', label='SLM spots')
            
            # Plot AOD spots as circles
            for pos in aod_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='blue', fill=False, linestyle='-')
                ax1.add_patch(circle)
            ax1.plot([], [], 'bx', label='AOD spots')
            
            # Add correction vector to original image
            ax1.arrow(center_aod[0], center_aod[1], dx_pixels, dy_pixels,
                     color='green', width=0.5, head_width=5,
                     label='Correction Vector')
            
            ax1.set_title('Original Image')
            ax1.legend()

            # Simulated Next Shot
            simulated_image = Image.open(next_image_path)
            ax2.imshow(np.array(simulated_image), cmap='gray')
            # Plot SLM spots as circles
            for pos in slm_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='red', fill=False, linestyle='-')
                ax2.add_patch(circle)
            ax2.plot([], [], 'rx', label='SLM spots')
            
            # Plot AOD spots as circles
            for pos in aod_positions_new:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='blue', fill=False, linestyle='-')
                ax2.add_patch(circle)
            ax2.plot([], [], 'bx', label='AOD spots')
            
            # Add correction vector to simulated image
            ax2.arrow(center_aod[0], center_aod[1], dx_pixels, dy_pixels,
                     color='green', width=0.5, head_width=5,
                     label='Applied Correction')
            
            ax2.set_title('Simulated Next Shot\n(After applying new AOD params)')
            ax2.legend()

            plt.tight_layout()
            plt.show()
        
        # Update for next iteration
        current_image_path = next_image_path
        current_params = new_params
        
        # Print progress
        print(f"\n[INFO] Iteration {iteration + 1} complete")
        print(f"Total offset: {alignment_history[-1]['total_offset']:.2f} pixels")
    
    # Print final results
    print("\nAlignment History:")
    print("-----------------")
    for entry in alignment_history:
        print(f"Iteration {entry['iteration']}:")
        print(f"  Offset: {entry['total_offset']:.2f} pixels")
        print(f"  dx: {entry['dx_pixels']:.2f}, dy: {entry['dy_pixels']:.2f}")
    
    return alignment_history

###############################################################################
# SPOT ANALYSIS FUNCTIONS
###############################################################################

# two_gaussian_2d():
# - Mathematical model for fitting two overlapping 2D Gaussian functions
# - Used to precisely locate spot centers when they may be close together

def two_gaussian_2d(xy, amplitude1, xo1, yo1, sigma_x1, sigma_y1,
                    amplitude2, xo2, yo2, sigma_x2, sigma_y2, offset):
    """
    A 2D model of two Gaussians plus an offset.
    """
    x, y = xy
    xo1 = float(xo1)
    yo1 = float(yo1)
    xo2 = float(xo2)
    yo2 = float(yo2)
    
    g1 = amplitude1 * np.exp(
        -(((x - xo1)**2)/(2*sigma_x1**2) + ((y - yo1)**2)/(2*sigma_y1**2))
    )
    g2 = amplitude2 * np.exp(
        -(((x - xo2)**2)/(2*sigma_x2**2) + ((y - yo2)**2)/(2*sigma_y2**2))
    )
    return (g1 + g2 + offset).ravel()

# find_and_separate_two_grids_intensity():
# - Main analysis function that:
#   1. Loads and processes the BMP image
#   2. Finds spots using thresholding and labeling
#   3. Fits Gaussian functions to each spot
#   4. Separates spots into AOD vs SLM grids based on intensity
#   5. Returns positions and parameters

def find_and_separate_two_grids_intensity(image_path, spot_size=3, threshold=0.1, max_distance=2):
    """Main analysis function for finding and separating spots"""
    print("\n[INFO] Starting spot analysis...")
    print("[INFO] Loading image:", image_path)
    image = Image.open(image_path).convert('L')
    image_array = np.array(image)

    print("[INFO] Applying Gaussian filter...")
    smoothed_image = gaussian_filter(image_array, sigma=spot_size / 2)
    threshold_value = smoothed_image.max() * threshold
    binary_image = smoothed_image > threshold_value

    print("[INFO] Finding objects above threshold...")
    labeled_image, num_features = label(binary_image)
    objects = find_objects(labeled_image)
    print(f"[INFO] Found {len(objects)} potential spots")

    aod_positions = []  # Brighter spots (was grid1_positions)
    slm_positions = []  # Dimmer spots (was grid2_positions)
    all_positions = []
    all_intensities = []
    gaussian_params = []

    print("\n[INFO] Processing spots...")
    total_objects = len(objects)
    for i, obj_slice in enumerate(objects):
        # Update progress every spot
        progress = (i + 1) / total_objects * 100
        print(f"\r[PROGRESS] Processing spot {i+1}/{total_objects} ({progress:.1f}%)", end="")
        
        # Get sub-image around the spot with padding
        y_min, y_max = max(0, obj_slice[0].start - 10), min(image_array.shape[0], obj_slice[0].stop + 10)
        x_min, x_max = max(0, obj_slice[1].start - 10), min(image_array.shape[1], obj_slice[1].stop + 10)
        sub_image = image_array[y_min:y_max, x_min:x_max]
        
        # Create coordinate meshgrid
        y, x = np.mgrid[y_min:y_max, x_min:x_max]
        
        # Initial guesses based on center of mass
        com_y, com_x = center_of_mass(sub_image)
        com_x += x_min  # Adjust for sub-image offset
        com_y += y_min
        
        # Make sure initial guesses are within bounds
        amplitude1_guess = float(np.max(sub_image))
        amplitude2_guess = amplitude1_guess * 0.5
        sigma_guess = 2.0
        offset_guess = float(np.min(sub_image))
        
        initial_guess = [
            amplitude1_guess, com_x, com_y, sigma_guess, sigma_guess,
            amplitude2_guess, com_x + 2, com_y + 2, sigma_guess, sigma_guess,
            offset_guess
        ]
        
        # Define bounds
        lower_bounds = [
            0, x_min, y_min, 0.1, 0.1,
            0, x_min, y_min, 0.1, 0.1,
            0
        ]
        
        upper_bounds = [
            float(np.max(sub_image)) * 2, x_max, y_max, 10, 10,
            float(np.max(sub_image)) * 2, x_max, y_max, 10, 10,
            float(np.max(sub_image))
        ]

        try:
            popt, _ = curve_fit(
                two_gaussian_2d, 
                (x.ravel(), y.ravel()), 
                sub_image.ravel(),
                p0=initial_guess,
                bounds=(lower_bounds, upper_bounds)
            )
            gaussian_params.append(popt)

            pos1 = (popt[1], popt[2])
            pos2 = (popt[6], popt[7])
            intensity1 = popt[0]
            intensity2 = popt[5]

            # Sort by amplitude: stronger -> grid1, weaker -> grid2
            if intensity1 > intensity2:
                aod_positions.append(pos1)
                slm_positions.append(pos2)
            else:
                aod_positions.append(pos2)
                slm_positions.append(pos1)

            all_positions.append(pos1)
            all_positions.append(pos2)
            all_intensities.append(intensity1)
            all_intensities.append(intensity2)

        except RuntimeError:
            # If fit fails, skip
            continue

    all_positions = np.array(all_positions)
    all_intensities = np.array(all_intensities).reshape(-1, 1)

    if len(aod_positions) == 0 or len(slm_positions) == 0:
        print("[WARN] Could not find any or enough spots to separate properly.")
        return aod_positions, slm_positions, gaussian_params, image_array

    # Determine bounding box around all detected spots
    all_grid_positions = np.vstack([aod_positions, slm_positions])
    x_min_crop = int(np.min(all_grid_positions[:, 0])) - 20
    x_max_crop = int(np.max(all_grid_positions[:, 0])) + 20
    y_min_crop = int(np.min(all_grid_positions[:, 1])) - 20
    y_max_crop = int(np.max(all_grid_positions[:, 1])) + 20

    x_min_crop = max(0, x_min_crop)
    y_min_crop = max(0, y_min_crop)
    x_max_crop = min(image_array.shape[1], x_max_crop)
    y_max_crop = min(image_array.shape[0], y_max_crop)

    # Crop
    cropped_image = image_array[y_min_crop:y_max_crop, x_min_crop:x_max_crop]

    # Shift positions for plotting
    aod_shifted = np.array(aod_positions) - [x_min_crop, y_min_crop]
    slm_shifted = np.array(slm_positions) - [x_min_crop, y_min_crop]

    # Plot only if visualizations are enabled
    if SHOW_VISUALIZATIONS:
        plt.figure(figsize=(8, 8))
        plt.imshow(cropped_image, cmap='gray', origin='upper')
        plt.scatter(aod_shifted[:, 0], aod_shifted[:, 1], color='red', label='AOD spots (Brighter)')
        plt.scatter(slm_shifted[:, 0], slm_shifted[:, 1], color='blue', label='SLM spots (Dimmer)')
        plt.title('Detected Laser Spots on Cropped Image')
        plt.legend()
        plt.show()

    print("\n\n[INFO] Spot processing complete!")
    print(f"[INFO] Found {len(aod_positions)} AOD spots (Brighter)")
    print(f"[INFO] Found {len(slm_positions)} SLM spots (Dimmer)")

    return aod_positions, slm_positions, gaussian_params, image_array


###############################################################################
# GRID ANALYSIS FUNCTIONS
###############################################################################

# calculate_grid_angle():
# - Uses PCA to find the principal axis of a grid of spots
# - Returns the angle in degrees

def calculate_grid_angle(positions):
    pca = PCA(n_components=2)
    pca.fit(positions)
    pc1 = pca.components_[0]
    angle = np.arctan2(pc1[1], pc1[0])  # radians
    return np.degrees(angle)

# calculate_grid_feedback():
# - Compares positions and angles between two grids
# - Returns feedback parameters for alignment

def calculate_grid_feedback(grid1_positions, grid2_positions, x_min_freq, x_max_freq, y_min_freq, y_max_freq):
    grid1_positions = np.array(grid1_positions)
    grid2_positions = np.array(grid2_positions)
    
    angle_grid1 = calculate_grid_angle(grid1_positions)
    angle_grid2 = calculate_grid_angle(grid2_positions)
    
    relative_angle = angle_grid2 - angle_grid1  # degrees
    feedback = {
        "x_min_freq_feedback": np.min(grid2_positions[:, 0]) - np.min(grid1_positions[:, 0]),
        "x_max_freq_feedback": np.max(grid2_positions[:, 0]) - np.max(grid1_positions[:, 0]),
        "y_min_freq_feedback": np.min(grid2_positions[:, 1]) - np.min(grid1_positions[:, 1]),
        "y_max_freq_feedback": np.max(grid2_positions[:, 1]) - np.max(grid1_positions[:, 1]),
        "rotation_angle_feedback": relative_angle
    }
    return feedback, relative_angle


###############################################################################
# FILE HANDLING FUNCTIONS
###############################################################################

# get_latest_shot_path():
# - Finds the most recent HDF5 file in the specified directory

def get_latest_shot_path():
    """Get the most recent HDF5 file"""
    h5_dir = Path(r"C:\Users\cleve\labscript-suite\CR_files\hdf5")
    # Look for any .h5 files
    h5_files = sorted(h5_dir.glob("*.h5"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not h5_files:
        raise FileNotFoundError("No HDF5 files found in directory")
    latest_file = str(h5_files[0])
    print(f"[INFO] Using most recent HDF5 file: {latest_file}")
    return latest_file

# read_previous_aod_params():
# - Extracts AOD parameters from an HDF5 file

def read_previous_aod_params(h5_path):
    """Read AOD parameters from previous shot's HDF5 file"""
    with h5py.File(h5_path, 'r') as f:
        try:
            params = {
                "X_OFFSET": float(f['globals']['Resorting_params']['X_OFFSET'][()]),
                "X_MIN_AOD": float(f['globals']['Resorting_params']['X_MIN_AOD'][()]),
                "X_MAX_AOD": float(f['globals']['Resorting_params']['X_MAX_AOD'][()]),
                "Y_OFFSET": float(f['globals']['Resorting_params']['Y_OFFSET'][()]),
                "Y_MIN_AOD": float(f['globals']['Resorting_params']['Y_MIN_AOD'][()]),
                "Y_MAX_AOD": float(f['globals']['Resorting_params']['Y_MAX_AOD'][()])
            }
            return params
        except KeyError as e:
            print(f"[ERROR] Could not find AOD parameters in HDF5: {e}")
            return None

# write_new_aod_params_to_h5():
# - Creates a new HDF5 file with updated parameters
# - Maintains version history by incrementing run numbers

def write_new_aod_params_to_h5(old_h5_path, new_params):
    """Write new AOD parameters to a new HDF5 file with incremented run number"""
    # Parse the old filename to get run number
    old_path = Path(old_h5_path)
    if "AOD_alignment_" in old_path.name:
        try:
            run_num = int(old_path.stem.split('_')[-1]) + 1
        except ValueError:
            run_num = 1
    else:
        run_num = 1

    # Create new filename with incremented run number
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"AOD_alignment_{timestamp}_run{run_num:03d}.h5"
    new_h5_path = old_path.parent / new_filename

    # Copy the old file to new file
    shutil.copy2(old_h5_path, new_h5_path)

    # Update parameters in new file
    with h5py.File(new_h5_path, 'r+') as f:
        try:
            # Create Resorting_params group if it doesn't exist
            if 'globals/Resorting_params' not in f:
                globals_group = f.require_group('globals')
                params_group = globals_group.create_group('Resorting_params')
            else:
                params_group = f['globals/Resorting_params']

            # Write new parameters
            for key, value in new_params.items():
                if key in params_group:
                    params_group[key][()] = value
                else:
                    params_group.create_dataset(key, data=value)

            # Add metadata about the alignment run
            params_group.attrs['alignment_timestamp'] = timestamp
            params_group.attrs['previous_h5_file'] = old_path.name
            params_group.attrs['run_number'] = run_num

            f.flush()
            print(f"[INFO] Successfully created new HDF5 with updated parameters: {new_h5_path}")
        except Exception as e:
            print(f"[ERROR] Could not write AOD parameters to new HDF5: {e}")
            raise

###############################################################################
# MAIN EXECUTION
###############################################################################

# The main block:
# 1. Analyzes a BMP image to find SLM and AOD spot positions
# 2. Reads previous AOD parameters from HDF5
# 3. Calculates required frequency shifts to align spots
# 4. Updates parameters and saves to both JSON and HDF5
# 5. Generates a simulated preview of the next shot
# 6. Creates visualization plots

if __name__ == "__main__":
    print("\n[INFO] Starting AOD-SLM alignment analysis...")
    
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='AOD-SLM Alignment Tool')
    parser.add_argument('--iters', type=int, default=1,
                      help='Number of alignment iterations (default: 1)')
    parser.add_argument('--visuals', type=str, choices=['on', 'off'], default='on',
                      help='Enable or disable visualizations (default: on)')
    
    args = parser.parse_args()
    
    # Set visualization flag based on argument
    SHOW_VISUALIZATIONS = (args.visuals.lower() == 'on')
    
    if args.iters > 1:
        print(f"[INFO] Running {args.iters} iterations with visuals {args.visuals}")
        alignment_history = run_iterative_alignment(args.iters)
    else:
        # Single iteration code
        print("[INFO] Running single iteration...")
        
        # 1) Analyze BMP
        input_file_name = "6x6.bmp"
        image_path = os.path.join(SCRIPT_DIR, "test_images", input_file_name)
        
        if not os.path.exists(image_path):
            print(f"\n[ERROR] Image file not found: {image_path}")
            print("[INFO] Please ensure the image exists in the correct location.")
            sys.exit(1)
        
        aod_positions, slm_positions, params, full_image = find_and_separate_two_grids_intensity(
            image_path, 
            spot_size=3,
            threshold=0.1,
            max_distance=2
        )

        # 2) Get previous AOD params
        try:
            h5_path = get_latest_shot_path()
            old_aod_params = read_previous_aod_params(h5_path)
        except:
            h5_path = None
            old_aod_params = None
        
        if old_aod_params is None:
            print("[WARN] Using default AOD params")
            old_aod_params = {
                "X_OFFSET":  0.0,
                "X_MIN_AOD": 97.0,
                "X_MAX_AOD": 107.0,
                "Y_OFFSET":  0.0,
                "Y_MIN_AOD": 90.0,
                "Y_MAX_AOD": 100.0
            }
        
        # 3) Calculate offsets
        center_slm = np.mean(slm_positions, axis=0)
        center_aod = np.mean(aod_positions, axis=0)
        dx_pixels = center_slm[0] - center_aod[0]
        dy_pixels = center_slm[1] - center_aod[1]

        dx_um = dx_pixels * 3.45
        dy_um = dy_pixels * 3.45
        dx_mhz = dx_um
        dy_mhz = dy_um

        # 4) Update parameters
        new_aod_params = old_aod_params.copy()
        new_aod_params["X_OFFSET"]  += dx_mhz
        new_aod_params["X_MIN_AOD"] += dx_mhz
        new_aod_params["X_MAX_AOD"] += dx_mhz
        new_aod_params["Y_OFFSET"]  += dy_mhz
        new_aod_params["Y_MIN_AOD"] += dy_mhz
        new_aod_params["Y_MAX_AOD"] += dy_mhz

        write_aod_params_to_json(new_aod_params)
        if h5_path is not None:
            write_new_aod_params_to_h5(h5_path, new_aod_params)

        # 5) Generate simulation if visualizations are enabled
        if SHOW_VISUALIZATIONS:
            aod_positions_new = np.array(aod_positions) + [dx_pixels, dy_pixels]
            simulated_bmp_path = os.path.join(SCRIPT_DIR, 'simulated_next_shot.bmp')
            
            generate_simulated_bmp(
                filename=simulated_bmp_path,
                image_shape=full_image.shape,
                slm_positions=slm_positions,
                aod_positions=aod_positions_new,
                slm_amplitude=100,
                aod_amplitude=255,
                sigma=2.0,
                noise_level=1
            )

            # Create visualization
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
            
            # Original Image
            ax1.imshow(full_image, cmap='gray')
            for pos in slm_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='red', fill=False, linestyle='-')
                ax1.add_patch(circle)
            ax1.plot([], [], 'rx', label='SLM spots')
            
            for pos in aod_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='blue', fill=False, linestyle='-')
                ax1.add_patch(circle)
            ax1.plot([], [], 'bx', label='AOD spots')
            
            # Add correction vector
            ax1.arrow(center_aod[0], center_aod[1], dx_pixels, dy_pixels,
                     color='green', width=0.5, head_width=5,
                     label='Correction Vector')
            
            ax1.set_title('Original Image')
            ax1.legend()

            # Simulated Next Shot
            simulated_image = Image.open(simulated_bmp_path)
            ax2.imshow(np.array(simulated_image), cmap='gray')
            
            for pos in slm_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='red', fill=False, linestyle='-')
                ax2.add_patch(circle)
            ax2.plot([], [], 'rx', label='SLM spots')
            
            for pos in aod_positions_new:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='blue', fill=False, linestyle='-')
                ax2.add_patch(circle)
            ax2.plot([], [], 'bx', label='AOD spots')
            
            # Add correction vector
            ax2.arrow(center_aod[0], center_aod[1], dx_pixels, dy_pixels,
                     color='green', width=0.5, head_width=5,
                     label='Applied Correction')
            
            ax2.set_title('Simulated Next Shot\n(After applying new AOD params)')
            ax2.legend()

            plt.tight_layout()
            plt.show()


