# Use an official Python runtime as a parent image.
FROM python:3.10-slim

# Install system dependencies: samba-client (for smbstatus) and sudo.
RUN apt-get update && apt-get install -y \
    samba-client \
    sudo \
 && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . /app

# Configure passwordless sudo for smbstatus inside the container.
# (Adjust the path to smbstatus if needed.)
RUN echo "root ALL=(ALL) NOPASSWD: /usr/bin/smbstatus" > /etc/sudoers.d/smbstatus && chmod 0440 /etc/sudoers.d/smbstatus

# Set a default port in case it's not provided at runtime
ENV FLASK_PORT=5069

# Expose the port dynamically
EXPOSE $FLASK_PORT

# Use exec form of CMD to allow environment variables to be substituted
CMD ["sh", "-c", "python samba_monitor_docker.py"]
