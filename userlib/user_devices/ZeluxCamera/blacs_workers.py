from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraWorker

import sys
import os

device_dir = os.path.dirname(os.path.abspath(__file__))
sdk_path = os.path.join(device_dir, 'thorlabs_tsi_sdk')

dll_path = os.path.join(device_dir, 'dlls', '64_lib')
thorcam_path = os.path.join(device_dir, 'ThorCam')

# Add paths to Python's sys.path
for path in [device_dir, sdk_path, dll_path, thorcam_path]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Add DLL paths to system PATH
os.environ['PATH'] = os.pathsep.join([dll_path, thorcam_path, os.environ['PATH']])

# Try to add DLL directories for Python 3.8+
try:
    os.add_dll_directory(dll_path)
    os.add_dll_directory(thorcam_path)
    os.add_dll_directory(sdk_path)
except AttributeError:
    pass

from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraWorker
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCameraError, ROI
    from thorlabs_tsi_sdk.tl_camera_enums import OPERATION_MODE, SENSOR_TYPE
    from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK
except ImportError as e:
    print(f"Error importing Thorlabs SDK: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Looking for SDK in: {sdk_path}")
    print(f"Files in SDK directory: {os.listdir(sdk_path)}")
    raise

import numpy as np

import ctypes
import time
import threading
from labscript_utils import zprocess
import cv2
from PIL import Image
import queue
from labscript_utils import dedent

