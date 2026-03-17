#!/bin/bash
# Pi 수집기 서비스 중지

HOSTNAME=$(hostname)

if [ "$HOSTNAME" = "raspberrypi" ]; then
    SERVICE="lte-collector"
elif [ "$HOSTNAME" = "hanul" ]; then
    SERVICE="starlink-real-collector"
else
    echo "[ERROR] Unknown host: $HOSTNAME"
    exit 1
fi

echo "[STOP] $SERVICE"
sudo systemctl stop "$SERVICE"
echo "[DONE] $SERVICE stopped"
