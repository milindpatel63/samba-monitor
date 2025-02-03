from flask import Flask, render_template, jsonify
import subprocess
import re
from datetime import datetime
import threading
import time
import requests
import os
app = Flask(__name__)

last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
notifications = []
current_status = {'sessions': [], 'services': [], 'locked_files': []}
# Get values from environment variables
# Discord webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
# List of IPs to exclude from notifications
EXCLUDED_IPS = os.getenv("EXCLUDED_IPS", "").split(",")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5069))

def send_discord_notification(message):
    """Sends a message to Discord via webhook."""
    payload = {
        "content": message
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification to Discord: {e}")

def parse_smbstatus():
    try:
        result = subprocess.run(
            ['sudo', 'smbstatus'],
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        print("Error running smbstatus:", e)
        return {'sessions': [], 'services': [], 'locked_files': []}

    output = result.splitlines()
    data = {'sessions': [], 'services': [], 'locked_files': []}
    current_section = None

    # Regex for sessions lines
    session_pattern = re.compile(
        r'^(\d+)\s+'             # PID
        r'(\S+)\s+'              # Username
        r'(\S+)\s+'              # Group
        r'(\S+)\s+'              # Machine (first part)
        r'\(ipv4:(\d+\.\d+\.\d+\.\d+):\d+\)\s+'  # (ipv4:IP:port)
        r'(\S+)\s+'              # Protocol
        r'(.+)$'                 # Encryption (and Signing details)
    )
    # Regex for services lines
    service_pattern = re.compile(
        r'^(\S+)\s+'             # Service name
        r'(\d+)\s+'              # PID
        r'(\S+)\s+'              # Machine
        r'(.+?)\s+'              # Connected at (non-greedy)
        r'(\S+)\s+'              # Encryption
        r'(\S+)$'                # Signing
    )
    # New regex for locked files lines (captures 9 columns)
    locked_files_pattern = re.compile(
        r'^(\d+)\s+'            # Pid
        r'(\S+)\s+'             # User
        r'(\S+)\s+'             # DenyMode
        r'(\S+)\s+'             # Access
        r'(\S+)\s+'             # R/W
        r'(\S+)\s+'             # Oplock
        r'(.+?)\s{2,}'          # SharePath (lazy match until two or more spaces)
        r'(.+?)\s{2,}'          # Name (lazy match until two or more spaces)
        r'(.+)$'                # Time (rest of line)
    )

    for line in output:
        stripped = line.lstrip()
        if stripped.startswith('PID') and 'Username' in stripped:
            current_section = 'sessions'
            continue
        elif stripped.startswith('Service') and 'pid' in stripped:
            current_section = 'services'
            continue
        elif stripped.startswith('Locked files:'):
            current_section = 'locked_files'
            continue

        if not stripped or all(ch == '-' for ch in stripped):
            continue

        if current_section == 'sessions':
            if stripped[0].isdigit():
                match = session_pattern.match(stripped)
                if match:
                    pid, username, group, machine, ip, protocol, encryption = match.groups()
                    data['sessions'].append({
                        'pid': pid,
                        'username': username,
                        'group': group,
                        'client': ip,
                        'protocol': protocol,
                        'encryption': encryption.strip()
                    })
        elif current_section == 'services':
            match = service_pattern.match(stripped)
            if match:
                service, pid, machine, connected_at, encryption, signing = match.groups()
                data['services'].append({
                    'service': service,
                    'pid': pid,
                    'machine': machine,
                    'connected_at': connected_at.strip(),
                    'encryption': encryption,
                    'signing': signing
                })
        elif current_section == 'locked_files':
            # Use our dedicated regex for locked files
            match = locked_files_pattern.match(stripped)
            if match:
                pid, user, deny_mode, access, rw, oplock, sharepath, name, time_str = match.groups()
                data['locked_files'].append({
                    'pid': pid,
                    'user': user,
                    'deny_mode': deny_mode,
                    'access': access,
                    'rw': rw,
                    'oplock': oplock,
                    'sharepath': sharepath,
                    'name': name,
                    'time': time_str.strip()
                })

    return data

def monitor_changes():
    global current_status, last_checked, notifications
    previous_clients = set()
    
    while True:
        time.sleep(10)
        new_data = parse_smbstatus()
        current_clients = set(s['client'] for s in new_data['sessions'])
        
        new_connections = current_clients - previous_clients
        if new_connections:
            for client in new_connections:
                notifications.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'message': f"New connection from {client}"
                })
                # Exclude specific IPs
                if client not in EXCLUDED_IPS:
                    # Find the session details for this client
                    session_info = next((s for s in new_data['sessions'] if s['client'] == client), None)
                    session_username = session_info['username'] if session_info else 'Unknown'
                    
                    # Find the service details associated with this session
                    service_info = next((s for s in new_data['services'] if s['pid'] == session_info['pid']), None)
                    service_name = service_info['service'] if service_info else 'Unknown Service'

                    # Find any locked files associated with this session
                    locked_files = [lf for lf in new_data['locked_files'] if lf['pid'] == session_info['pid']]
                    locked_file_names = ", ".join([lf['name'] for lf in locked_files]) if locked_files else 'No locked files'

                    # Create a message including all details
                    message = (f"New SMB Connection from {client}\n"
                               f"Username: {session_username}\n"
                               f"Service: {service_name}\n"
                               f"Locked files: {locked_file_names}")
                    # Send notification to Discord
                    send_discord_notification(message)
        current_status = new_data
        previous_clients = current_clients
        last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route('/')
def dashboard():
    return render_template(
        'dashboard.html',
        data=current_status,
        last_checked=last_checked,
        notifications=notifications[-5:]
    )

@app.route('/refresh_data', methods=['GET'])
def refresh_data():
    new_data = parse_smbstatus()
    return jsonify(new_data)

if __name__ == '__main__':
    current_status = parse_smbstatus()
    monitor_thread = threading.Thread(target=monitor_changes, daemon=True)
    monitor_thread.start()
    app.run(host='0.0.0.0', port=FLASK_PORT)
