import os
import sys
import numpy as np
import threading
import zmq
from labscript_utils import dedent
from blacs.tab_base_classes import Worker
from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraWorker
from labscript_utils.ls_zprocess import Context

# Add the Thorlabs SDK path to system path
sdk_paths = [
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit\thorlabs_tsi_sdk-0.0.8",
    os.path.join(os.path.dirname(__file__), "thorlabs_tsi_sdk")
]

# Try each potential SDK path
sdk_found = False
for sdk_path in sdk_paths:
    if os.path.exists(sdk_path) and sdk_path not in sys.path:
        sys.path.append(sdk_path)
        try:
            from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCameraError, ROI
            sdk_found = True
            print(f"Found Thorlabs SDK at: {sdk_path}")
            break
        except ImportError:
            sys.path.remove(sdk_path)
            continue

if not sdk_found:
    raise ImportError(
        "Could not find Thorlabs SDK. Please ensure it is installed in one of the following locations:\n" +
        "\n".join(sdk_paths)
    )

# Configure DLL paths - add all relevant directories
dll_paths = [
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Native Toolkit\dlls\Native_64_lib",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Native Toolkit",
]

# Add all DLL paths to environment PATH
for dll_path in dll_paths:
    if os.path.exists(dll_path):
        if dll_path not in os.environ['PATH']:
            os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']
            try:
                os.add_dll_directory(dll_path)
            except (AttributeError, OSError) as e:
                print(f"Warning: Could not add DLL directory {dll_path}: {str(e)}")

print(f"Current PATH: {os.environ['PATH']}")

class ZeluxCameraWorker(IMAQdxCameraWorker):
    def init(self):
        # Call parent's init first to get _image_socket_port
        self.manual_mode_dict = IMAQdxCameraWorker.init(self)
        
        try:
            self.sdk = TLCameraSDK()
            self.camera = None
            self.continuous_thread = None
            self.abort_continuous = False
            self.image_socket = Context.instance().socket(zmq.REQ)
            self.image_socket.connect('tcp://127.0.0.1:%d' % self._image_socket_port)
            
            # Get list of cameras
            cameras = self.sdk.discover_available_cameras()
            if not cameras:
                raise Exception("No Zelux cameras found!")
                
            # Connect to the first available camera
            self.serial_number = cameras[0]
            self.camera = self.sdk.open_camera(self.serial_number)
            
            # Configure default settings
            self.camera.exposure_time_us = 10000  # 10ms exposure
            self.camera.frames_per_trigger_zero_for_unlimited = 0
            self.camera.image_poll_timeout_ms = 1000
            self.camera.operation_mode = 0  # Software triggered mode
            
            return self.manual_mode_dict
            
        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            raise

    def get_attributes_as_dict(self, visibility_level='all'):
        """Get camera attributes as a dictionary."""
        try:
            attrs = {
                'exposure_time': self.camera.exposure_time_us,
                'frame_time': self.camera.frame_time_us,
                'sensor_width': self.camera.sensor_width_pixels,
                'sensor_height': self.camera.sensor_height_pixels,
                'image_width': self.camera.roi.width,
                'image_height': self.camera.roi.height,
                'roi_x': self.camera.roi.upper_left_x_pixels,
                'roi_y': self.camera.roi.upper_left_y_pixels,
            }
            return attrs
        except Exception as e:
            print(f"Error getting attributes: {str(e)}")
            return {}

    def get_attributes_as_text(self, visibility_level='all'):
        """Get camera attributes as formatted text."""
        attrs = self.get_attributes_as_dict(visibility_level)
        text = 'Zelux Camera Attributes:\n\n'
        for key, value in attrs.items():
            text += f'{key}: {value}\n'
        return text

    def snap(self):
        """Capture a single frame."""
        try:
            # Make sure camera is disarmed first
            if self.camera.is_armed:  # Remove parentheses - it's a property
                self.camera.disarm()
            
            # Configure for single frame
            self.camera.frames_per_trigger_zero_for_unlimited = 1
            self.camera.operation_mode = 0  # Software triggered mode
            
            # Arm and capture
            try:
                self.camera.arm(1)  # Request only 1 frame buffer
                self.camera.issue_software_trigger()
                frame = self.camera.get_pending_frame_or_null()
                if frame is not None:
                    return np.copy(frame.image_buffer)
                else:
                    raise Exception("Failed to acquire image")
            finally:
                self.camera.disarm()
        except Exception as e:
            print(f"Error in snap: {str(e)}")
            raise

    def start_continuous(self, fresh=False):
        """Start continuous acquisition mode."""
        if self.continuous_thread is not None:
            return

        def continuous_acquisition():
            try:
                # Make sure camera is disarmed first
                if self.camera.is_armed:  # Remove parentheses - it's a property
                    self.camera.disarm()
                
                # Configure for continuous acquisition
                self.camera.frames_per_trigger_zero_for_unlimited = 0
                self.camera.operation_mode = 0  # Software triggered mode
                
                self.camera.arm(2)  # Use 2 frame buffers for continuous mode
                
                while not self.abort_continuous:
                    try:
                        self.camera.issue_software_trigger()
                        frame = self.camera.get_pending_frame_or_null()
                        if frame is not None:
                            image = np.copy(frame.image_buffer)
                            self.new_frame_signal.emit(image)
                    except Exception as e:
                        print(f"Error in continuous acquisition loop: {str(e)}")
                        break
            finally:
                try:
                    if self.camera.is_armed:  # Remove parentheses here too
                        self.camera.disarm()
                except:
                    pass

        self.abort_continuous = False
        self.continuous_thread = threading.Thread(target=continuous_acquisition)
        self.continuous_thread.daemon = True
        self.continuous_thread.start()

    def stop_continuous(self):
        """Stop continuous acquisition mode."""
        if self.continuous_thread is None:
            return
        self.abort_continuous = True
        self.continuous_thread.join()
        self.continuous_thread = None
        
    def program_manual(self, values):
        return values
        
    def transition_to_buffered(self, device_name, h5file, initial_values, fresh):
        return self.manual_mode_dict
        
    def transition_to_manual(self):
        return True
        
    def abort_buffered(self):
        return True
        
    def abort_transition_to_buffered(self):
        return True
        
    def shutdown(self):
        if self.continuous_thread is not None:
            self.stop_continuous()
        if hasattr(self, 'camera') and self.camera:
            self.camera.dispose()
        if hasattr(self, 'sdk') and self.sdk:
            self.sdk.dispose()