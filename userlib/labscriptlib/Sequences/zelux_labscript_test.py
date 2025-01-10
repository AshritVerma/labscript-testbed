"""
zelux_labscript_test.py

A comprehensive test sequence for the Zelux camera implementation,
testing various features and capabilities through the labscript interface.
"""

from labscript import start, stop
from labscriptlib.example_apparatus.connection_table import cxn_table

###############################################################################
# TEST PARAMETERS
###############################################################################
# Camera settings to test
EXPOSURE_TIMES = [10000, 20000, 50000]  # microseconds
IMAGE_SIZES = [
    (1280, 1024),  # Full frame
    (640, 512),    # Half frame
]
ROI_TESTS = [
    (0, 0, 1280, 1024),    # Full sensor
    (320, 256, 960, 768),  # Center region
]

def run_camera_tests():
    """Run a series of camera configuration tests"""
    t = 0.0
    
    # Test 1: Basic image capture with different exposure times
    print("Test 1: Exposure time series")
    for exp_time in EXPOSURE_TIMES:
        zelux.exposure_time_us = exp_time  # Set attribute directly
        t += 0.1
        zelux.expose(t, f'exposure_test_{exp_time}us', 'image')
        t += exp_time/1e6 + 0.1  # Convert to seconds and add buffer
    
    # Test 2: Different image sizes
    print("Test 2: Image size series")
    for width, height in IMAGE_SIZES:
        zelux.image_width_pixels = width
        zelux.image_height_pixels = height
        t += 0.1
        zelux.expose(t, f'size_test_{width}x{height}', 'image')
        t += 0.2  # Buffer between shots
    
    # Test 3: ROI testing
    print("Test 3: ROI series")
    for x1, y1, x2, y2 in ROI_TESTS:
        zelux.roi = (x1, y1, x2, y2)  # Set ROI directly as a tuple
        t += 0.1
        zelux.expose(t, f'roi_test_{x1}_{y1}_{x2}_{y2}', 'image')
        t += 0.2  # Buffer between shots
    
    # Test 4: Rapid sequential captures
    print("Test 4: Rapid sequence")
    zelux.exposure_time_us = 10000  # Fast exposure
    for i in range(5):
        t += 0.02  # 20ms between frames
        zelux.expose(t, f'rapid_test_frame_{i}', 'image')
    
    return t

###############################################################################
# LABSCRIPT SEQUENCE
###############################################################################
if __name__ == '__main__':

    cxn_table()
    # Begin labscript sequence
    start()
    
    print("Starting Zelux camera test sequence")
    
    # Run all camera tests
    final_time = run_camera_tests()
    
    # End sequence
    stop(final_time + 0.1)  # Add final buffer
    
    print("Test sequence complete")
