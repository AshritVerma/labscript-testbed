"""
AOD_SLM_alignment.py

converting fitfunc_alignment.py functionality into a labscript sequence.
designed for realigning AOD (Acousto-Optic Deflector) and SLM (Spatial Light Modulator) laser spots for near-perfect overlapping

"""

import os
import sys
import json
import shutil
import argparse
import numpy as np
import h5py
import time
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import gaussian_filter, label, find_objects, center_of_mass
from scipy.optimize import curve_fit
from scipy.spatial import distance
from sklearn.decomposition import PCA
from labscript import start, stop, Camera
from labscriptlib.example_apparatus.connection_table import cxn_table
from user_devices.ZeluxCamera.labscript_devices import ZeluxCamera

###############################################################################
# GLOBAL SETTINGS AND CONVERSION FACTORS
###############################################################################
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1 pixel : 3.45 µm
PIXEL_TO_UM = 3.45

# Show plots inline or not
SHOW_VISUALIZATIONS = True

# Default alignment iterations
ALIGNMENT_ITERATIONS = 3

###############################################################################
# CAMERA SETTINGS
###############################################################################
CAMERA_SERIAL = "18666"  # Your Zelux camera serial number
EXPOSURE_TIME_US = 10000  # 10ms exposure time

###############################################################################
# HELPER FUNCTIONS
###############################################################################
def write_aod_params_to_json(params):
    """Write updated AOD parameters to JSON file."""
    json_path = os.path.join(SCRIPT_DIR, 'updated_aod_params.json')
    print(f"[INFO] Writing AOD parameters to: {json_path}")
    with open(json_path, 'w') as f:
        json.dump(params, f, indent=4)

def write_previous_aod_params_to_json(params):
    """Save older AOD parameters (read from HDF5) to a separate JSON for reference."""
    json_path = os.path.join(SCRIPT_DIR, 'previous_aod_params.json')
    print(f"[INFO] Writing previous AOD parameters to: {json_path}")
    with open(json_path, 'w') as f:
        json.dump(params, f, indent=4)

def check_grid_spacing(pos1, pos2):
    """
    Verify that relative distances between spots are preserved.
    """
    print("[INFO] Verifying grid spacing is preserved...")
    for i in range(len(pos1)-1):
        for j in range(i+1, len(pos1)):
            d1 = np.linalg.norm(pos1[i] - pos1[j])
            d2 = np.linalg.norm(pos2[i] - pos2[j])
            if abs(d1 - d2) > 1e-10:  
                print(f"[WARN] Grid spacing changed between spots {i} and {j}")
                print(f"       Original distance: {d1:.3f}, New distance: {d2:.3f}")


###############################################################################
# SPOT-FINDING AND FITTING
###############################################################################
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

