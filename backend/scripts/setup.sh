#!/bin/bash
# BAURSAK ARM — Raspberry Pi Setup
# Run once: chmod +x setup.sh && ./setup.sh

set -e

echo "=== BAURSAK ARM SETUP ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install -y python3-venv python3-pip

# Create virtual environment
cd "$(dirname "$0")/.."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Add user to dialout group (Serial access)
sudo usermod -aG dialout $USER

# Create systemd service for auto-start
sudo tee /etc/systemd/system/baursak-arm.service > /dev/null << 'EOF'
[Unit]
Description=Baursak Arm Server
After=network.target

[Service]
Type=simple
User=robolab
WorkingDirectory=/home/robolab/baursak-arm/backend
ExecStart=/home/robolab/baursak-arm/backend/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable baursak-arm.service

echo ""
echo "=== SETUP COMPLETE ==="
echo "Reboot for Serial permissions, then:"
echo "  sudo systemctl start baursak-arm"
echo "  Open http://$(hostname -I | awk '{print $1}'):8080"
