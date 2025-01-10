from blacs.device_base_class import DeviceTab
from qtutils.qt import QtCore, QtWidgets
import numpy as np

class ZeluxCameraTab(DeviceTab):
    def __init__(self, *args, **kwargs):
        self.device_worker_class = 'user_devices.ZeluxCamera.blacs_workers.ZeluxCameraWorker'
        self.ui = QtWidgets.QWidget()
        
        # Create GUI elements before parent initialization
        self.create_GUI()
        
        # Initialize parent class
        DeviceTab.__init__(self, *args, **kwargs)
        
        # Create worker after parent initialization
        self.primary_worker = self.create_worker("main_worker", self.device_worker_class)

    def create_GUI(self):
        """Create all GUI elements."""
        # Create a layout for the tab
        self.layout = QtWidgets.QVBoxLayout(self.ui)
        
        # Create widgets for displaying camera info and images
        self.info_label = QtWidgets.QLabel("Camera Status: Not Connected")
        self.image_label = QtWidgets.QLabel()
        
        # Add widgets to layout
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.image_label)
        
        # Create control buttons
        self.snap_button = QtWidgets.QPushButton("Snap")
        self.snap_button.clicked.connect(self.on_snap)
        self.layout.addWidget(self.snap_button)

    def initialise_GUI(self):
        """Called when the tab is started."""
        if hasattr(self, 'info_label'):
            self.info_label.setText("Camera Status: Initializing...")

    def on_snap(self):
        """Handle snap button click."""
        try:
            results = self.queue_work("main_worker", "snap")
            if results is not None:
                self.info_label.setText("Image captured successfully")
        except Exception as e:
            self.info_label.setText(f"Error capturing image: {str(e)}")

    def get_tab_layout(self):
        return self.layout