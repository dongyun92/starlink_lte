# Starlink LTE Setup Guide (Collector + Ground Station + Tailscale)

This guide works on any PC. It uses your current user and repo path automatically.

## 1) Install from GitHub
```sh
cd ~
git clone https://github.com/dongyun92/starlink_lte.git
cd ~/starlink_lte
```

## 2) One-shot service setup (recommended)
```sh
chmod +x scripts/setup_services.sh
./scripts/setup_services.sh
```

If your repo path is different:
```sh
BASE_DIR=/path/to/starlink_lte ./scripts/setup_services.sh
```

If your username is different:
```sh
USER_NAME=youruser ./scripts/setup_services.sh
```

## 3) Check status
```sh
systemctl status lte-collector.service --no-pager
systemctl status lte-ground-station.service --no-pager
systemctl status starlink-collector.service --no-pager
systemctl status starlink-ground-station.service --no-pager
systemctl status starlink-real-collector.service --no-pager
```

## 4) Port map (what connects to what)
LTE:
- Collector API: `8897`
- Ground station dashboard: `8079`

Starlink:
- Simulator collector API: `8899`
- Real gRPC collector API: `9201` (this service talks to dish at `192.168.100.1:9200`)
- Ground station dashboard: `8080`

Dashboard input examples:
- Starlink simulator: `http://<LAN-IP>:8899`
- Starlink real: `http://<LAN-IP>:9201`

## 5) Dashboard access (LAN)
```sh
hostname -I
```
Open in browser:
```
http://<LAN-IP>:8079/
```

Starlink dashboard:
```
http://<LAN-IP>:8080/
```

## 6) CSV storage path
Default:
```
/home/<user>/lte-collector-data
```

## 7) Tailscale for remote access
### Install on Raspberry Pi
```sh
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### Get Tailscale IP
```sh
tailscale ip -4
```

### Install on your PC/phone
- Install Tailscale app
- Login with the same account

### Access dashboard
```
http://<tailscale-ip>:8079/
```

Starlink:
```
http://<tailscale-ip>:8080/
```

## Notes
- If you only want the collector on the device, disable ground station:
  ```sh
  sudo systemctl disable --now lte-ground-station.service
  ```
- If you only want ground station, disable collector:
  ```sh
  sudo systemctl disable --now lte-collector.service
  ```
- Starlink services can be disabled the same way:
  ```sh
  sudo systemctl disable --now starlink-ground-station.service
  sudo systemctl disable --now starlink-collector.service
  ```
