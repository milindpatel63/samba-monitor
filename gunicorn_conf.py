# gunicorn_conf.py
import threading
from samba_monitor_docker import monitor_changes  # Replace 'your_app_module' with your actual module name

def post_fork(server, worker):
    # Start the monitoring thread in each worker process
    monitor_thread = threading.Thread(target=monitor_changes, daemon=True)
    monitor_thread.start()