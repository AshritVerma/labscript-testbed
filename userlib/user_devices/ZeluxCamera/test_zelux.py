import os
import time
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, ROI
import numpy as np
from PIL import Image
import sys
import cv2

def save_image(image_data, filename):
    """Save the image data as a PNG file with proper normalization."""
    try:
        # Create directory if it doesn't exist
        save_dir = os.path.join(os.path.dirname(__file__), 'test_images')
        os.makedirs(save_dir, exist_ok=True)
        
        # Normalize to 0-255 range
        normalized = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Convert to BGR for display
        display_image = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
        
        # Save both raw and display versions
        full_path = os.path.join(save_dir, filename)
        np.save(f"{full_path}_raw.npy", image_data)  # Save raw data
        cv2.imwrite(f"{full_path}.png", display_image)  # Save viewable image
        
        return display_image
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        return None

def configure_path():
    """Configure the system path to include necessary DLLs."""
    dll_path = r"C:\Program Files\Thorlabs\Scientific Imaging\ThorCam"
    os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']
    try:
        os.add_dll_directory(dll_path)
    except AttributeError:
        pass

def test_exposure_series(camera, base_filename):
    """Test different exposure times."""
    exposure_times = [10000, 20000, 50000]  # microseconds
    images = []
    
    print("\nTesting exposure times...")
    for exp_time in exposure_times:
        try:
            camera.exposure_time_us = exp_time
            print(f"Set exposure time to {exp_time}us")
            
            camera.issue_software_trigger()
            frame = camera.get_pending_frame_or_null()
            
            if frame is not None:
                image_buffer = np.copy(frame.image_buffer)
                image = image_buffer.reshape(camera.image_height_pixels, camera.image_width_pixels)
                save_image(image, f"{base_filename}_exp_{exp_time}us")
                images.append(image)
                print(f"Captured image with {exp_time}us exposure")
            else:
                print(f"Failed to capture image at {exp_time}us exposure")
            
            time.sleep(0.1)  # Buffer between captures
        except Exception as e:
            print(f"Error during exposure test {exp_time}us: {str(e)}")
    
    return images

def test_roi_series(camera, base_filename):
    """Test different ROI settings."""
    roi_tests = [
        ROI(0, 0, 1280, 1024),  # Full frame
        ROI(320, 256, 960, 768),  # Center region
        ROI(0, 0, 640, 512),    # Top-left quarter
    ]
    
    images = []
    print("\nTesting ROI settings...")
    
    for roi in roi_tests:
        try:
            camera.roi = roi
            print(f"Set ROI to {roi}")
            
            camera.issue_software_trigger()
            frame = camera.get_pending_frame_or_null()
            
            if frame is not None:
                image_buffer = np.copy(frame.image_buffer)
                image = image_buffer.reshape(camera.image_height_pixels, camera.image_width_pixels)
                save_image(image, f"{base_filename}_roi_{roi.upper_left_x_pixels}_{roi.upper_left_y_pixels}_{roi.lower_right_x_pixels}_{roi.lower_right_y_pixels}")
                images.append(image)
                print(f"Captured image with ROI: {roi}")
            else:
                print(f"Failed to capture image with ROI: {roi}")
            
            time.sleep(0.1)  # Buffer between captures
        except Exception as e:
            print(f"Error during ROI test {roi}: {str(e)}")
    
    return images

def test_rapid_capture(camera, base_filename, num_frames=5):
    """Test rapid sequential capture."""
    images = []
    print(f"\nTesting rapid capture of {num_frames} frames...")
    
    try:
        camera.exposure_time_us = 10000  # Set to fast exposure
        camera.roi = ROI(0, 0, 1280, 1024)  # Reset to full frame
        
        for i in range(num_frames):
            camera.issue_software_trigger()
            frame = camera.get_pending_frame_or_null()
            
            if frame is not None:
                image_buffer = np.copy(frame.image_buffer)
                image = image_buffer.reshape(camera.image_height_pixels, camera.image_width_pixels)
                save_image(image, f"{base_filename}_rapid_{i}")
                images.append(image)
                print(f"Captured rapid frame {i+1}/{num_frames}")
            else:
                print(f"Failed to capture rapid frame {i+1}/{num_frames}")
            
            time.sleep(0.02)  # Minimal buffer between captures
    except Exception as e:
        print(f"Error during rapid capture: {str(e)}")
    
    return images

def main():
    configure_path()
    serial_number = "18666"
    
    print("Initializing camera test sequence...")
    
    try:
        with TLCameraSDK() as sdk:
            available_cameras = sdk.discover_available_cameras()
            if not available_cameras:
                print("No cameras found!")
                return
            
            print(f"Available cameras: {available_cameras}")
            
            with sdk.open_camera(serial_number) as camera:
                print(f"Connected to camera. Serial number: {camera.serial_number}")
                
                # Initial camera setup
                camera.frames_per_trigger_zero_for_unlimited = 0
                camera.image_poll_timeout_ms = 1000
                camera.arm(2)
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                base_filename = f"test_{timestamp}"
                
                # Run test series
                exposure_images = test_exposure_series(camera, base_filename)
                roi_images = test_roi_series(camera, base_filename)
                rapid_images = test_rapid_capture(camera, base_filename)
                
                camera.disarm()
                print("\nTest sequence completed successfully!")
                
    except Exception as e:
        print(f"Error during test sequence: {str(e)}")

if __name__ == "__main__":
    main()