def find_and_separate_two_grids_intensity(image_path, spot_size=3, threshold=0.1, max_distance=2):
    """
    Main analysis function for finding and separating AOD vs SLM spots
    by fitting double-Gaussians and splitting by amplitude (brighter vs dimmer).
    """
    print("\n[INFO] Starting spot analysis...")
    print("[INFO] Loading image:", image_path)
    image = Image.open(image_path).convert('L')
    image_array = np.array(image)

    # 1) Gaussian filter for smoothing
    print("[INFO] Applying Gaussian filter...")
    smoothed_image = gaussian_filter(image_array, sigma=spot_size / 2)
    threshold_value = smoothed_image.max() * threshold
    binary_image = smoothed_image > threshold_value

    # 2) Label/identify spots
    print("[INFO] Finding objects above threshold...")
    labeled_image, num_features = label(binary_image)
    objects = find_objects(labeled_image)
    print(f"[INFO] Found {len(objects)} potential spots")

    aod_positions = []  
    slm_positions = []  
    all_positions = []
    all_intensities = []
    gaussian_params = []

    print("\n[INFO] Processing spots...")
    total_objects = len(objects)
    for i, obj_slice in enumerate(objects):
        progress = (i + 1) / total_objects * 100
        print(f"\r[PROGRESS] Processing spot {i+1}/{total_objects} ({progress:.1f}%)", end="")

        # Sub-image around the spot (with padding)
        y_min, y_max = max(0, obj_slice[0].start - 10), min(image_array.shape[0], obj_slice[0].stop + 10)
        x_min, x_max = max(0, obj_slice[1].start - 10), min(image_array.shape[1], obj_slice[1].stop + 10)
        sub_image = image_array[y_min:y_max, x_min:x_max]
        
        # Meshgrid for curve_fit
        y, x = np.mgrid[y_min:y_max, x_min:x_max]

        # Initial guess
        com_y, com_x = center_of_mass(sub_image)
        com_x += x_min  
        com_y += y_min
        
        amplitude1_guess = float(np.max(sub_image))
        amplitude2_guess = amplitude1_guess * 0.5
        sigma_guess = 2.0
        offset_guess = float(np.min(sub_image))
        
        initial_guess = [
            amplitude1_guess, com_x, com_y, sigma_guess, sigma_guess,
            amplitude2_guess, com_x + 2, com_y + 2, sigma_guess, sigma_guess,
            offset_guess
        ]

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

        # 3) Fit two Gaussians
        try:
            popt, _ = curve_fit(
                two_gaussian_2d, 
                (x.ravel(), y.ravel()), 
                sub_image.ravel(),
                p0=initial_guess,
                bounds=(lower_bounds, upper_bounds)
            )
            gaussian_params.append(popt)

            pos1 = (popt[1], popt[2])  # (x, y)
            pos2 = (popt[6], popt[7])  # (x, y)
            intensity1 = popt[0]
            intensity2 = popt[5]

            # Sort by amplitude
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
        print("[WARN] Could not find enough spots to separate properly.")
        return aod_positions, slm_positions, gaussian_params, image_array

    # Crop around detected spots (optional)
    all_grid_positions = np.vstack([aod_positions, slm_positions])
    x_min_crop = int(np.min(all_grid_positions[:, 0])) - 20
    x_max_crop = int(np.max(all_grid_positions[:, 0])) + 20
    y_min_crop = int(np.min(all_grid_positions[:, 1])) - 20
    y_max_crop = int(np.max(all_grid_positions[:, 1])) + 20

    x_min_crop = max(0, x_min_crop)
    y_min_crop = max(0, y_min_crop)
    x_max_crop = min(image_array.shape[1], x_max_crop)
    y_max_crop = min(image_array.shape[0], y_max_crop)

    cropped_image = image_array[y_min_crop:y_max_crop, x_min_crop:x_max_crop]
    aod_shifted = np.array(aod_positions) - [x_min_crop, y_min_crop]
    slm_shifted = np.array(slm_positions) - [x_min_crop, y_min_crop]

    # Optional visualization
    if SHOW_VISUALIZATIONS:
        plt.figure(figsize=(8, 8))
        plt.imshow(cropped_image, cmap='gray', origin='upper')
        plt.scatter(aod_shifted[:, 0], aod_shifted[:, 1], color='red', label='AOD spots (Brighter)')
        plt.scatter(slm_shifted[:, 0], slm_shifted[:, 1], color='blue', label='SLM spots (Dimmer)')
        plt.title('Detected Laser Spots on Cropped Image')
        plt.legend()
        plt.show()

    print("\n[INFO] Spot processing complete!")
    print(f"[INFO] Found {len(aod_positions)} AOD spots (Brighter)")
    print(f"[INFO] Found {len(slm_positions)} SLM spots (Dimmer)")

    return aod_positions, slm_positions, gaussian_params, image_array


###############################################################################
# GRID AND ALIGNMENT FUNCTIONS
###############################################################################
def calculate_grid_angle(positions):
    """Use PCA to find principal axis of a grid of spots."""
    pca = PCA(n_components=2)
    pca.fit(positions)
    pc1 = pca.components_[0]
    angle = np.arctan2(pc1[1], pc1[0])  # radians
    return np.degrees(angle)

def calculate_grid_feedback(grid1_positions, grid2_positions, x_min_freq, x_max_freq, y_min_freq, y_max_freq):
    """
    Compare positions and angles between two grids for alignment feedback.
    """
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

def generate_simulated_bmp(
    filename,
    image_shape=(400, 400),
    slm_positions=None,
    aod_positions=None,
    slm_amplitude=100,
    aod_amplitude=255,
    sigma=2.0,
    noise_level=1
):
    """
    Create a synthetic BMP with Gaussian spots representing SLM and AOD.
    """
    height, width = image_shape
    
    # Create black background
    image_array = np.zeros((height, width))

    y = np.arange(height)
    x = np.arange(width)
    X, Y = np.meshgrid(x, y)

    if slm_positions is None: slm_positions = []
    if aod_positions is None: aod_positions = []

    # Add SLM spots (dimmer)
    for x_slm, y_slm in slm_positions:
        spot = slm_amplitude * np.exp(-(((X - x_slm)**2 + (Y - y_slm)**2) / (2 * sigma**2)))
        image_array += spot

    # Add AOD spots (brighter)
    for x_aod, y_aod in aod_positions:
        spot = aod_amplitude * np.exp(-(((X - x_aod)**2 + (Y - y_aod)**2) / (2 * sigma**2)))
        image_array += spot
    
    # Add some noise
    if noise_level > 0:
        image_array += noise_level * np.random.randn(height, width)

    # Clip and convert
    image_array = np.clip(image_array, 0, 255)
    image_array_uint8 = image_array.astype(np.uint8)

    img = Image.fromarray(image_array_uint8, mode='L')
    img.save(filename, format='BMP')
    print(f"[INFO] Saved simulated BMP to: {filename}")


