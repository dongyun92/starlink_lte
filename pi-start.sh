#!/bin/bash
# Pi 수집기 서비스 시작
# Pi-1 (raspberrypi): lte-collector
# Pi-2 (hanul):       starlink-real-collector

HOSTNAME=$(hostname)

if [ "$HOSTNAME" = "raspberrypi" ]; then
    SERVICE="lte-collector"
elif [ "$HOSTNAME" = "hanul" ]; then
    SERVICE="starlink-real-collector"
else
    echo "[ERROR] Unknown host: $HOSTNAME"
    exit 1
fi

echo "[START] $SERVICE"
sudo systemctl start "$SERVICE"
sleep 1
sudo systemctl status "$SERVICE" --no-pager -n 5
