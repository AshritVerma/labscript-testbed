import os
import time
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
import numpy as np
from PIL import Image
import sys

def save_image(image_data, filename):
    """Save the image data as a PNG file."""
    # Normalize to 0-255 range
    normalized = ((image_data - image_data.min()) * (255.0 / (image_data.max() - image_data.min()))).astype(np.uint8)
    image = Image.fromarray(normalized)
    image.save(filename)
    return image

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
            
            # Set some camera parameters
            camera.exposure_time_us = 10000  # set exposure to 10 ms
            camera.frames_per_trigger_zero_for_unlimited = 0  # start camera in continuous mode
            camera.image_poll_timeout_ms = 1000  # 1 second polling timeout
            
            # Arm the camera
            camera.arm(2)
            
            # Capture an image
            camera.issue_software_trigger()
            frame = camera.get_pending_frame_or_null()
            
            if frame is not None:
                print(f"Frame #{frame.frame_count} received!")
                image_buffer_copy = np.copy(frame.image_buffer)
                numpy_shaped_image = image_buffer_copy.reshape(
                    camera.image_height_pixels, 
                    camera.image_width_pixels
                )
                
                # Save the image and get the PIL Image object
                image = save_image(numpy_shaped_image, "captured_image.png")
                print("Image saved as 'captured_image.png'")
                
                # Display the image using PIL
                image.show()
            else:
                print("Unable to acquire image, program exiting...")
            
            # Disarm the camera
            camera.disarm()

if __name__ == "__main__":
    main()