###############################################################################
# HDF5 FILE HANDLING
###############################################################################
def get_latest_shot_path():
    """
    Get the most recent HDF5 file from a known directory.
    """
    h5_dir = Path(r"C:\Users\cleve\labscript-suite\CR_files\hdf5")
    h5_files = sorted(h5_dir.glob("*.h5"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not h5_files:
        raise FileNotFoundError("No HDF5 files found in directory")
    latest_file = str(h5_files[0])
    print(f"[INFO] Using most recent HDF5 file: {latest_file}")
    return latest_file

def read_previous_aod_params(h5_path):
    """Extract AOD parameters from an existing HDF5 file."""
    with h5py.File(h5_path, 'r') as f:
        try:
            params = {
                "X_OFFSET":  float(f['globals']['Resorting_params']['X_OFFSET'][()]),
                "X_MIN_AOD": float(f['globals']['Resorting_params']['X_MIN_AOD'][()]),
                "X_MAX_AOD": float(f['globals']['Resorting_params']['X_MAX_AOD'][()]),
                "Y_OFFSET":  float(f['globals']['Resorting_params']['Y_OFFSET'][()]),
                "Y_MIN_AOD": float(f['globals']['Resorting_params']['Y_MIN_AOD'][()]),
                "Y_MAX_AOD": float(f['globals']['Resorting_params']['Y_MAX_AOD'][()])
            }
            return params
        except KeyError as e:
            print(f"[ERROR] Could not find AOD parameters in HDF5: {e}")
            return None

"not needed since labscript does this automatically in runmanager"
"""
def write_new_aod_params_to_h5(old_h5_path, new_params):
 
    #Create a new HDF5 file with updated AOD parameters, incrementing run number.
    
    old_path = Path(old_h5_path)
    if "AOD_alignment_" in old_path.name:
        try:
            run_num = int(old_path.stem.split('_')[-1].replace('run','')) + 1
        except ValueError:
            run_num = 1
    else:
        run_num = 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"AOD_alignment_{timestamp}_run{run_num:03d}.h5"
    new_h5_path = old_path.parent / new_filename

    shutil.copy2(old_h5_path, new_h5_path)

    with h5py.File(new_h5_path, 'r+') as f:
        try:
            if 'globals/Resorting_params' not in f:
                globals_group = f.require_group('globals')
                params_group = globals_group.create_group('Resorting_params')
            else:
                params_group = f['globals/Resorting_params']

            for key, value in new_params.items():
                if key in params_group:
                    params_group[key][()] = value
                else:
                    params_group.create_dataset(key, data=value)

            params_group.attrs['alignment_timestamp'] = timestamp
            params_group.attrs['previous_h5_file'] = old_path.name
            params_group.attrs['run_number'] = run_num

            f.flush()
            print(f"[INFO] Successfully created new HDF5 with updated parameters: {new_h5_path}")
        except Exception as e:
            print(f"[ERROR] Could not write AOD parameters to new HDF5: {e}")
            raise

    return str(new_h5_path)
"""

###############################################################################
# ITERATIVE ALIGNMENT LOGIC
###############################################################################
"""not necessary anymore since can run same script multiple times. 
    this may still be useful since looping in one script is faster 
    than running multiple shots"""
def run_iterative_alignment(num_iterations=ALIGNMENT_ITERATIONS):
    """
    Run multiple iterations of alignment using simulated outputs as next inputs.
    """
    print(f"\n[INFO] Starting iterative alignment sequence ({num_iterations} iterations)...")
    alignment_history = []

    input_file_name = "6x6_rotated.bmp"
    current_image_path = os.path.join(SCRIPT_DIR, "test_images", input_file_name)
    
    # Try reading previous params from HDF5
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

        # 1) Analyze current image
        aod_positions, slm_positions, params, full_image = find_and_separate_two_grids_intensity(
            current_image_path,
            spot_size=3,
            threshold=0.1,
            max_distance=2
        )
        
        # 2) Calculate the offset
        center_slm = np.mean(slm_positions, axis=0)
        center_aod = np.mean(aod_positions, axis=0)
        dx_pixels = center_slm[0] - center_aod[0]
        dy_pixels = center_slm[1] - center_aod[1]

        dx_um = dx_pixels * PIXEL_TO_UM
        dy_um = dy_pixels * PIXEL_TO_UM
        dx_mhz = dx_um
        dy_mhz = dy_um
        
        # 3) Update parameters
        new_params = current_params.copy()
        new_params["X_OFFSET"]  += dx_mhz
        new_params["X_MIN_AOD"] += dx_mhz
        new_params["X_MAX_AOD"] += dx_mhz
        new_params["Y_OFFSET"]  += dy_mhz
        new_params["Y_MIN_AOD"] += dy_mhz
        new_params["Y_MAX_AOD"] += dy_mhz
        
        # Record iteration result
        alignment_history.append({
            'iteration': iteration + 1,
            'dx_pixels': dx_pixels,
            'dy_pixels': dy_pixels,
            'total_offset': np.sqrt(dx_pixels**2 + dy_pixels**2),
            'params': new_params.copy()
        })
        
        # 4) Generate next simulated image
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

        # 5) Save parameters
        write_aod_params_to_json(new_params)
        if h5_path is not None:
            h5_path = write_new_aod_params_to_h5(h5_path, new_params)

        # 6) Visualization
        if SHOW_VISUALIZATIONS:
            print(f"\n[INFO] Displaying results for iteration {iteration + 1}...")
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
            
            # Original
            ax1.imshow(full_image, cmap='gray')
            for pos in slm_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='red', fill=False, linestyle='-')
                ax1.add_patch(circle)
            ax1.plot([], [], 'rx', label='SLM spots')
            
            for pos in aod_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='blue', fill=False, linestyle='-')
                ax1.add_patch(circle)
            ax1.plot([], [], 'bx', label='AOD spots')

            ax1.arrow(
                center_aod[0], center_aod[1], dx_pixels, dy_pixels,
                color='green', width=0.5, head_width=5, label='Correction Vector'
            )
            ax1.set_title(f'Original Image (Iteration {iteration + 1})')
            ax1.legend()

            # Simulated Next
            simulated_image = Image.open(next_image_path)
            ax2.imshow(np.array(simulated_image), cmap='gray')
            
            for pos in slm_positions:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='red', fill=False, linestyle='-')
                ax2.add_patch(circle)
            ax2.plot([], [], 'rx', label='SLM spots')

            for pos in aod_positions_new:
                circle = plt.Circle((pos[0], pos[1]), radius=3, color='blue', fill=False, linestyle='-')
                ax2.add_patch(circle)
            ax2.plot([], [], 'bx', label='AOD spots')

            ax2.arrow(
                center_aod[0], center_aod[1], dx_pixels, dy_pixels,
                color='green', width=0.5, head_width=5, label='Applied Correction'
            )
            ax2.set_title('Simulated Next Shot\n(After applying new AOD params)')
            ax2.legend()

            plt.tight_layout()
            plt.show()

        # Prepare for next iteration
        current_image_path = next_image_path
        current_params = new_params
        print(f"\n[INFO] Iteration {iteration + 1} complete.")
        print(f"Total offset: {alignment_history[-1]['total_offset']:.2f} pixels")

    # Print final results
    print("\nAlignment History:")
    for entry in alignment_history:
        print(f"Iteration {entry['iteration']}: Offset={entry['total_offset']:.2f} px (dx={entry['dx_pixels']:.2f}, dy={entry['dy_pixels']:.2f})")

    return alignment_history


###############################################################################
# LABSCRIPT SEQUENCE
###############################################################################
if __name__ == '__main__':
    # Import connection table - this creates all device objects
    cxn_table()

    # Begin labscript sequence
    start()

    # Configure camera settings
    zelux_camera.exposure_time = EXPOSURE_TIME_US
    zelux_camera.continuous = False  # We want single-shot mode

    # Trigger camera to take image at t=1s
    t = 1.0
    zelux_camera.expose(t, 'alignment_shot', 'image')
    
    # End sequence
    t += EXPOSURE_TIME_US/1e6 + 0.1  # Add exposure time plus buffer
    stop(t)
