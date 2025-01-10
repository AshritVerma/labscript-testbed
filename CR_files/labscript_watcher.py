import http.server
import socketserver
import json
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import configparser
import sys
import subprocess
from collections import deque
import time

EXPECTED_PYTHON = 'C:\\Users\\cleve\\CR_labscript\\Scripts\\python.exe'
if not sys.executable.endswith('CR_labscript\\Scripts\\python.exe'):
    print(f"Restarting with correct Python environment: {EXPECTED_PYTHON}")
    try:
        subprocess.run([EXPECTED_PYTHON, __file__], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script in CR_labscript environment: {e}")
        sys.exit(1)
    sys.exit(0)

config = configparser.ConfigParser()
CONFIG_PATH = r'C:\Users\cleve\labscript-suite\labconfig\JARVIS-STUDIO.ini'

try:
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found at: {CONFIG_PATH}")
        sys.exit(1)
        
    config.read(CONFIG_PATH)
    WATCH_DIR = config['DEFAULT']['experiment_shot_storage']
    print(f"Watching directory: {WATCH_DIR}")
except KeyError:
    print(f"Error: 'experiment_shot_storage' not found in config file: {CONFIG_PATH}")
    print("Please ensure the config file contains:")
    print("[DEFAULT]")
    print("experiment_shot_storage = <your_path>")
    sys.exit(1)
except Exception as e:
    print(f"Error reading config file: {e}")
    sys.exit(1)


script_history = deque(maxlen=10)
currently_running_script = None
status = "idle"
last_change_time = datetime.now().isoformat()

# Configuration for completion detection
CHECK_INTERVAL = 0.5  # How often to check file mod time
STABLE_PERIOD = 1.0    # How long file must remain stable (no modifications) to consider complete

class ScriptRecord:
    def __init__(self, filename):
        self.filename = filename
        self.start_time = datetime.now()
        self.end_time = None
        self.status = "running"
        
    def complete(self):
        self.end_time = datetime.now()
        self.status = "complete"
        
    def to_dict(self):
        return {
            "filename": self.filename,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "duration": str(self.end_time - self.start_time) if self.end_time else "ongoing"
        }

class ShotEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        global currently_running_script, status, last_change_time
        if event.is_directory:
            return
        if event.src_path.endswith('.h5'):
            filename = os.path.basename(event.src_path)
            currently_running_script = ScriptRecord(filename)
            status = "running"
            last_change_time = datetime.now().isoformat()
            script_history.appendleft(currently_running_script)

    # We keep on_deleted logic if ever needed, but likely won't trigger if not deleting h5.
    def on_deleted(self, event):
        global currently_running_script, status, last_change_time
        if event.is_directory:
            return
        if event.src_path.endswith('.h5'):
            if currently_running_script and os.path.basename(event.src_path) == currently_running_script.filename:
                currently_running_script.complete()
                status = "complete"
                last_change_time = datetime.now().isoformat()
                currently_running_script = None

class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html = """
            <html>
            <head>
                <title>Labscript Shot Monitor</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .current {{ background: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .history {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                    .running {{ color: #2196F3; }}
                    .complete {{ color: #4CAF50; }}
                    .idle {{ color: #757575; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    h2 {{ color: #333; }}
                    .refresh-note {{ font-size: 0.8em; color: #666; margin-top: 20px; }}
                </style>
                <script>
                    function refreshPage() {{
                        location.reload();
                    }}
                    setInterval(refreshPage, 5000);  // Refresh every 5 seconds
                </script>
            </head>
            <body>
                <h2>Current Status</h2>
                <div class="current">
                    <p>Status: <span class="{}">{}</span></p>
                    {}
                </div>
                
                <h2>Script History</h2>
                <div class="history">
                    <table>
                        <tr>
                            <th>Script Name</th>
                            <th>Start Time</th>
                            <th>End Time</th>
                            <th>Duration</th>
                            <th>Status</th>
                        </tr>
                        {}
                    </table>
                </div>
                <p class="refresh-note">Page auto-refreshes every 5 seconds</p>
            </body>
            </html>
            """

            current_info = ""
            if currently_running_script:
                current_info = f"""
                <p>Running: {currently_running_script.filename}</p>
                <p>Started: {currently_running_script.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                """

            history_rows = ""
            for script in script_history:
                history_rows += f"""
                <tr>
                    <td>{script.filename}</td>
                    <td>{script.start_time.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{script.end_time.strftime('%Y-%m-%d %H:%M:%S') if script.end_time else 'Running'}</td>
                    <td>{script.to_dict()['duration']}</td>
                    <td class="{script.status}">{script.status}</td>
                </tr>
                """

            html = html.format(
                status.lower(),
                status.upper(),
                current_info,
                history_rows
            )
            
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def completion_monitor():
    """
    Periodically checks if the currently running script’s h5 file has stopped changing.
    If the file hasn't been modified for STABLE_PERIOD seconds, mark the script as complete.
    """
    global currently_running_script, status, last_change_time

    last_mod_time = None
    stable_start = None

    while True:
        if currently_running_script and status == "running":
            file_path = os.path.join(WATCH_DIR, currently_running_script.filename)
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                if last_mod_time is None or mtime != last_mod_time:
                    # Modification time changed, reset stable_start
                    stable_start = datetime.now()
                    last_mod_time = mtime
                else:
                    # No change in mod time
                    elapsed = (datetime.now() - stable_start).total_seconds()
                    if elapsed >= STABLE_PERIOD:
                        # Consider run complete
                        currently_running_script.complete()
                        status = "complete"
                        last_change_time = datetime.now().isoformat()
                        currently_running_script = None
            else:
                # File disappeared before being stable?
                # This might be handled by on_deleted, but just in case:
                if currently_running_script:
                    currently_running_script.complete()
                    status = "complete"
                    last_change_time = datetime.now().isoformat()
                    currently_running_script = None
        else:
            # Reset checks if no running script
            last_mod_time = None
            stable_start = None
        
        time.sleep(CHECK_INTERVAL)

def run_server():
    PORT = 8000
    httpd = socketserver.TCPServer(("", PORT), StatusHandler)
    print(f"Serving status info at http://localhost:{PORT}/status")
    httpd.serve_forever()

if __name__ == "__main__":
    event_handler = ShotEventHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()

    # Start the completion monitor thread
    monitor_thread = threading.Thread(target=completion_monitor, daemon=True)
    monitor_thread.start()

    try:
        run_server()
    finally:
        observer.stop()
        observer.join()
