#!/bin/bash
# Script to set up systemd service for CBSE App (WSL/Linux)

set -e

# Ensure running inside the project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CURRENT_USER=$(whoami)
SERVICE_NAME="cbse-app"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=== Setting up Systemd Service for CBSE App ==="
echo "Project Directory: $SCRIPT_DIR"
echo "Running User:      $CURRENT_USER"

# Create dynamic service file with correct user and path
cat <<EOF > /tmp/${SERVICE_NAME}.service
[Unit]
Description=Class X Education Platform (CBSE App)
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/bin/bash ${SCRIPT_DIR}/start.sh \${MODE:-mesh}
Restart=always
RestartSec=5
Environment=PORT=9090
Environment=UVICORN_WORKERS=1
Environment=WORKER_COUNT=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Copying service file to ${SERVICE_FILE} (requires sudo)..."
sudo cp /tmp/${SERVICE_NAME}.service ${SERVICE_FILE}
rm /tmp/${SERVICE_NAME}.service

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling service to start on boot..."
sudo systemctl enable ${SERVICE_NAME}

echo "Starting service..."
sudo systemctl restart ${SERVICE_NAME}

echo "Checking service status..."
sudo systemctl status ${SERVICE_NAME} --no-pager

echo ""
echo "=== Setup complete! Service is configured to run 24/7 ==="
echo "To view logs, run: journalctl -u ${SERVICE_NAME} -f"
echo "To stop the service, run: sudo systemctl stop ${SERVICE_NAME}"
echo "To start the service, run: sudo systemctl start ${SERVICE_NAME}"
EOF
