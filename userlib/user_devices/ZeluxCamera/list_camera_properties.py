import os
import sys

# Add the Thorlabs SDK path to system path
sdk_paths = [
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit",
    r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit\thorlabs_tsi_sdk-0.0.8",
    os.path.join(os.path.dirname(__file__), "thorlabs_tsi_sdk")
]

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

def list_camera_properties():
    """List all available properties of the connected camera."""
    sdk = None
    camera = None
    try:
        sdk = TLCameraSDK()
        cameras = sdk.discover_available_cameras()
        if not cameras:
            print("No cameras found!")
            return
        
        print(f"Found {len(cameras)} camera(s)")
        print(f"Camera serial numbers: {cameras}")
        
        camera = sdk.open_camera(cameras[0])
        
        print("\nCamera Properties:")
        print("-----------------")
        print(f"Model: {camera.model}")
        print(f"Name: {camera.name}")
        print(f"Serial Number: {camera.serial_number}")
        print(f"Firmware Version: {camera.firmware_version}")
        
        print("\nSensor Properties:")
        print("-----------------")
        print(f"Sensor width: {camera.sensor_width_pixels} pixels")
        print(f"Sensor height: {camera.sensor_height_pixels} pixels")
        print(f"Pixel width: {camera.sensor_pixel_width_um} um")
        print(f"Pixel height: {camera.sensor_pixel_height_um} um")
        print(f"Pixel clock: {camera.camera_sensor_type}")
        
        print("\nExposure Properties:")
        print("-------------------")
        print(f"Exposure range: {camera.exposure_time_range_us}")
        print(f"Current exposure: {camera.exposure_time_us} us")
        
        print("\nGain Properties:")
        print("---------------")
        print(f"Gain range: {camera.gain_range}")
        print(f"Current gain: {camera.gain}")
        
        print("\nROI Properties:")
        print("--------------")
        print(f"ROI range: {camera.roi_range}")
        print(f"Current ROI: {camera.roi}")
        
        print("\nTrigger Properties:")
        print("------------------")
        print(f"Supports hardware triggering: {camera.hardware_trigger_masks}")
        print(f"Operation modes: Software trigger, Hardware trigger")
        
        print("\nOther Properties:")
        print("----------------")
        print(f"Bit depth: {camera.bit_depth}")
        print(f"Black level: {camera.black_level_range}")
        print(f"Frame time: {camera.frame_time_us} us")
        print(f"Image poll timeout: {camera.image_poll_timeout_ms} ms")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if camera is not None:
            camera.dispose()
        if sdk is not None:
            sdk.dispose()

if __name__ == "__main__":
    list_camera_properties() 