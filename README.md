# Samba Connection Monitor

This is a Flask-based web application that monitors Samba (SMB) connections using `smbstatus` and sends notifications to Discord and/or ntfy when a new client connects. It also provides a simple web dashboard to display active sessions, services, and locked files.

![Screenshot.](/sambasharemonitor.jpeg)

## Features
- Monitors active Samba connections using `smbstatus`.
- Sends notifications to Discord and/or ntfy when a new client connects.
- Displays session details, services, and locked files in a web dashboard.
- Allows configuration via environment variables.
- Runs inside a Docker container.

## Environment Variables
| Variable          | Description                                  | Default |
|------------------|----------------------------------|---------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for notifications (optional) | `""` (empty) |
| `NTFY_TOPIC_URL` | ntfy topic URL for notifications (optional) | `""` (empty) |
| `EXCLUDED_IPS`   | Comma-separated list of IPs to exclude from notifications | `""` (empty) |
| `FLASK_PORT`     | Port for the Flask web server | `5069` |

## Installation

### Running Locally

Since smbstatus requires sudo, you might have to exclude the user you are running the flask app with from sudo.
Run
```
sudo visudo
```
and put this at the end of the file
```
your_username ALL=(ALL) NOPASSWD: /usr/bin/smbstatus
```
Replace `your_username` with the user you are running the flask app with.

Ensure you have Python 3.10+ installed.

```sh
# Clone the repository
git clone https://github.com/milindpatel63/samba-monitor.git
cd samba-monitor

# Install dependencies
pip install -r requirements.txt

# Run the application
FLASK_PORT=5069 DISCORD_WEBHOOK_URL="your_webhook_url" NTFY_TOPIC_URL="https://ntfy.sh/mytopic" EXCLUDED_IPS="192.168.1.1,192.168.1.2" python samba_monitor.py
```

The application will start on `http://0.0.0.0:5069` by default.

Note: The application checks for new connections every 30 seconds by default. To change this interval, modify the `time.sleep(30)` value in line 192 of `samba_monitor.py`.

### Running with Docker

Since docker can't run smbstatus command on the host. So you'll have to use a script running on the host to pass output via a txt file inside docker.

Put smbstatus_listener.sh somewhere on your host and run it with cron every minute.

Make it executable
```
chmod +x /path/to/smbstatus_listener.sh
```
Cron command
```
* * * * * /path/to/smbstatus_listener.sh
```

#### Run the Container
```sh
docker run -d \
  -e FLASK_PORT=5069 \
  -e DISCORD_WEBHOOK_URL=your_webhook_url \
  -e NTFY_TOPIC_URL=https://ntfy.sh/mytopic \
  -e EXCLUDED_IPS=192.168.1.1,192.168.1.2 \
  -p 5069:5069 \
  -v /tmp/smbstatus_output.txt:/tmp/smbstatus_output.txt \
  --name samba-monitor \
  milindpatel63/samba-monitor:latest
```
Note:

    The Docker container checks for updates based on the interval set in samba_monitor_docker.py (line 194). Modify this value to adjust how often the app refreshes its data and sends notifications.

    The actual data from smbstatus is updated according to the cron schedule (every minute by default). Ensure the cron job's interval aligns with your desired data refresh rate.

### Docker Compose
Create a `docker-compose.yml` file:
```yaml
version: '3.8'
services:
  samba-monitor:
    image: milindpatel63/samba-monitor:latest
    container_name: samba-monitor
    ports:
      - "5069:5069"
    environment:
      - FLASK_PORT=5069
      - DISCORD_WEBHOOK_URL=your_webhook_url
      - NTFY_TOPIC_URL=https://ntfy.sh/mytopic  # Optional
      - EXCLUDED_IPS=192.168.1.1,192.168.1.2
    volumes:
      - /tmp/smbstatus_output.txt:/tmp/smbstatus_output.txt
    restart: unless-stopped
    healthcheck:
      test:
        - CMD-SHELL
        - curl http://localhost:5069/health | grep ok
      interval: 60s
      timeout: 30s
      retries: 2
```
Run the application with:
```sh
docker-compose up -d
```
## API Endpoints

### GET `/refresh_data`
Returns the latest parsed `smbstatus` output as JSON.

### GET `/health`
Returns a simple healthcheck.
Can be used in something like Uptime Kuma for running a healthcheck.

### Web Dashboard
Visit `http://localhost:5069/` to view the dashboard with active connections and notifications.

## Contributing
Feel free to fork the project, submit issues, and contribute via pull requests!

## License
This project is licensed under the MIT License.

