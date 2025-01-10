import os
import sys

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
            from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
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

def list_cameras():
    """List all available Thorlabs cameras."""
    try:
        with TLCameraSDK() as sdk:
            cameras = sdk.discover_available_cameras()
            if not cameras:
                print("No Thorlabs cameras found!")
            else:
                print(f"Found {len(cameras)} camera(s):")
                for i, serial in enumerate(cameras, 1):
                    print(f"{i}. Serial Number: {serial}")
            return cameras
    except Exception as e:
        print(f"Error listing cameras: {str(e)}")
        return []

if __name__ == '__main__':
    list_cameras() 