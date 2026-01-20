# Starlink + LTE Dual Network Monitoring System

Aircraft-grade dual network monitoring system for Starlink and LTE connectivity.

## 🚀 Quick Start for Raspberry Pi

### Prerequisites
- Raspberry Pi 4 (4GB+ RAM recommended)
- Quectel EC25/EC21 LTE Module (USB)
- Starlink Dish with Ethernet connection
- Internet connection for initial setup

### Installation (Aircraft/Drone Deployment)

```bash
# 1. Clone repository
git clone https://github.com/dongyun92/starlink_lte.git
cd starlink_lte

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install flask pyserial requests grpcio grpcio-tools

# 4. Create data directories
mkdir -p lte-data starlink-data logs
```

### Running Services

#### Option 1: LTE Collector Only (For Aircraft)
```bash
# Start LTE data collector
python lte_remote_collector_en.py \
  --data-dir ./lte-data \
  --control-port 8897 \
  --serial-port /dev/ttyUSB0
```

#### Option 2: Starlink Collector Only
```bash
# Start Starlink data collector
python starlink-grpc-tools/test_remote_collector.py \
  --data-dir ./starlink-data \
  --control-port 8899
```

#### Option 3: Both Collectors (Dual Network)
```bash
# Start both in separate terminals or use screen
screen -dmS lte python lte_remote_collector_en.py
screen -dmS starlink python starlink-grpc-tools/test_remote_collector.py
```

## 📡 System Architecture

### Aircraft/Drone (Raspberry Pi)
- **LTE Collector** (Port 8897): Collects data from LTE module via AT commands
- **Starlink Collector** (Port 8899): Collects data from Starlink via gRPC
- **Data Storage**: CSV files with 10-minute rotation
- **API Endpoints**: REST API for remote monitoring

### Ground Station (Optional - PC/Server)
- **LTE Dashboard** (Port 8079): Real-time monitoring interface
- **Starlink Dashboard** (Port 8080): Real-time monitoring interface
- **Database**: SQLite for long-term storage

## 🔌 Hardware Setup

### LTE Module Connection
```
Raspberry Pi USB → Quectel EC25/EC21
Default Serial Port: /dev/ttyUSB0
Baudrate: 115200
```

### Starlink Connection
```
Raspberry Pi Ethernet → Starlink Router
gRPC Endpoint: 192.168.100.1:9200
```

## 📊 API Endpoints

### LTE Collector (Port 8897)
- `GET /status` - Get collector status
- `POST /start` - Start data collection
- `POST /stop` - Stop data collection
- `GET /data/recent` - Get recent data points
- `GET /data/files` - List CSV files
- `GET /data/download/<filename>` - Download CSV file

### Starlink Collector (Port 8899)
- Same endpoints as LTE Collector

## 🛠️ Systemd Service Setup

### Create service file
```bash
sudo nano /etc/systemd/system/lte-collector.service
```

```ini
[Unit]
Description=LTE Data Collector
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/starlink_lte
ExecStart=/home/pi/starlink_lte/venv/bin/python /home/pi/starlink_lte/lte_remote_collector_en.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable lte-collector
sudo systemctl start lte-collector
sudo systemctl status lte-collector
```

## 📈 Data Format

### LTE Data Fields
- `timestamp`: ISO 8601 timestamp
- `rssi`: Signal strength in dBm (-113 to -51)
- `ber`: Bit error rate (0-7)
- `network_type`: LTE/3G/2G
- `network_operator`: Carrier name
- `registration_status`: Network registration state
- `rx_bytes`: Received bytes
- `tx_bytes`: Transmitted bytes

### Starlink Data Fields
- `timestamp`: ISO 8601 timestamp
- `uptime`: Connection uptime in seconds
- `latency`: Ping latency in ms
- `download_speed`: Mbps
- `upload_speed`: Mbps
- `obstruction_percentage`: Sky obstruction %

## 🔒 Security

### Firewall Configuration
```bash
# Allow only monitoring ports
sudo ufw allow 8897/tcp  # LTE Collector
sudo ufw allow 8899/tcp  # Starlink Collector
sudo ufw enable
```

### API Authentication (Optional)
Add to environment variables:
```bash
export API_KEY=your_secure_key_here
```

## 🐛 Troubleshooting

### LTE Module Not Detected
```bash
# Check USB connection
lsusb | grep Quectel

# Check serial port
ls -la /dev/ttyUSB*

# Test AT commands manually
screen /dev/ttyUSB0 115200
AT+CSQ  # Check signal
```

### Starlink Connection Failed
```bash
# Check network connection
ping 192.168.100.1

# Test gRPC endpoint
grpcurl -plaintext 192.168.100.1:9200 list
```

### Service Won't Start
```bash
# Check logs
sudo journalctl -u lte-collector -n 50

# Run manually for debugging
cd /home/pi/starlink_lte
source venv/bin/activate
python lte_remote_collector_en.py
```

## 📝 CSV File Management

Files are automatically rotated every 10 minutes or when reaching 30MB.

### Manual cleanup (keep last 7 days)
```bash
find ./lte-data -name "*.csv" -mtime +7 -delete
find ./starlink-data -name "*.csv" -mtime +7 -delete
```

### Automatic cleanup (crontab)
```bash
crontab -e
# Add line:
0 2 * * * find /home/pi/starlink_lte/*-data -name "*.csv" -mtime +7 -delete
```

## 🚁 Drone/Aircraft Deployment Notes

1. **Power Management**: Use stable 5V/3A power supply
2. **Vibration**: Use dampening mounts for Raspberry Pi
3. **Temperature**: Add heatsink or cooling fan
4. **Storage**: Use high-quality SD card (Class 10+)
5. **Network**: Configure VPN for secure remote access

## 📊 Performance

- **CPU Usage**: ~5-10% on Raspberry Pi 4
- **Memory**: ~50MB per collector
- **Storage**: ~100MB per day per collector
- **Network**: <1KB/s bandwidth usage

## 🔄 Updates

```bash
cd ~/starlink_lte
git pull origin main
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart lte-collector
```

## 📧 Support

Issues: https://github.com/dongyun92/starlink_lte/issues

## 📄 License

MIT License - See LICENSE file for details