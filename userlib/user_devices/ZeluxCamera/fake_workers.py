from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraWorker
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCameraError
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK
import numpy as np
import sys
import os
import ctypes
import time
import threading
from labscript_utils import zprocess
import cv2
from PIL import Image

class ZeluxCameraWorker(IMAQdxCameraWorker):
    interface_class = TLCameraSDK
    
    @staticmethod
    def save_image(image_data, filename):
        """Save the image data as a PNG file on local dir as a test."""
        image = Image.fromarray(image_data)
        image.save(filename)

    
    def configure_path(self):
        dll_path = r"C:\Program Files\Thorlabs\Scientific Imaging\ThorCam"
        
        # Add the DLL path to the system PATH
        os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']
        try:
        # Python 3.8 introduces a new method to specify dll directory
            os.add_dll_directory(dll_path)
        except AttributeError:
            pass 


    def init(self):

        print(f"ZeluxCameraWorker init method called, so configuring path with sdk dlls")
        self.configure_path()

        try:
            
            self.sdk = TLCameraSDK()
            print("TLCameraSDK initialized successfully")
        except Exception as e:
            print(f"Error initializing TLCameraSDK: {e}")
            print(f"Current PATH: {os.environ['PATH']}")
            print(f"Python executable: {sys.executable}")
            print(f"Working directory: {os.getcwd()}")
            raise

        camera_list = self.sdk.discover_available_cameras()
        if len(camera_list) == 0:
            raise Exception("No Thorlabs cameras found")
        
        print(f"Available cameras: {camera_list}")

        try:
            #self.camera = self.sdk.open_camera(self.sdk.discover_available_cameras()[0])
            self.camera = self.sdk.open_camera(str(self.serial_number))
        except TLCameraError as e:
            print(f"Error opening camera: {e}")
            print("Available cameras:")
            for cam_serial in camera_list:
                print(f" - {cam_serial}")
            raise Exception(f"Could not open camera with serial number {self.serial_number}. Please check if the serial number is correct and the camera is connected.")

        print(f"Successfully opened camera with serial number: {self.serial_number}")

        try:
            # Set some camera parameters
            self.camera.exposure_time_us = 10000  # set exposure to 10 ms
            self.camera.frames_per_trigger_zero_for_unlimited = 0  # start camera in continuous mode
            self.camera.image_poll_timeout_ms = 1000  # 1 second polling timeout
            
            # Arm the camera
            self.camera.arm(2)
            
            #need to save image width and height for color processing
            self.image_width = self.camera.image_width_pixels
            self.image_height = self.camera.image_height_pixels

            self.continuous_thread = None
            self.stop_continuous_flag = threading.Event()

            # user defined exposure time attrs for testing and passing vars directly from workers script instead of cxn table
            acq_time_get_loc = 40
            acq_time_get_probe = 40
            

        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            raise

    def acquire(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"Attempting to acquire frame (attempt {attempt + 1}/{max_attempts})...")
                self.camera.issue_software_trigger()
                frame = self.camera.get_pending_frame_or_null()
                if frame is not None:
                    print(f"Frame #{frame.frame_count} received!")
                    image_buffer = np.copy(frame.image_buffer)
                    numpy_shaped_image = image_buffer.reshape(self.camera.image_height_pixels, self.camera.image_width_pixels)
                
                    # Normalize the image to 0-255 range
                    numpy_shaped_image = cv2.normalize(numpy_shaped_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                    
                    # Create a 3-channel image
                    nd_image_array = cv2.cvtColor(numpy_shaped_image, cv2.COLOR_GRAY2BGR)
                    
                    cv2.imshow("Image From TSI Cam", nd_image_array)
                    cv2.waitKey(0)
                    #cv2.destroyAllWindows() #used for single frame acq testing purposes
                    
                    print(f"Frame buffer info: dtype={image_buffer.dtype}, shape={image_buffer.shape}")
                    print(f"Pixel value range: min={image_buffer.min()}, max={image_buffer.max()}")
                    
                    result = np.array(image_buffer)
                    
                    print(f"Resulting image shape: {result.shape}, dtype: {result.dtype}")
                    print(f"Resulting image range: min={result.min()}, max={result.max()}")
                    
                    return result
                else:
                    print(f"No frame received. Camera armed: {self.camera.is_armed}")
                    print(f"Frames per trigger: {self.camera.frames_per_trigger_zero_for_unlimited}")
                    print(f"Exposure time: {self.camera.exposure_time_us} us")
                    print(f"Image poll timeout: {self.camera.image_poll_timeout_ms} ms")
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error during acquisition: {str(e)}")
                time.sleep(0.1)
        
        raise Exception(f"Failed to receive frame after {max_attempts} attempts")
    
    def snap(self):
        return self.acquire()

    def _continuous_acquisition(self, dt):
        try:
            if not self.camera.is_armed:
                self.camera.arm(2)
            self.camera.issue_software_trigger()

            frame_count = 0
            while not self.stop_continuous_flag.is_set():
                try:
                    start_time = time.time()
                    
                    frame = self.camera.get_pending_frame_or_null()
                    if frame is not None:
                        frame_count += 1
                        print(f"Frame #{frame_count} received!")
                        
                        image_buffer_copy = np.copy(frame.image_buffer)
                        numpy_shaped_image = image_buffer_copy.reshape(self.image_height, self.image_width)
                        
                        # Normalize the image to 0-255 range
                        numpy_shaped_image = cv2.normalize(numpy_shaped_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                        
                        # Create a 3-channel image
                        nd_image_array = cv2.cvtColor(numpy_shaped_image, cv2.COLOR_GRAY2BGR)
                        
                        # Instead of displaying, we'll send the image to the parent
                        self.image_to_send = nd_image_array
                        
                        cv2.imshow("Image From TSI Cam", nd_image_array)
                        cv2.waitKey(1) 
                        
                    else:
                        print("Unable to acquire image, retrying...")
                    
                    processing_time = time.time() - start_time
                    sleep_time = max(0, dt - processing_time)
                    time.sleep(sleep_time)
                
                except Exception as e:
                    print(f"Error in continuous acquisition: {str(e)}")
                    time.sleep(0.1)
            
            self.camera.disarm()
            print("Continuous acquisition stopped")
        except Exception as e:
            print(f"Error arming camera: {str(e)}")
        
        self.camera.disarm()
        print("Continuous acquisition stopped")

    def start_continuous(self, dt):
        assert self.continuous_thread is None
        self.stop_continuous_flag.clear()
        self.continuous_thread = threading.Thread(target=self._continuous_acquisition, args=(dt,))
        self.continuous_thread.start()

    def stop_continuous(self):
        if self.continuous_thread is not None:
            self.stop_continuous_flag.set()
            self.continuous_thread.join()
            self.continuous_thread = None
        print("Continuous acquisition thread stopped")


    def grab(self):
        return self.acquire()

    def stop_acquisition(self):
        if self.camera.is_armed:
            self.camera.disarm()

    def abort_acquisition(self):
        self.stop_acquisition()

    def close(self):
        self.stop_continuous()
        if hasattr(self, 'camera'):
            self.camera.disarm()
            self.camera.dispose()
        if hasattr(self, 'sdk'):
            self.sdk.dispose()



    """
    def get_attributes_as_dict(self, visibility_level):
        Return a dict of the attributes of the camera for the given visibility level
        return self.camera.get_attributes(visibility_level)
    """
    def get_attributes_as_dict(self, visibility_level):

        attributes = {}
        try:
            attributes['exposure_time_us'] = self.camera.exposure_time_us
            attributes['image_width_pixels'] = self.camera.image_width_pixels
            attributes['image_height_pixels'] = self.camera.image_height_pixels
            attributes['sensor_readout_time_ns'] = self.camera.sensor_readout_time_ns
            attributes['bit_depth'] = self.camera.bit_depth
            attributes['sensor_pixel_width_um'] = self.camera.sensor_pixel_width_um
            attributes['sensor_pixel_height_um'] = self.camera.sensor_pixel_height_um
        except Exception as e:
            print(f"Error getting attributes: {str(e)}")
        return attributes

    def set_attribute(self, name, value):
        try:
            setattr(self.camera, name, value)
        except AttributeError:
            print(f"Attribute {name} not found or not settable")
        except Exception as e:
            print(f"Error setting attribute {name}: {str(e)}")

    def get_attribute(self, name):
        try:
            return getattr(self.camera, name)
        except AttributeError:
            print(f"Attribute {name} not found")
            return None

    
    def transition_to_buffered(self, device_name, h5_file, initial_values, fresh):
        # Set up for triggered acquisition
        self.camera.frames_per_trigger_zero_for_unlimited = 1
        self.camera.arm(2)
        return IMAQdxCameraWorker.transition_to_buffered(self, device_name, h5_file, initial_values, fresh)

    def transition_to_manual(self):
        # Set up for continuous acquisition
        self.camera.frames_per_trigger_zero_for_unlimited = 0
        self.camera.arm(2)
        return IMAQdxCameraWorker.transition_to_manual(self)
    
    def post_experiment(self, *args, **kwargs):
        self.stop_continuous()
        return True

    def abort(self):
        self.stop_continuous()
        return True