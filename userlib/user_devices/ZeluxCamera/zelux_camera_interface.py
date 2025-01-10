import numpy as np
import os
import sys
import ctypes
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

class ZeluxCameraInterface:
    def __init__(self, serial_number):
        dll_path = r"C:/Program Files/Thorlabs\Scientific Imaging/ThorCam/thorlabs_tsi_camera_sdk.dll"
        
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"DLL not found at {dll_path}")

        try:
            ctypes.cdll.LoadLibrary(dll_path)
            print(f"Successfully loaded DLL from {dll_path}")
        except Exception as e:
            print(f"Error loading DLL: {e}")
            raise

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
        
        if serial_number:
            if serial_number in camera_list:
                self.camera = self.sdk.open_camera(serial_number)
            else:
                raise Exception(f"Camera with serial number {serial_number} not found")
        else:
            self.camera = self.sdk.open_camera(camera_list[0])

        self.camera.arm(2)

    def set_attributes(self, attributes_dict):
        for attr, value in attributes_dict.items():
            self.set_attribute(attr, value)

    def set_attribute(self, name, value):
        try:
            setattr(self.camera, name, value)
        except AttributeError:
            raise ValueError(f"Camera has no attribute '{name}'")

    def get_attributes(self, visibility_level, writeable_only=True):
        attributes = {}
        for attr in dir(self.camera):
            if not attr.startswith('_') and not callable(getattr(self.camera, attr)):
                try:
                    attributes[attr] = getattr(self.camera, attr)
                except Exception:
                    pass
        return attributes
    
    def get_attribute(self, name):
        try:
            return getattr(self.camera, name)
        except AttributeError:
            raise ValueError(f"Camera has no attribute '{name}'")

    def snap(self):
        try:
            print("Issuing software trigger")
            self.camera.issue_software_trigger()
            print("Waiting for frame")
            frame = self.camera.get_pending_frame_or_null(timeout_ms=5000)  # 5 second timeout
            if frame is not None:
                print("Frame received")
                return frame.image_buffer.copy()
            else:
                print("No frame received within timeout")
                raise Exception("Snap Error: No frame received from camera within timeout")
        except Exception as e:
            print(f"Error in snap(): {str(e)}")
            raise

    def configure_acquisition(self, continuous=True, bufferCount=10):
        try:
            print(f"Configuring acquisition: continuous={continuous}, bufferCount={bufferCount}")
            self.camera.frames_per_trigger_zero_for_unlimited = 0 if continuous else 1
            if not self.camera.is_armed():
                print("Arming camera")
                self.camera.arm(2)
            else:
                print("Camera already armed")
        except Exception as e:
            print(f"Error in configure_acquisition(): {str(e)}")
            raise

    def grab(self):
        self.camera.issue_software_trigger()
        frame = self.camera.get_pending_frame_or_null()
        if frame is not None:
            return frame.image_buffer.copy()
        else:
            raise Exception("Grab Error: No frame received from camera")

    def stop_acquisition(self):
        self.camera.disarm()

    def close(self):
        self.camera.disarm()
        self.camera.dispose()
        self.sdk.dispose()

    def check_camera_status(self):
        try:
            print(f"Camera armed: {self.camera.is_armed()}")
            print(f"Frames per trigger: {self.camera.frames_per_trigger_zero_for_unlimited}")
            print(f"Exposure time: {self.camera.exposure_time_us} us")
            print(f"Image poll timeout: {self.camera.image_poll_timeout_ms} ms")
        except Exception as e:
            print(f"Error checking camera status: {str(e)}")