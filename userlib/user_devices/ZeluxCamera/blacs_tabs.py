from labscript_devices.IMAQdxCamera.blacs_tabs import IMAQdxCameraTab

class ZeluxCameraTab(IMAQdxCameraTab):

    worker_class = 'user_devices.ZeluxCamera.blacs_workers.ZeluxCameraWorker'