class ZeluxCameraWorker(IMAQdxCameraWorker):
    interface_class = TLCameraSDK

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.h5_filepath = None
        self.acquisition_thread = None
        self.stop_acquisition_flag = threading.Event()
        self.acquisition_queue = queue.Queue()
        self.stop_acquisition_timeout = 10.0  # Default timeout of 5 seconds
        self.exception_on_failed_shot = True
        self._is_armed = False
    
    @staticmethod
    def save_image(image_data, filename):
        """Save the image data as a PNG file on local dir as a test."""
        image = Image.fromarray(image_data)
        image.save(filename)

    def set_attributes_smart(self, attributes):
        was_armed = self.is_armed
        if was_armed:
            self.stop_acquisition()
        for attr, value in attributes.items():
            if attr == 'exposure_time_us':
                self.camera.exposure_time_us = value
            elif attr == 'image_width_pixels' or attr == 'image_height_pixels':
                self._set_roi(attributes.get('image_width_pixels'), attributes.get('image_height_pixels'))
            elif attr == 'roi':
                self._set_roi(*value)
        self.smart_cache.update(attributes)
        if was_armed:
            self.start_acquisition()
        
    def _set_roi(self, width=None, height=None):
        current_roi = self.camera.roi
        new_roi = ROI(
            current_roi.upper_left_x_pixels,
            current_roi.upper_left_y_pixels,
            width or current_roi.lower_right_x_pixels,
            height or current_roi.lower_right_y_pixels
        )
        self.camera.roi = new_roi

    def configure_acquisition(self, continuous=False, bufferCount=5):
        was_armed = self.is_armed
        if was_armed:
            self.stop_acquisition()

        self.camera.frames_per_trigger_zero_for_unlimited = 0 if continuous else 1
        # The TLCamera SDK doesn't have a direct equivalent to bufferCount,
        # so we'll ignore it for now.

        if was_armed:
            self.start_acquisition()
    
    def start_acquisition(self):
        if not self.is_armed:
            try:
                self.camera.arm(2)
                self._is_armed = True
                self.camera_running = True
                self.start_acquisition_thread()
            except Exception as e:
                print(f"Error arming camera: {str(e)}")
                self._is_armed = False
                self.camera_running = False

    def stop_acquisition(self):
        if self._is_armed:
            try:
                self.stop_acquisition_flag.set()
                if self.acquisition_thread is not None:
                    self.acquisition_thread.join(timeout=self.stop_acquisition_timeout)
                    if self.acquisition_thread.is_alive():
                        print("Warning: Acquisition thread did not finish in time")
                self.camera.disarm()
                self._is_armed = False
            except Exception as e:
                print(f"Error stopping acquisition: {str(e)}")
    
    def configure_path(self):
        # Get the absolute path to the device directory
        device_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define paths to SDK components
        sdk_path = os.path.join(device_dir, 'thorlabs_tsi_sdk')
        dll_path = os.path.join(device_dir, 'dlls', '64_lib')
        thorcam_path = os.path.join(device_dir, 'ThorCam')
        
        # Add all paths to Python's sys.path if not already there
        for path in [device_dir, sdk_path, dll_path, thorcam_path]:
            if path not in sys.path:
                sys.path.insert(0, path)
        
        # Add the DLL paths to the system PATH
        os.environ['PATH'] = os.pathsep.join([dll_path, thorcam_path, os.environ['PATH']])
        
        try:
            # Python 3.8+ method to specify dll directory
            os.add_dll_directory(dll_path)
            os.add_dll_directory(thorcam_path)
        except AttributeError:
            pass

    def _create_window(self):
        with self.window_lock:
            if not self.window_created:
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                self.window_created = True

    def _window_exists(self):
        with self.window_lock:
            try:
                return cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) >= 0
            except cv2.error:
                return False

    def _destroy_window(self):
        with self.window_lock:
            try:
                if self.window_created:
                    cv2.destroyWindow(self.window_name)
            except cv2.error:
                pass  # Window might already be destroyed
            finally:
                self.window_created = False
            
    @property
    def is_armed(self):
        return self._is_armed
    
    def init(self):

        print(f"ZeluxCameraWorker init method called, so configuring path with sdk dlls")
        self.configure_path()
        self.window_name = "Image from zelux camera"
        self.window_created = False
        self.window_lock = threading.Lock()
        self.start_acquisition_thread()

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
            self._is_armed = True
            
            #need to save image width and height for color processing
            self.image_width = self.camera.image_width_pixels
            self.image_height = self.camera.image_height_pixels

            self.continuous_thread = None
            self.stop_continuous_flag = threading.Event()

            self.start_acquisition_thread()

            # user defined exposure time attrs for testing and passing vars directly from workers script instead of cxn table
            acq_time_get_loc = 40
            acq_time_get_probe = 40
            

        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            raise
        

    def acquire(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            if not self._is_armed:
                self.start_acquisition_thread()

            try:
                print(f"Attempting to acquire frame (attempt {attempt + 1}/{max_attempts})...")
                
                if not self.camera.is_armed:
                    print("Camera is not armed. Arming...")
                    #self.camera.arm(2)
                    self.start_acquisition()
                    time.sleep(0.001)

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
            except queue.Empty:
                print("Timeout waiting for image acquisition")
                return None
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

            self._create_window()

            while not self.stop_continuous_flag.is_set():
                try:
                    start_time = time.time()
                    
                    frame = self.camera.get_pending_frame_or_null()
                    if frame is not None:
                        image_buffer_copy = np.copy(frame.image_buffer)
                        numpy_shaped_image = image_buffer_copy.reshape(self.image_height, self.image_width)
                        
                        numpy_shaped_image = cv2.normalize(numpy_shaped_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                        nd_image_array = cv2.cvtColor(numpy_shaped_image, cv2.COLOR_GRAY2BGR)
                        
                        self.image_to_send = nd_image_array
                        
                        if self._window_exists():
                            cv2.imshow(self.window_name, nd_image_array)
                            key = cv2.waitKey(1) & 0xFF
                            if key == ord('q'):
                                break
                        else:
                            print("Display window was closed. Stopping continuous acquisition.")
                            break
                    else:
                        print("Unable to acquire image, retrying...")
                    
                    processing_time = time.time() - start_time
                    sleep_time = max(0, dt - processing_time)
                    time.sleep(sleep_time)
                
                except Exception as e:
                    print(f"Error in continuous acquisition: {str(e)}")
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error in continuous acquisition: {str(e)}")
        finally:
            self.camera.disarm()
            self._destroy_window()
            print("Continuous acquisition stopped")

    def stop_continuous(self):
        if self.continuous_thread is not None:
            self.stop_continuous_flag.set()
            self.continuous_thread.join()
            self.continuous_thread = None
        self._destroy_window()
        print("Continuous acquisition thread stopped")
        

    def start_continuous(self, dt):
        if self.continuous_thread is not None:
            self.stop_continuous()
        self.stop_continuous_flag.clear()
        self.continuous_thread = threading.Thread(target=self._continuous_acquisition, args=(dt,))
        self.continuous_thread.start()


    def grab(self):
        return self.acquire()

    def abort_acquisition(self):
        self.stop_acquisition()

    def close(self):
        self.stop_acquisition_thread()
        if hasattr(self, 'camera'):
            if self.camera.is_armed:
                self.camera.disarm()
            self.camera.dispose()
        super().close()



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
    
    def change_exposure_time(self, exposure_time_us):
        """Change the exposure time of the camera."""
        try:
            self.camera.exposure_time_us = exposure_time_us
            print(f"Exposure time set to {self.camera.exposure_time_us} us")
        except Exception as e:
            print(f"Error setting exposure time: {str(e)}")

    def change_image_size(self, width, height):
        """Change the image size of the camera."""
        try:
            # Calculate a valid ROI
            new_roi = ROI(
                upper_left_x_pixels=0,
                upper_left_y_pixels=0,
                lower_right_x_pixels=min(width, self.camera.sensor_width_pixels),
                lower_right_y_pixels=min(height, self.camera.sensor_height_pixels)
            )
            self.camera.roi = new_roi
            print(f"Image size set to {self.camera.image_width_pixels}x{self.camera.image_height_pixels}")
        except Exception as e:
            print(f"Error setting image size: {str(e)}")

    def get_camera_attributes(self):
        """Get current camera attributes."""
        return {
            'exposure_time_us': self.camera.exposure_time_us,
            'image_width_pixels': self.camera.image_width_pixels,
            'image_height_pixels': self.camera.image_height_pixels,
            'roi': self.camera.roi,
            'bit_depth': self.camera.bit_depth,
            'sensor_pixel_width_um': self.camera.sensor_pixel_width_um,
            'sensor_pixel_height_um': self.camera.sensor_pixel_height_um,
        }

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

    def start_acquisition_thread(self):
        if self.acquisition_thread is None or not self.acquisition_thread.is_alive():
            self.stop_acquisition_flag.clear()
            self.acquisition_thread = threading.Thread(target=self._acquisition_loop)
            self.acquisition_thread.daemon = True
            self.acquisition_thread.start()

    def _acquisition_loop(self):
        while not self.stop_acquisition_flag.is_set():
            try:
                if self.is_armed:
                    frame = self.camera.get_pending_frame_or_null()
                    if frame is not None:
                        image_buffer = np.copy(frame.image_buffer)
                        self.acquisition_queue.put(image_buffer)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Error in acquisition loop: {str(e)}")
            time.sleep(0.001)  # Small sleep to prevent busy-waiting

    def stop_acquisition_thread(self):
        self.stop_acquisition_flag.set()
        if self.acquisition_thread is not None:
            self.acquisition_thread.join(timeout=self.stop_acquisition_timeout)
            if self.acquisition_thread.is_alive():
                print("Warning: Acquisition thread did not finish in time")
            self.acquisition_thread = None

    def transition_to_buffered(self, device_name, h5_file, initial_values, fresh):
        self.h5_filepath = h5_file
        self.stop_acquisition_thread()
        self.camera.disarm()
        self._is_armed = False
        
        for key, value in initial_values.items():
            if hasattr(self.camera, key):
                setattr(self.camera, key, value)
        
        self.camera.arm(2)
        self._is_armed = True
        self.start_acquisition_thread()
        
        return super().transition_to_buffered(device_name, h5_file, initial_values, fresh)

    
    def transition_to_manual(self):
        try:
            self.stop_acquisition_thread()
            self.camera.disarm()
            self._is_armed = False
            
            self.camera.frames_per_trigger_zero_for_unlimited = 0
            self.camera.arm(2)
            self._is_armed = True
            
            self.start_acquisition_thread()
            
            self.h5_filepath = None
            return True
        except Exception as e:
            msg = f"""Error in transition_to_manual: {str(e)}
            Failed to transition to manual mode.
            Check camera configuration and connections."""
            print(dedent(msg))
            if self.exception_on_failed_shot:
                raise RuntimeError(dedent(msg))
            return False

    def stop_acquisition(self):
        self.stop_acquisition_thread()
        if self.camera.is_armed:
            self.camera.disarm()
        self._is_armed = False

    
    def post_experiment(self, *args, **kwargs):
        
        return True

    def abort(self):
        self.stop_acquisition()
        return True