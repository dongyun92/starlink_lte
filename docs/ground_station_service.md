# LTE Ground Station Service Setup (Raspberry Pi)

## 1) Copy systemd units
```sh
sudo cp /home/pi/starlink_lte/systemd/lte-ground-station.service /etc/systemd/system/
```

Optional (collector on same Pi):
```sh
sudo cp /home/pi/starlink_lte/systemd/lte-collector.service /etc/systemd/system/
```

## 2) Reload and enable
```sh
sudo systemctl daemon-reload
sudo systemctl enable lte-ground-station.service
sudo systemctl start lte-ground-station.service
```

Optional (collector):
```sh
sudo systemctl enable lte-collector.service
sudo systemctl start lte-collector.service
```

## 3) Check status
```sh
systemctl status lte-ground-station.service --no-pager
journalctl -u lte-ground-station.service -f
```

## 4) Firewall (UFW)
```sh
sudo ufw allow 8079/tcp
sudo ufw status
```

## 5) Router port forward
Forward external TCP port 8079 -> Raspberry Pi LAN IP 8079.

## 6) Verify externally
- LAN: http://<pi-lan-ip>:8079/
- WAN: http://<public-ip>:8079/

## Notes
- If your install path is not `/home/pi/starlink_lte`, edit the unit file paths.
- If you use a different serial port or interval, update `lte-collector.service`.
