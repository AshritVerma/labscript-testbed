import sys
import nivision as nv

def get_attribute_info(camera, attr):
    """Get detailed information about an attribute."""
    name = attr.Name.decode()
    info = {
        'name': name,
        'type': attr.Type,
        'readable': attr.Readable,
        'writable': attr.Writable,
        'value': None,
        'range': None,
        'supported_values': None
    }
    
    try:
        info['value'] = nv.IMAQdxGetAttribute(camera, name.encode())
        if isinstance(info['value'], nv.core.IMAQdxEnumItem):
            info['value'] = info['value'].Name.decode()
        elif isinstance(info['value'], bytes):
            info['value'] = info['value'].decode()
            
        # Try to get range for numeric attributes
        try:
            info['range'] = nv.IMAQdxGetAttributeRange(camera, name.encode())
        except:
            pass
            
        # Try to get enumeration values
        try:
            info['supported_values'] = [
                item.Name.decode()
                for item in nv.IMAQdxEnumerateAttributeValues(camera, name.encode())
            ]
        except:
            pass
            
    except Exception as e:
        info['value'] = f"<error reading value: {str(e)}>"
        
    return info

def list_camera_attributes():
    """List all available IMAQdx attributes for the connected camera."""
    try:
        # Find all cameras
        print("Finding cameras...")
        cameras = nv.IMAQdxEnumerateCameras(True)
        if not cameras:
            print("No cameras found!")
            return
        
        print(f"\nFound {len(cameras)} camera(s):")
        for i, cam in enumerate(cameras):
            print(f"\nCamera {i+1}:")
            print(f"  Interface: {cam.InterfaceName.decode()}")
            print(f"  Serial: {(cam.SerialNumberHi << 32) + cam.SerialNumberLo:X}")
            print(f"  Vendor: {cam.VendorName.decode()}")
            print(f"  Model: {cam.ModelName.decode()}")
        
        # Let user choose which camera to inspect
        if len(cameras) > 1:
            camera_index = int(input("\nWhich camera to inspect? (1-{len(cameras)}): ")) - 1
        else:
            camera_index = 0
            
        # Connect to the selected camera
        print(f"\nConnecting to camera {camera_index + 1}...")
        camera = nv.IMAQdxOpenCamera(
            cameras[camera_index].InterfaceName,
            nv.IMAQdxCameraControlModeController
        )
        
        # Get all attributes
        print("\nCamera Attributes:")
        print("-----------------")
        for visibility in ['simple', 'intermediate', 'advanced']:
            print(f"\n{visibility.upper()} Attributes:")
            print("-" * (len(visibility) + 12))
            
            visibility_level = {
                'simple': nv.IMAQdxAttributeVisibilitySimple,
                'intermediate': nv.IMAQdxAttributeVisibilityIntermediate,
                'advanced': nv.IMAQdxAttributeVisibilityAdvanced,
            }[visibility]
            
            attributes = nv.IMAQdxEnumerateAttributes2(camera, b'', visibility_level)
            for attr in attributes:
                info = get_attribute_info(camera, attr)
                print(f"\n{info['name']}:")
                print(f"  Type: {info['type']}")
                print(f"  Readable: {info['readable']}")
                print(f"  Writable: {info['writable']}")
                print(f"  Current Value: {info['value']}")
                if info['range'] is not None:
                    print(f"  Range: {info['range']}")
                if info['supported_values'] is not None:
                    print(f"  Supported Values: {info['supported_values']}")
        
        # Clean up
        nv.IMAQdxCloseCamera(camera)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    list_camera_attributes() 