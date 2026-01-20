#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${USER_NAME:-$(whoami)}"
BASE_DIR="${BASE_DIR:-$(pwd)}"
GROUND_DATA_DIR="${GROUND_DATA_DIR:-/home/${USER_NAME}/lte-ground-station-data}"
COLLECT_DATA_DIR="${COLLECT_DATA_DIR:-/home/${USER_NAME}/lte-collector-data}"
STARLINK_GRPC_DIR="${BASE_DIR}/starlink-grpc-tools"
VENV_DIR="${BASE_DIR}/.venv"
LTE_PYTHON_BIN="/usr/bin/python3"
STARLINK_PYTHON_BIN="/usr/bin/python3"

UNIT_GS="/etc/systemd/system/lte-ground-station.service"
UNIT_COL="/etc/systemd/system/lte-collector.service"
UNIT_SL_GS="/etc/systemd/system/starlink-ground-station.service"
UNIT_SL_SIM_COL="/etc/systemd/system/starlink-collector.service"
UNIT_SL_REAL_COL="/etc/systemd/system/starlink-real-collector.service"

if [[ ! -f "${BASE_DIR}/systemd/lte-ground-station.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/lte-ground-station.service"
  exit 1
fi

if [[ ! -f "${BASE_DIR}/systemd/lte-collector.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/lte-collector.service"
  exit 1
fi

if [[ ! -f "${BASE_DIR}/systemd/starlink-ground-station.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/starlink-ground-station.service"
  exit 1
fi

if [[ ! -f "${BASE_DIR}/systemd/starlink-collector.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/starlink-collector.service"
  exit 1
fi

if [[ ! -f "${BASE_DIR}/systemd/starlink-real-collector.service" ]]; then
  echo "[ERROR] Run this script inside the repo. Missing systemd/starlink-real-collector.service"
  exit 1
fi

echo "[INFO] Using USER_NAME=${USER_NAME}"
echo "[INFO] Using BASE_DIR=${BASE_DIR}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "[INFO] Creating venv and installing Python dependencies"
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -r "${BASE_DIR}/requirements.txt"
fi
STARLINK_PYTHON_BIN="${VENV_DIR}/bin/python"

if [[ ! -f "${STARLINK_GRPC_DIR}/dish_grpc_text.py" ]]; then
  if [[ -d "${STARLINK_GRPC_DIR}/archive-old-files" ]]; then
    echo "[INFO] Activating starlink-grpc-tools scripts from archive-old-files"
    cp -a "${STARLINK_GRPC_DIR}/archive-old-files/." "${STARLINK_GRPC_DIR}/"
  else
    echo "[INFO] starlink-grpc-tools not found. Cloning..."
    git clone https://github.com/sparky8512/starlink-grpc-tools "${STARLINK_GRPC_DIR}" || true
  fi
fi

if [[ -d "${STARLINK_GRPC_DIR}/archive-old-files" ]] && [[ ! -f "${STARLINK_GRPC_DIR}/dish_grpc_text.py" ]]; then
  echo "[INFO] Activating starlink-grpc-tools scripts from archive-old-files"
  cp -a "${STARLINK_GRPC_DIR}/archive-old-files/." "${STARLINK_GRPC_DIR}/"
fi

echo "[INFO] Stopping existing services (if any)"
sudo systemctl stop lte-ground-station.service || true
sudo systemctl stop lte-collector.service || true
sudo systemctl stop starlink-ground-station.service || true
sudo systemctl stop starlink-collector.service || true
sudo systemctl stop starlink-real-collector.service || true
sudo systemctl disable lte-ground-station.service || true
sudo systemctl disable lte-collector.service || true
sudo systemctl disable starlink-ground-station.service || true
sudo systemctl disable starlink-collector.service || true
sudo systemctl disable starlink-real-collector.service || true

# Remove old units
sudo rm -f "${UNIT_GS}" "${UNIT_COL}" "${UNIT_SL_GS}" "${UNIT_SL_SIM_COL}" "${UNIT_SL_REAL_COL}"

# Copy fresh units from repo
sudo cp "${BASE_DIR}/systemd/lte-ground-station.service" "${UNIT_GS}"
sudo cp "${BASE_DIR}/systemd/lte-collector.service" "${UNIT_COL}"
sudo cp "${BASE_DIR}/systemd/starlink-ground-station.service" "${UNIT_SL_GS}"
sudo cp "${BASE_DIR}/systemd/starlink-collector.service" "${UNIT_SL_SIM_COL}"
sudo cp "${BASE_DIR}/systemd/starlink-real-collector.service" "${UNIT_SL_REAL_COL}"

# Patch User/Group/paths to current user
sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_GS}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_GS}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_GS}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=${LTE_PYTHON_BIN} ${BASE_DIR}/|" "${UNIT_GS}"
sudo sed -i "s|--data-dir /opt/lte-ground-station-data|--data-dir ${GROUND_DATA_DIR}|" "${UNIT_GS}"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_COL}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_COL}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_COL}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=${LTE_PYTHON_BIN} ${BASE_DIR}/|" "${UNIT_COL}"
sudo sed -i "s|--data-dir /home/pi/lte-collector-data|--data-dir ${COLLECT_DATA_DIR}|" "${UNIT_COL}"

# Starlink services
STARLINK_GS_DATA_DIR="${STARLINK_GS_DATA_DIR:-/home/${USER_NAME}/starlink-ground-station-data}"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_SL_GS}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_SL_GS}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_SL_GS}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=${STARLINK_PYTHON_BIN} ${BASE_DIR}/|" "${UNIT_SL_GS}"
sudo sed -i "s|--data-dir /home/pi/starlink-ground-station-data|--data-dir ${STARLINK_GS_DATA_DIR}|" "${UNIT_SL_GS}"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_SL_SIM_COL}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_SL_SIM_COL}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_SL_SIM_COL}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=${STARLINK_PYTHON_BIN} ${BASE_DIR}/|" "${UNIT_SL_SIM_COL}"

