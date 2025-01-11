"""
zelux_labscript_test.py

A comprehensive test sequence for the Zelux camera implementation,
testing various features and capabilities through the labscript interface.
"""

from labscript import start, stop, add_time_marker
from labscriptlib.example_apparatus.connection_table import cxn_table

def run_camera_tests():
    """Run a series of camera configuration tests"""
    t = 0.0
    
    # Test 1: Basic image capture with different exposure times
    print("Test 1: Exposure time series")
    for exp_time in [10000, 20000, 50000]:  # microseconds
        add_time_marker(t, f"Exposure test: {exp_time}us")
        t += 0.1
        zelux.expose(t, f'exposure_test_{exp_time}us', 'image', trigger_duration=0.1)
        t += 0.2  # Buffer between shots
    
    # Test 2: Different ROI settings
    print("Test 2: ROI series")
    roi_tests = [
        (0, 0, 1280, 1024),    # Full sensor
        (320, 256, 960, 768),  # Center region
    ]
    
    for x1, y1, x2, y2 in roi_tests:
        add_time_marker(t, f"ROI test: ({x1},{y1},{x2},{y2})")
        t += 0.1
        zelux.expose(t, f'roi_test_{x1}_{y1}_{x2}_{y2}', 'image', trigger_duration=0.1)
        t += 0.2  # Buffer between shots
    
    # Test 3: Rapid sequential captures
    print("Test 3: Rapid sequence")
    add_time_marker(t, "Starting rapid sequence")
    
    # Calculate minimum safe time between triggers
    trigger_duration = 0.1  # seconds
    buffer_time = 0.02     # seconds
    min_spacing = trigger_duration + buffer_time
    
    for i in range(5):
        t += min_spacing  # Ensure enough time between triggers
        zelux.expose(t, f'rapid_test_frame_{i}', 'image', trigger_duration=trigger_duration)
    
    return t

if __name__ == '__main__':
    # Initialize connection table
    cxn_table()
    
    # Begin labscript sequence
    start()
    
    print("Starting Zelux camera test sequence")
    
    # Run all camera tests
    final_time = run_camera_tests()
    
    # End sequence
    stop(final_time + 0.1)  # Add final buffer
    
    print("Test sequence complete")
