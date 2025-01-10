import numpy as np
import os
import cv2
import time
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, OPERATION_MODE

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

    with TLCameraSDK() as sdk:
        available_cameras = sdk.discover_available_cameras()
        if len(available_cameras) < 1:
            print("No cameras detected")
            return

        print(f"Available cameras: {available_cameras}")

        with sdk.open_camera(serial_number) as camera:
            print(f"Connected to camera. Serial number: {camera.serial_number}")

            camera.exposure_time_us = 10000  # set exposure to 10 ms
            camera.frames_per_trigger_zero_for_unlimited = 0  # start camera in continuous mode
            camera.image_poll_timeout_ms = 1000  # 1 second polling timeout
            camera.frame_rate_control_value = 10
            camera.is_frame_rate_control_enabled = True

            camera.arm(2)
            camera.issue_software_trigger()

            try:
                frame_count = 0
                while True:
                    frame = camera.get_pending_frame_or_null()
                    if frame is not None:
                        frame_count += 1
                        print(f"Frame #{frame_count} received!")
                        
                        image_buffer_copy = np.copy(frame.image_buffer)
                        numpy_shaped_image = image_buffer_copy.reshape(camera.image_height_pixels, camera.image_width_pixels)
                        
                        # Normalize the image to 0-255 range
                        numpy_shaped_image = cv2.normalize(numpy_shaped_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                        
                        # Create a 3-channel image
                        nd_image_array = cv2.cvtColor(numpy_shaped_image, cv2.COLOR_GRAY2BGR)
                        
                        cv2.imshow("Image From TSI Cam", nd_image_array)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    else:
                        print("Unable to acquire image, retrying...")
                        time.sleep(0.1)
            
            except KeyboardInterrupt:
                print("Loop terminated by user")
            
            finally:
                cv2.destroyAllWindows()
                camera.disarm()
                print("Camera disarmed")

    print("Program completed")

if __name__ == "__main__":
    main()