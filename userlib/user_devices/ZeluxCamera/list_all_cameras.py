import os
import sys
import nivision as nv

# Add the Thorlabs SDK path to system path
sdk_paths = [
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit\thorlabs_tsi_sdk-0.0.8",
    os.path.join(os.path.dirname(__file__), "thorlabs_tsi_sdk")
]

# Configure DLL paths
dll_paths = [
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Native Toolkit\dlls\Native_64_lib",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Native Toolkit",
]

# Add DLL paths to environment PATH
for dll_path in dll_paths:
    if os.path.exists(dll_path):
        if dll_path not in os.environ['PATH']:
            os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']
            try:
                os.add_dll_directory(dll_path)
            except (AttributeError, OSError) as e:
                print(f"Warning: Could not add DLL directory {dll_path}: {str(e)}")

def list_imaqdx_cameras():
    """List all cameras detected by IMAQdx."""
    print("\nIMAQdx Cameras:")
    print("--------------")
    try:
        cameras = nv.IMAQdxEnumerateCameras(True)
        if not cameras:
            print("No IMAQdx cameras found!")
            return
        
        for i, cam in enumerate(cameras):
            print(f"\nCamera {i+1}:")
            print(f"  Interface: {cam.InterfaceName.decode()}")
            print(f"  Serial: {(cam.SerialNumberHi << 32) + cam.SerialNumberLo:X}")
            print(f"  Vendor: {cam.VendorName.decode()}")
            print(f"  Model: {cam.ModelName.decode()}")
            print(f"  Bus Type: {cam.BusType}")
            
    except Exception as e:
        print(f"Error listing IMAQdx cameras: {str(e)}")

def list_thorlabs_cameras():
    """List all cameras detected by Thorlabs SDK."""
    print("\nThorlabs Cameras:")
    print("----------------")
    
    # Try each potential SDK path
    sdk_found = False
    for sdk_path in sdk_paths:
        if os.path.exists(sdk_path) and sdk_path not in sys.path:
            sys.path.append(sdk_path)
            try:
                from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
                sdk_found = True
                print(f"Found Thorlabs SDK at: {sdk_path}")
                break
            except ImportError:
                sys.path.remove(sdk_path)
                continue

    if not sdk_found:
        print("Could not find Thorlabs SDK!")
        return

    try:
        with TLCameraSDK() as sdk:
            cameras = sdk.discover_available_cameras()
            if not cameras:
                print("No Thorlabs cameras found!")
                return
            
            print(f"\nFound {len(cameras)} camera(s)")
            for i, serial in enumerate(cameras):
                try:
                    with sdk.open_camera(serial) as camera:
                        print(f"\nCamera {i+1}:")
                        print(f"  Model: {camera.model}")
                        print(f"  Name: {camera.name}")
                        print(f"  Serial Number: {camera.serial_number}")
                        print(f"  Firmware Version: {camera.firmware_version}")
                except Exception as e:
                    print(f"Error opening camera {serial}: {str(e)}")
                    
    except Exception as e:
        print(f"Error listing Thorlabs cameras: {str(e)}")

if __name__ == "__main__":
    print("Listing all available cameras in the system...")
    list_imaqdx_cameras()
    list_thorlabs_cameras() 