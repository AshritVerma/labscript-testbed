from labscript import start, stop, add_time_marker, Trigger, AnalogOut, DigitalOut 
from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
from labscript_devices.DummyIntermediateDevice import DummyIntermediateDevice
from user_devices.ZeluxCamera.labscript_devices import ZeluxCamera

def cxn_table():
    # Use a virtual ('dummy') device for the psuedoclock
    DummyPseudoclock(name='pseudoclock')

    # An output of this DummyPseudoclock is its 'clockline' attribute
    DummyIntermediateDevice(name='intermediate_device', parent_device=pseudoclock.clockline)

    # Create a DigitalOut child of the DummyIntermediateDevice
    DigitalOut(
        name='digital_out', parent_device=intermediate_device, connection='port0/line0'
    )

    # Instantiate a Trigger for the camera
    Trigger(
        name='camera_trigger', 
        parent_device=intermediate_device, 
        connection='port0/line0'
    )

    # Initialize the Zelux Camera
    ZeluxCamera(
        name='zelux',
        parent_device=camera_trigger,
        connection='trigger',
        serial_number='18666',  # Serial number is now a required argument
        exposure_time_us=40000,
        image_width_pixels=1280,
        image_height_pixels=1024,
        offset_x=0,
        offset_y=0,
        roi=(0,0,1280,1024),
    )

if __name__ == '__main__':

    cxn_table()
    start()
    stop(1)
