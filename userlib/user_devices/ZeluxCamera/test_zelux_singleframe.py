import os
import time
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
from thorlabs_tsi_sdk.tl_camera import ROI
from thorlabs_tsi_sdk.tl_camera_enums import OPERATION_MODE, TRIGGER_POLARITY
import numpy as np
from PIL import Image
import sys
import cv2

def save_image(image_data, filename):
    """Save the image data as a PNG file."""
    image = Image.fromarray(image_data)
    image.save(filename)

def test_roi_and_image_size(camera):
    print("Testing ROI and image size...")
    roi_range = camera.roi_range
    print(f"ROI range: {roi_range}")

    # Calculate a valid ROI that's roughly half the sensor size
    new_roi = ROI(
        upper_left_x_pixels=0,
        upper_left_y_pixels=0,
        lower_right_x_pixels=((camera.sensor_width_pixels // 2) // 4) * 4,
        lower_right_y_pixels=((camera.sensor_height_pixels // 2) // 4) * 4
    )

    # Ensure the new ROI is within the allowed range
    new_roi = ROI(
        upper_left_x_pixels=max(new_roi.upper_left_x_pixels, roi_range.upper_left_x_pixels_min),
        upper_left_y_pixels=max(new_roi.upper_left_y_pixels, roi_range.upper_left_y_pixels_min),
        lower_right_x_pixels=min(new_roi.lower_right_x_pixels, roi_range.lower_right_x_pixels_max),
        lower_right_y_pixels=min(new_roi.lower_right_y_pixels, roi_range.lower_right_y_pixels_max)
    )

    print(f"Setting ROI to: {new_roi}")
    camera.roi = new_roi

    # Verify that the ROI was set correctly
    actual_roi = camera.roi
    print(f"Actual ROI: {actual_roi}")

    if actual_roi == new_roi:
        print("ROI set successfully!")
    else:
        print("Warning: ROI not set exactly as expected.")
        print(f"Expected: {new_roi}")
        print(f"Actual: {actual_roi}")

    # Print the new image size based on the ROI
    print(f"New image size: {camera.image_width_pixels}x{camera.image_height_pixels}")

    # Print pixel size information
    print(f"Sensor pixel size: {camera.sensor_pixel_width_um}um x {camera.sensor_pixel_height_um}um")

    # Test taking an image with the new ROI
    print("Capturing image with new ROI...")
    camera.exposure_time_us = 50000  # 50 ms exposure
    camera.frames_per_trigger_zero_for_unlimited = 1
    
    # Check and set operation mode
    current_mode = camera.operation_mode
    print(f"Current operation mode: {current_mode}")
    if current_mode != OPERATION_MODE.SOFTWARE_TRIGGERED:
        print("Setting operation mode to SOFTWARE_TRIGGERED")
        camera.operation_mode = OPERATION_MODE.SOFTWARE_TRIGGERED
    else:
        print("Operation mode is already set to SOFTWARE_TRIGGERED")

    try:
        camera.arm(2)
        print("Camera armed successfully")
        
        camera.issue_software_trigger()
        print("Software trigger issued")

        timeout_ms = 1000
        start_time = time.time()
        while (time.time() - start_time) * 1000 < timeout_ms:
            frame = camera.get_pending_frame_or_null()
            if frame is not None:
                print(f"Frame #{frame.frame_count} received!")
                print(f"Frame dimensions: {frame.image_buffer.shape}")
                return
            time.sleep(0.01)  # Short sleep to prevent busy-waiting

        print("Timeout: Failed to capture frame within the specified time")
    except Exception as e:
        print(f"An error occurred during frame capture: {str(e)}")
    finally:
        camera.disarm()
        print("Camera disarmed")


def configure_path():
    # Full path to the DLL
    dll_path = r"C:\Program Files\Thorlabs\Scientific Imaging\ThorCam"
    
    # Add the DLL path to the system PATH
    os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']

    try:
        # Python 3.8 introduces a new method to specify dll directory
        os.add_dll_directory(dll_path)
    except AttributeError:
        pass

def change_exposure_time(camera, exposure_time_us):
    """Change the exposure time of the camera."""
    camera.exposure_time_us = exposure_time_us

def change_image_size(camera, image_width_pixels, image_height_pixels):
    """Change the image size of the camera."""
    camera.image_width_pixels = image_width_pixels
    camera.image_height_pixels = image_height_pixels
    
def comprehensive_camera_test(camera):
    print("\n--- Comprehensive Camera Test ---\n")

    # 1. Basic Camera Information
    print(f"Camera Model: {camera.model}")
    print(f"Camera Serial Number: {camera.serial_number}")
    print(f"Firmware Version: {camera.firmware_version}")

    # 2. Sensor Information
    print(f"\nSensor Type: {camera.camera_sensor_type}")
    print(f"Sensor Width: {camera.sensor_width_pixels} pixels")
    print(f"Sensor Height: {camera.sensor_height_pixels} pixels")
    print(f"Sensor Pixel Size: {camera.sensor_pixel_width_um}um x {camera.sensor_pixel_height_um}um")
    print(f"Bit Depth: {camera.bit_depth}")

    # 3. ROI Test
    print("\n--- ROI Test ---")
    roi_range = camera.roi_range
    print(f"ROI Range: {roi_range}")
    print(f"Current ROI: {camera.roi}")
    print(f"Current image size: {camera.image_width_pixels}x{camera.image_height_pixels}")

    # 4. Exposure Settings
    print("\n--- Exposure Settings ---")
    print(f"Exposure Time Range: {camera.exposure_time_range_us}")
    print(f"Current exposure: {camera.exposure_time_us} us")

    # 5. Gain Settings
    print("\n--- Gain Settings ---")
    if hasattr(camera, 'gain_range'):
        print(f"Gain Range: {camera.gain_range}")
        print(f"Current gain: {camera.gain}")
    else:
        print("Gain setting not supported by this camera model.")

    # 6. Frame Rate Control
    print("\n--- Frame Rate Control ---")
    if hasattr(camera, 'is_frame_rate_control_enabled'):
        print(f"Frame Rate Control Enabled: {camera.is_frame_rate_control_enabled}")
        if camera.is_frame_rate_control_enabled:
            print(f"Frame Rate Range: {camera.frame_rate_control_value_range}")
            print(f"Current Frame Rate: {camera.frame_rate_control_value}")
    else:
        print("Frame rate control not supported by this camera model.")

    # 7. Triggering
    print("\n--- Triggering Settings ---")
    print(f"Current Operation Mode: {camera.operation_mode}")
    
    if hasattr(camera, 'TRIGGER_POLARITY'):
        print(f"Trigger Polarity: {camera.TRIGGER_POLARITY}")

    # 8. Image Capture Test
    print("\n--- Image Capture Test ---")
    camera.frames_per_trigger_zero_for_unlimited = 1
    try:
        camera.arm(2)
        print("Camera armed successfully")
        
        camera.issue_software_trigger()
        print("Software trigger issued")

        timeout_ms = 1000
        start_time = time.time()
        while (time.time() - start_time) * 1000 < timeout_ms:
            frame = camera.get_pending_frame_or_null()
            if frame is not None:
                print(f"Frame #{frame.frame_count} received!")
                print(f"Frame dimensions: {frame.image_buffer.shape}")
                break
            time.sleep(0.01)
        else:
            print("Timeout: Failed to capture frame within the specified time")
    except Exception as e:
        print(f"An error occurred during frame capture: {str(e)}")
    finally:
        camera.disarm()
        print("Camera disarmed")

def main():
    configure_path()
    
    serial_number = "18666"  # Make sure this is a string
    
    # Initialize the SDK
    with TLCameraSDK() as sdk:
        # Discover available cameras
        available_cameras = sdk.discover_available_cameras()
        if not available_cameras:
            print("No cameras found!")
            return
        
        print(f"Available cameras: {available_cameras}")
        
        # Open the camera with the specified serial number
        with sdk.open_camera(serial_number) as camera:
            print(f"Connected to camera. Serial number: {camera.serial_number}")
            
            # 1. Test changing exposure time
            print("\n--- Testing Exposure Time ---")
            original_exposure = camera.exposure_time_us
            test_exposure = 20000  # 20 ms
            camera.exposure_time_us = test_exposure
            if camera.exposure_time_us != test_exposure:
                print(f"Warning: Exposure time set to {camera.exposure_time_us} us instead of {test_exposure} us")
            print(f"Exposure time set to {camera.exposure_time_us} us")
            
            # 2. Test ROI and image size
            print("\n--- Testing ROI and Image Size ---")
            test_roi_and_image_size(camera)
            
            # 3. Capture a test image
            print("\n--- Capturing Test Image ---")
            camera.exposure_time_us = 10000  # set exposure to 10 ms
            camera.frames_per_trigger_zero_for_unlimited = 0  # start camera in continuous mode
            camera.image_poll_timeout_ms = 1000  # 1 second polling timeout
            
            camera.arm(2)
            
            # Skip the first frame
            print("Skipping first frame...")
            camera.issue_software_trigger()
            _ = camera.get_pending_frame_or_null()
            
            # Capture the second frame
            print("Capturing second frame...")
            camera.issue_software_trigger()
            frame = camera.get_pending_frame_or_null()
            
            if frame is not None:
                print(f"Frame #{frame.frame_count} received!")
                image_buffer_copy = np.copy(frame.image_buffer)
                numpy_shaped_image = image_buffer_copy.reshape(camera.image_height_pixels, camera.image_width_pixels)
                
                # Normalize the image to 0-255 range
                numpy_shaped_image = cv2.normalize(numpy_shaped_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                
                # Create a 3-channel image
                nd_image_array = cv2.cvtColor(numpy_shaped_image, cv2.COLOR_GRAY2BGR)
                
                cv2.imshow("Image From TSI Cam", nd_image_array)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                
                # Save the image
                save_image(numpy_shaped_image, "captured_image.png")
                print("Image saved as 'captured_image.png'")
            else:
                print("Unable to acquire image")
            
            camera.disarm()
            
            # 4. Run comprehensive camera test
            print("\n--- Running Comprehensive Camera Test ---")
            comprehensive_camera_test(camera)
            
            # 5. Restore original settings
            print("\n--- Restoring Original Settings ---")
            camera.exposure_time_us = original_exposure
            print(f"Exposure time restored to {camera.exposure_time_us} us")


            # Correctly reset ROI to full sensor
            try:
                full_roi = ROI(
                    upper_left_x_pixels=0,
                    upper_left_y_pixels=0,
                    lower_right_x_pixels=camera.sensor_width_pixels,
                    lower_right_y_pixels=camera.sensor_height_pixels
                )
                camera.roi = full_roi
                print(f"ROI reset to full sensor: {camera.roi}")
            except Exception as e:
                print(f"Failed to reset ROI: {str(e)}")
                
    print("\nCamera testing completed.")

   
if __name__ == "__main__":
    main()