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
            ],
            }
    )
    def __init__(self, name, parent_device, connection,
                 exposure_time_us=1000, image_width_pixels=1280, image_height_pixels=1024,
                 offset_x=0, offset_y=0, roi=None, **kwargs):
        
        # Initialize Zelux-specific attributes
        self.exposure_time_us = exposure_time_us
        self.image_width_pixels = image_width_pixels
        self.image_height_pixels = image_height_pixels
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.roi = roi if roi else (0, 0, image_width_pixels, image_height_pixels)

        # Update camera_attributes with Zelux-specific settings
        camera_attributes = kwargs.get('camera_attributes', {})
        camera_attributes.update({
            'exposure_time_us': exposure_time_us,
            'image_width_pixels': image_width_pixels,
            'image_height_pixels': image_height_pixels,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'roi': self.roi,
        })
        kwargs['camera_attributes'] = camera_attributes

        # Call the parent class constructor
        super().__init__(name, parent_device, connection, **kwargs)

    def expose(self, t, name, frametype='frame', trigger_duration=None):
        # Update exposure time and image size before calling the parent method
        self.set_property('exposure_time_us', self.exposure_time_us, location='device')
        self.set_property('image_width_pixels', self.image_width_pixels, location='device')
        self.set_property('image_height_pixels', self.image_height_pixels, location='device')

        # Call the parent class's expose method
        super().expose(t, name, frametype, trigger_duration)

    # def generate_code(self, hdf5_file):
    #     # Call the parent class's generate_code method
    #     super().generate_code(hdf5_file)
    
    def change_exposure_time(self, exposure_time_us):
        """Change the exposure time of the camera."""
        self.exposure_time_us = exposure_time_us

    def change_image_size(self, image_width_pixels, image_height_pixels):
        """Change the image size of the camera."""
        self.image_width_pixels = image_width_pixels
        self.image_height_pixels = image_height_pixels

    def change_roi(self, upper_left_x_pixels, upper_left_y_pixels, lower_right_x_pixels, lower_right_y_pixels):
        """Change the region of interest of the camera."""

        new_roi = ROI(upper_left_x_pixels=upper_left_x_pixels, upper_left_y_pixels=upper_left_y_pixels,
                      lower_right_x_pixels=lower_right_x_pixels, lower_right_y_pixels=lower_right_y_pixels)

        print(f"Setting ROI to: {new_roi}")
        self.roi = new_roi

        actual_roi = self.roi
        print(f"Actual ROI: {actual_roi}")

        if actual_roi == new_roi:
            print("ROI set successfully!")
        else:
            print("Warning: ROI not set exactly as expected.")
            print(f"Expected: {new_roi}")
            print(f"Actual: {actual_roi}")

        print(f"New image size: {self.image_width_pixels}x{self.image_height_pixels}")
        # print(f"Sensor pixel size: {self.sensor_pixel_width_um}um x {self.sensor_pixel_height_um}um")
