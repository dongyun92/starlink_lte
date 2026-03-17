#!/bin/bash
# Pi 수집기 서비스 재시작

HOSTNAME=$(hostname)

if [ "$HOSTNAME" = "raspberrypi" ]; then
    SERVICE="lte-collector"
elif [ "$HOSTNAME" = "hanul" ]; then
    SERVICE="starlink-real-collector"
else
    echo "[ERROR] Unknown host: $HOSTNAME"
    exit 1
fi

echo "[RESTART] $SERVICE"
sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE"
sleep 1
sudo journalctl -u "$SERVICE" --no-pager -n 20
