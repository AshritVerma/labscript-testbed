print("registering Zelux Camera")
from labscript_devices import register_classes
#from user_devices.ZeluxCamera.labscript_devices import ZeluxCamera

register_classes(
    'ZeluxCamera',
    BLACS_tab='user_devices.ZeluxCamera.blacs_tabs.ZeluxCameraTab',
    runviewer_parser=None
)
print("completed registering Zelux Camera")