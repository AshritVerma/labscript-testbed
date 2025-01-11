from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from labscript.labscript import set_passed_properties
import sys
import os

# Add the local SDK path to Python's path
sdk_path = os.path.dirname(os.path.abspath(__file__))
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from thorlabs_tsi_sdk.tl_camera import ROI
from .blacs_workers import ZeluxCameraWorker

class ZeluxCamera(IMAQdxCamera):
    description = 'Thorlabs Zelux Camera'
    camera_class = 'ZeluxCamera'
    worker_class = ZeluxCameraWorker
    
    @set_passed_properties(
        property_names = {
            "connection_table_properties": [
                "exposure_time_us",
                "image_width_pixels",
                "image_height_pixels",
                "offset_x",
                "offset_y",
                "roi",
                "acquisition_timeout",
                "fail_on_error"
            ]
        }
    )
    def __init__(self, name, parent_device, connection,
                 serial_number,
                 exposure_time_us=1000,
                 image_width_pixels=1280,
                 image_height_pixels=1024,
                 offset_x=0,
                 offset_y=0,
                 roi=None,
                 acquisition_timeout=5.0,
                 fail_on_error=True,
                 **kwargs):
        
        # Store our own properties
        self._exposure_time_us = exposure_time_us
        self._image_width_pixels = image_width_pixels
        self._image_height_pixels = image_height_pixels
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._roi = roi if roi else (0, 0, image_width_pixels, image_height_pixels)
        self._acquisition_timeout = acquisition_timeout
        self._fail_on_error = fail_on_error

        # Convert serial number to string if it's not already
        if not isinstance(serial_number, str):
            serial_number = str(serial_number)

        # Call parent with minimal parameters
        super().__init__(
            name=name,
            parent_device=parent_device,
            connection=connection,
            serial_number=serial_number,
            stop_acquisition_timeout=acquisition_timeout,
            exception_on_failed_shot=fail_on_error,
            **kwargs
        )

    @property
    def exposure_time_us(self):
        return self._exposure_time_us

    @property
    def image_width_pixels(self):
        return self._image_width_pixels

    @property
    def image_height_pixels(self):
        return self._image_height_pixels

    @property
    def offset_x(self):
        return self._offset_x

    @property
    def offset_y(self):
        return self._offset_y

    @property
    def roi(self):
        return self._roi

    @property
    def acquisition_timeout(self):
        return self._acquisition_timeout

    @property
    def fail_on_error(self):
        return self._fail_on_error

    def expose(self, t, name, frametype='frame', trigger_duration=None):
        """Request an exposure at the given time."""
        super().expose(t, name, frametype, trigger_duration)

    def generate_code(self, hdf5_file):
        super().generate_code(hdf5_file)
    
    def get_property_value(self, name):
        """Get the current value of a property"""
        if hasattr(self, f"_{name}"):
            return getattr(self, f"_{name}")
        return None

    def get_all_properties(self):
        """Get all camera properties as a dictionary"""
        return {
            'exposure_time_us': self._exposure_time_us,
            'image_width_pixels': self._image_width_pixels,
            'image_height_pixels': self._image_height_pixels,
            'offset_x': self._offset_x,
            'offset_y': self._offset_y,
            'roi': self._roi,
            'acquisition_timeout': self._acquisition_timeout,
            'fail_on_error': self._fail_on_error
        }