sudo sed -i "s/User=pi/User=${USER_NAME}/" "${UNIT_SL_REAL_COL}"
sudo sed -i "s/Group=pi/Group=${USER_NAME}/" "${UNIT_SL_REAL_COL}"
sudo sed -i "s|WorkingDirectory=/home/pi/starlink_lte|WorkingDirectory=${BASE_DIR}|" "${UNIT_SL_REAL_COL}"
sudo sed -i "s|ExecStart=/usr/bin/python3 /home/pi/starlink_lte/|ExecStart=${STARLINK_PYTHON_BIN} ${BASE_DIR}/|" "${UNIT_SL_REAL_COL}"

# Ensure data directories exist
STARLINK_SIM_DATA_DIR="${STARLINK_SIM_DATA_DIR:-/home/${USER_NAME}/starlink-sim-data}"
mkdir -p "${GROUND_DATA_DIR}" "${COLLECT_DATA_DIR}" "${STARLINK_GS_DATA_DIR}" "${STARLINK_SIM_DATA_DIR}"

# Reload and start
sudo systemctl daemon-reload
sudo systemctl reset-failed lte-ground-station.service || true
sudo systemctl reset-failed lte-collector.service || true
sudo systemctl reset-failed starlink-ground-station.service || true
sudo systemctl reset-failed starlink-collector.service || true
sudo systemctl reset-failed starlink-real-collector.service || true

sudo systemctl enable lte-ground-station.service
sudo systemctl enable lte-collector.service
sudo systemctl enable starlink-ground-station.service
sudo systemctl enable starlink-collector.service
sudo systemctl enable starlink-real-collector.service

sudo systemctl start lte-ground-station.service
sudo systemctl start lte-collector.service
sudo systemctl start starlink-ground-station.service
sudo systemctl start starlink-collector.service
sudo systemctl start starlink-real-collector.service

echo "[INFO] Services status:"
systemctl status lte-ground-station.service --no-pager
systemctl status lte-collector.service --no-pager
systemctl status starlink-ground-station.service --no-pager
systemctl status starlink-collector.service --no-pager
systemctl status starlink-real-collector.service --no-pager
