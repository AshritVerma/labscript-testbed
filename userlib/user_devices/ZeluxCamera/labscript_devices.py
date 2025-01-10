from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from labscript import set_passed_properties, LabscriptError, start, stop, wait, AnalogOut, DigitalOut


class ZeluxCamera(IMAQdxCamera):
    description = 'Thorlabs Zelux Camera'
    
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
            "device_properties": [
                "exposure_time_us",
                "image_width_pixels",
                "image_height_pixels",
                "roi",
            ]
        }
    )
    def __init__(self, name, parent_device, connection, serial_number,
                 exposure_time_us=1000, image_width_pixels=1280, image_height_pixels=1024,
                 offset_x=0, offset_y=0, roi=None, **kwargs):
        
        # Store our custom attributes
        self.exposure_time_us = exposure_time_us
        self.image_width_pixels = image_width_pixels
        self.image_height_pixels = image_height_pixels
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.roi = roi if roi else (0, 0, image_width_pixels, image_height_pixels)

        # Set up camera attributes for parent class
        camera_attributes = {
            'exposure_time_us': exposure_time_us,
            'image_width_pixels': image_width_pixels,
            'image_height_pixels': image_height_pixels,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'roi': self.roi,
        }
        
        # Call parent class constructor with our camera attributes
        IMAQdxCamera.__init__(
            self,
            name=name,
            parent_device=parent_device,
            connection=connection,
            serial_number=serial_number,
            camera_attributes=camera_attributes,
            **kwargs
        )

    def expose(self, t, name, frametype='image'):
        """Request exposure of one frame."""
        # Call parent expose method with default trigger duration
        trigger_duration = 0.001  # 1ms trigger pulse
        IMAQdxCamera.expose(self, t, name, frametype, trigger_duration)
    
    def change_exposure_time(self, exposure_time_us):
        """Change the exposure time of the camera."""
        self.exposure_time_us = exposure_time_us
        # Update camera_attributes instead of using set_property
        if not hasattr(self, '_camera_attributes'):
            self._camera_attributes = {}
        self._camera_attributes['exposure_time_us'] = exposure_time_us

    def change_image_size(self, image_width_pixels, image_height_pixels):
        """Change the image size of the camera."""
        self.image_width_pixels = image_width_pixels
        self.image_height_pixels = image_height_pixels
        # Update camera_attributes
        if not hasattr(self, '_camera_attributes'):
            self._camera_attributes = {}
        self._camera_attributes.update({
            'image_width_pixels': image_width_pixels,
            'image_height_pixels': image_height_pixels
        })

    def change_roi(self, upper_left_x_pixels, upper_left_y_pixels, lower_right_x_pixels, lower_right_y_pixels):
        """Change the region of interest of the camera."""
        self.roi = (upper_left_x_pixels, upper_left_y_pixels, 
                   lower_right_x_pixels, lower_right_y_pixels)
        
        # Update image size based on ROI
        self.image_width_pixels = lower_right_x_pixels - upper_left_x_pixels
        self.image_height_pixels = lower_right_y_pixels - upper_left_y_pixels
        
        # Update camera_attributes
        if not hasattr(self, '_camera_attributes'):
            self._camera_attributes = {}
        self._camera_attributes.update({
            'roi': self.roi,
            'image_width_pixels': self.image_width_pixels,
            'image_height_pixels': self.image_height_pixels
        })

    def generate_code(self, hdf5_file):
        # Call the parent class's generate_code method
        IMAQdxCamera.generate_code(self, hdf5_file)
