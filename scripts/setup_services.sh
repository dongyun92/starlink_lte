#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${USER_NAME:-$(whoami)}"
BASE_DIR="${BASE_DIR:-$(pwd)}"
GROUND_DATA_DIR="${GROUND_DATA_DIR:-/home/${USER_NAME}/lte-ground-station-data}"
COLLECT_DATA_DIR="${COLLECT_DATA_DIR:-/home/${USER_NAME}/lte-collector-data}"

UNIT_GS="/etc/systemd/system/lte-ground-station.service"
UNIT_COL="/etc/systemd/system/lte-collector.service"

if [[ ! -f "${BASE_DIR}/systemd/lte-ground-station.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/lte-ground-station.service"
  exit 1
fi

if [[ ! -f "${BASE_DIR}/systemd/lte-collector.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/lte-collector.service"
  exit 1
fi

echo "[INFO] Using USER_NAME=${USER_NAME}"
echo "[INFO] Using BASE_DIR=${BASE_DIR}"

echo "[INFO] Stopping existing services (if any)"
sudo systemctl stop lte-ground-station.service || true
sudo systemctl stop lte-collector.service || true
sudo systemctl disable lte-ground-station.service || true
sudo systemctl disable lte-collector.service || true

# Remove old units
sudo rm -f "${UNIT_GS}" "${UNIT_COL}"

# Copy fresh units from repo
sudo cp "${BASE_DIR}/systemd/lte-ground-station.service" "${UNIT_GS}"
sudo cp "${BASE_DIR}/systemd/lte-collector.service" "${UNIT_COL}"

# Patch User/Group/paths to current user
sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_GS}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_GS}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_GS}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=/usr/bin/python3 ${BASE_DIR}/|" "${UNIT_GS}"
sudo sed -i "s|--data-dir /opt/lte-ground-station-data|--data-dir ${GROUND_DATA_DIR}|" "${UNIT_GS}"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_COL}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_COL}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_COL}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=/usr/bin/python3 ${BASE_DIR}/|" "${UNIT_COL}"
sudo sed -i "s|--data-dir /home/pi/lte-collector-data|--data-dir ${COLLECT_DATA_DIR}|" "${UNIT_COL}"

# Ensure data directories exist
mkdir -p "${GROUND_DATA_DIR}" "${COLLECT_DATA_DIR}"

# Reload and start
sudo systemctl daemon-reload
sudo systemctl reset-failed lte-ground-station.service || true
sudo systemctl reset-failed lte-collector.service || true

sudo systemctl enable lte-ground-station.service
sudo systemctl enable lte-collector.service

sudo systemctl start lte-ground-station.service
sudo systemctl start lte-collector.service

echo "[INFO] Services status:"
systemctl status lte-ground-station.service --no-pager
systemctl status lte-collector.service --no-pager
