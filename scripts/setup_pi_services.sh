#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${USER_NAME:-hanul}"
BASE_DIR="/home/${USER_NAME}/starlink_lte"
GROUND_DATA_DIR="/home/${USER_NAME}/lte-ground-station-data"
COLLECT_DATA_DIR="/home/${USER_NAME}/lte-collector-data"

UNIT_GS="/etc/systemd/system/lte-ground-station.service"
UNIT_COL="/etc/systemd/system/lte-collector.service"
UNIT_SL_GS="/etc/systemd/system/starlink-ground-station.service"
UNIT_SL_COL="/etc/systemd/system/starlink-collector.service"

if [[ ! -d "${BASE_DIR}" ]]; then
  echo "[ERROR] Base directory not found: ${BASE_DIR}"
  exit 1
fi

cd "${BASE_DIR}"

echo "[INFO] Stopping existing services (if any)"
sudo systemctl stop lte-ground-station.service || true
sudo systemctl stop lte-collector.service || true
sudo systemctl stop starlink-ground-station.service || true
sudo systemctl stop starlink-collector.service || true
sudo systemctl disable lte-ground-station.service || true
sudo systemctl disable lte-collector.service || true
sudo systemctl disable starlink-ground-station.service || true
sudo systemctl disable starlink-collector.service || true

# Remove old units
sudo rm -f "${UNIT_GS}" "${UNIT_COL}" "${UNIT_SL_GS}" "${UNIT_SL_COL}"

# Copy fresh units from repo
sudo cp "${BASE_DIR}/systemd/lte-ground-station.service" "${UNIT_GS}"
sudo cp "${BASE_DIR}/systemd/lte-collector.service" "${UNIT_COL}"
sudo cp "${BASE_DIR}/systemd/starlink-ground-station.service" "${UNIT_SL_GS}"
sudo cp "${BASE_DIR}/systemd/starlink-collector.service" "${UNIT_SL_COL}"

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

# Starlink services
STARLINK_DATA_DIR="/home/${USER_NAME}/starlink-data"
STARLINK_GS_DATA_DIR="/home/${USER_NAME}/starlink-ground-station-data"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_SL_GS}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_SL_GS}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_SL_GS}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=/usr/bin/python3 ${BASE_DIR}/|" "${UNIT_SL_GS}"
sudo sed -i "s|--data-dir /home/pi/starlink-ground-station-data|--data-dir ${STARLINK_GS_DATA_DIR}|" "${UNIT_SL_GS}"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_SL_COL}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_SL_COL}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_SL_COL}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=/usr/bin/python3 ${BASE_DIR}/|" "${UNIT_SL_COL}"
sudo sed -i "s|--data-dir /home/pi/starlink-data|--data-dir ${STARLINK_DATA_DIR}|" "${UNIT_SL_COL}"

# Ensure data directories exist
mkdir -p "${GROUND_DATA_DIR}" "${COLLECT_DATA_DIR}" "${STARLINK_DATA_DIR}" "${STARLINK_GS_DATA_DIR}"

# Reload and start
sudo systemctl daemon-reload
sudo systemctl reset-failed lte-ground-station.service || true
sudo systemctl reset-failed lte-collector.service || true
sudo systemctl reset-failed starlink-ground-station.service || true
sudo systemctl reset-failed starlink-collector.service || true

sudo systemctl enable lte-ground-station.service
sudo systemctl enable lte-collector.service
sudo systemctl enable starlink-ground-station.service
sudo systemctl enable starlink-collector.service

sudo systemctl start lte-ground-station.service
sudo systemctl start lte-collector.service
sudo systemctl start starlink-ground-station.service
sudo systemctl start starlink-collector.service

echo "[INFO] Services status:"
systemctl status lte-ground-station.service --no-pager
systemctl status lte-collector.service --no-pager
systemctl status starlink-ground-station.service --no-pager
systemctl status starlink-collector.service --no-pager
