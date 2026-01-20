# 🚀 Raspberry Pi 완전 설치 가이드
## Starlink + LTE 이중화 네트워크 모니터링 시스템

---

## 📋 사전 준비

### 필요한 것들
- Raspberry Pi 4 (4GB RAM 이상 권장)
- SD 카드 (32GB 이상)
- 인터넷 연결
- SSH 접속 가능한 PC

### Raspberry Pi OS 설치
1. Raspberry Pi Imager 다운로드
2. Raspberry Pi OS (64-bit) 선택
3. SSH 활성화, WiFi 설정
4. SD 카드에 쓰기

---

## 🔧 Step 1: Raspberry Pi 초기 설정

### SSH 접속
```bash
# Windows PowerShell 또는 Mac/Linux Terminal에서
ssh pi@raspberrypi.local
# 또는 IP 주소로
ssh pi@192.168.1.XXX

# 기본 비밀번호: raspberry
```

### 시스템 업데이트
```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y git python3-pip python3-venv screen htop vim
```

---

## 📦 Step 2: 프로젝트 다운로드

```bash
# 홈 디렉토리로 이동
cd ~

# GitHub에서 프로젝트 클론
git clone https://github.com/dongyun92/starlink_lte.git

# 프로젝트 디렉토리로 이동
cd starlink_lte
```

---

## 🐍 Step 3: Python 가상환경 설정

```bash
# Python 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 필수 패키지 설치
pip install flask pyserial requests grpcio grpcio-tools
```

---

## 📁 Step 4: 디렉토리 구조 생성

```bash
# 데이터 저장 디렉토리 생성
mkdir -p ~/starlink_lte/lte-data
mkdir -p ~/starlink_lte/lte-ground-data
mkdir -p ~/starlink_lte/starlink-data
mkdir -p ~/starlink_lte/starlink-ground-data
mkdir -p ~/starlink_lte/logs

# 권한 설정
chmod 755 ~/starlink_lte/*-data
chmod 755 ~/starlink_lte/logs
```

---

## ⚙️ Step 5: Systemd 서비스 등록

### LTE Collector 서비스
```bash
sudo tee /etc/systemd/system/lte-collector.service > /dev/null << 'EOF'
[Unit]
Description=LTE Data Collector Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/starlink_lte
Environment="PATH=/home/pi/starlink_lte/venv/bin"
ExecStart=/home/pi/starlink_lte/venv/bin/python /home/pi/starlink_lte/lte_remote_collector.py --data-dir /home/pi/starlink_lte/lte-data --control-port 8897 --serial-port /dev/ttyUSB0
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/starlink_lte/logs/lte-collector.log
StandardError=append:/home/pi/starlink_lte/logs/lte-collector.log

[Install]
WantedBy=multi-user.target
EOF
```

### LTE Dashboard 서비스
```bash
sudo tee /etc/systemd/system/lte-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=LTE Dashboard Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/starlink_lte
Environment="PATH=/home/pi/starlink_lte/venv/bin"
ExecStart=/home/pi/starlink_lte/venv/bin/python /home/pi/starlink_lte/lte_ground_station.py --port 8079 --data-dir /home/pi/starlink_lte/lte-ground-data
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/starlink_lte/logs/lte-dashboard.log
StandardError=append:/home/pi/starlink_lte/logs/lte-dashboard.log

[Install]
WantedBy=multi-user.target
EOF
```

### Starlink Collector 서비스
```bash
sudo tee /etc/systemd/system/starlink-collector.service > /dev/null << 'EOF'
[Unit]
Description=Starlink Data Collector Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/starlink_lte
Environment="PATH=/home/pi/starlink_lte/venv/bin"
ExecStart=/home/pi/starlink_lte/venv/bin/python /home/pi/starlink_lte/starlink-grpc-tools/test_remote_collector.py --data-dir /home/pi/starlink_lte/starlink-data
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/starlink_lte/logs/starlink-collector.log
StandardError=append:/home/pi/starlink_lte/logs/starlink-collector.log

[Install]
WantedBy=multi-user.target
EOF
```

### Starlink Dashboard 서비스
```bash
sudo tee /etc/systemd/system/starlink-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=Starlink Dashboard Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/starlink_lte
Environment="PATH=/home/pi/starlink_lte/venv/bin"
ExecStart=/home/pi/starlink_lte/venv/bin/python /home/pi/starlink_lte/starlink-grpc-tools/ground_station_receiver.py --port 8080 --data-dir /home/pi/starlink_lte/starlink-ground-data
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/starlink_lte/logs/starlink-dashboard.log
StandardError=append:/home/pi/starlink_lte/logs/starlink-dashboard.log

[Install]
WantedBy=multi-user.target
EOF
```

---

## 🚀 Step 6: 서비스 시작

```bash
# Systemd 데몬 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable lte-collector
sudo systemctl enable lte-dashboard
sudo systemctl enable starlink-collector
sudo systemctl enable starlink-dashboard

# 서비스 시작
sudo systemctl start lte-collector
sudo systemctl start lte-dashboard
sudo systemctl start starlink-collector
sudo systemctl start starlink-dashboard

# 서비스 상태 확인
sudo systemctl status lte-collector
sudo systemctl status lte-dashboard
sudo systemctl status starlink-collector
sudo systemctl status starlink-dashboard
```

---

## 🛡️ Step 7: 방화벽 설정

```bash
# UFW 설치 및 활성화
sudo apt install -y ufw

# SSH 허용 (중요!)
sudo ufw allow 22/tcp

# 모니터링 포트 허용
sudo ufw allow 8897/tcp  # LTE Collector
sudo ufw allow 8079/tcp  # LTE Dashboard
sudo ufw allow 8899/tcp  # Starlink Collector
sudo ufw allow 8080/tcp  # Starlink Dashboard

# 방화벽 활성화
sudo ufw --force enable

# 상태 확인
sudo ufw status verbose
```

---

## 🌐 Step 8: 접속 테스트

### 로컬 테스트 (Raspberry Pi에서)
```bash
# 서비스 동작 확인
curl http://localhost:8897/status
curl http://localhost:8079
curl http://localhost:8899/status  
curl http://localhost:8080
```

### 원격 테스트 (PC에서)
```bash
# Raspberry Pi IP 확인
hostname -I

# 웹 브라우저에서 접속
# LTE Dashboard: http://[RPI_IP]:8079
# Starlink Dashboard: http://[RPI_IP]:8080
```

---

## 📊 Step 9: 로그 확인 및 모니터링

### 실시간 로그 모니터링
```bash
# 모든 서비스 로그 동시에 보기
sudo journalctl -f -u lte-collector -u lte-dashboard -u starlink-collector -u starlink-dashboard

# 개별 서비스 로그
sudo journalctl -f -u lte-collector
tail -f ~/starlink_lte/logs/lte-collector.log
```

### 시스템 리소스 모니터링
```bash
# CPU, 메모리 사용량
htop

# 디스크 사용량
df -h

# 네트워크 연결 상태
netstat -tuln | grep -E '8897|8079|8899|8080'
```

---

## 🔧 문제 해결

### LTE 모듈 인식 안됨
```bash
# USB 장치 확인
lsusb | grep Quectel

# 시리얼 포트 확인
ls -la /dev/ttyUSB*

# 권한 설정
sudo usermod -a -G dialout pi
sudo chmod 666 /dev/ttyUSB0

# 서비스 재시작
sudo systemctl restart lte-collector
```

### 서비스 시작 실패
```bash
# 상세 오류 확인
sudo journalctl -xe -u lte-collector

# 가상환경 경로 확인
which python
ls -la ~/starlink_lte/venv/bin/python

# 수동 실행 테스트
cd ~/starlink_lte
source venv/bin/activate
python lte_remote_collector.py --help
```

### 포트 충돌
```bash
# 포트 사용 확인
sudo lsof -i :8897
sudo lsof -i :8079

# 프로세스 종료
sudo kill -9 [PID]

# 서비스 재시작
sudo systemctl restart lte-collector
```

---

## 🔄 업데이트 방법

```bash
# 프로젝트 디렉토리로 이동
cd ~/starlink_lte

# 최신 코드 가져오기
git pull origin main

# 가상환경 활성화
source venv/bin/activate

# 패키지 업데이트
pip install --upgrade -r requirements.txt

# 서비스 재시작
sudo systemctl restart lte-collector lte-dashboard starlink-collector starlink-dashboard
```

---

## 🎯 빠른 설치 스크립트

모든 단계를 한 번에 실행하려면:

```bash
#!/bin/bash
# quick_install.sh

# 색상 정의
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Starlink + LTE 모니터링 시스템 설치 시작 ===${NC}"

# 1. 시스템 업데이트
echo -e "${GREEN}[1/9] 시스템 업데이트${NC}"
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-pip python3-venv screen htop vim ufw

# 2. 프로젝트 클론
echo -e "${GREEN}[2/9] 프로젝트 다운로드${NC}"
cd ~
git clone https://github.com/dongyun92/starlink_lte.git
cd starlink_lte

# 3. 가상환경 설정
echo -e "${GREEN}[3/9] Python 가상환경 설정${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask pyserial requests grpcio grpcio-tools

# 4. 디렉토리 생성
echo -e "${GREEN}[4/9] 디렉토리 구조 생성${NC}"
mkdir -p ~/starlink_lte/{lte-data,lte-ground-data,starlink-data,starlink-ground-data,logs}
chmod 755 ~/starlink_lte/*-data ~/starlink_lte/logs

# 5. Starlink 파일 확인 및 생성
echo -e "${GREEN}[5/9] Starlink 파일 준비${NC}"
if [ ! -d "starlink-grpc-tools" ]; then
    mkdir -p starlink-grpc-tools
    # 필요한 Starlink 파일들을 여기서 생성하거나 복사
fi

# 6. 서비스 등록
echo -e "${GREEN}[6/9] Systemd 서비스 등록${NC}"
# (위의 서비스 파일 생성 코드 실행)

# 7. 서비스 시작
echo -e "${GREEN}[7/9] 서비스 시작${NC}"
sudo systemctl daemon-reload
sudo systemctl enable lte-collector lte-dashboard starlink-collector starlink-dashboard
sudo systemctl start lte-collector lte-dashboard starlink-collector starlink-dashboard

# 8. 방화벽 설정
echo -e "${GREEN}[8/9] 방화벽 설정${NC}"
sudo ufw allow 22/tcp
sudo ufw allow 8897/tcp
sudo ufw allow 8079/tcp
sudo ufw allow 8899/tcp
sudo ufw allow 8080/tcp
sudo ufw --force enable

# 9. 완료
echo -e "${GREEN}[9/9] 설치 완료!${NC}"
echo ""
echo "접속 URL:"
echo "LTE Dashboard: http://$(hostname -I | awk '{print $1}'):8079"
echo "Starlink Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "서비스 상태 확인: sudo systemctl status lte-collector"
```

---

## 📝 참고 사항

### 자동 시작 확인
```bash
# 재부팅 후 자동 시작 테스트
sudo reboot

# 재접속 후 확인
sudo systemctl status lte-collector
sudo systemctl status lte-dashboard
```

### 백업 설정
```bash
# 데이터 백업 스크립트
crontab -e
# 추가: 0 2 * * * tar -czf /backup/monitoring_$(date +\%Y\%m\%d).tar.gz /home/pi/starlink_lte/*-data/
```

### 원격 접속 설정
```bash
# SSH 키 인증 설정 (보안 강화)
ssh-keygen -t rsa -b 4096
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

---

## ✅ 설치 완료 체크리스트

- [ ] Raspberry Pi OS 설치 및 SSH 접속
- [ ] 시스템 업데이트 완료
- [ ] GitHub에서 프로젝트 클론
- [ ] Python 가상환경 설정
- [ ] 필수 패키지 설치
- [ ] 데이터 디렉토리 생성
- [ ] Systemd 서비스 등록
- [ ] 서비스 시작 및 자동 시작 설정
- [ ] 방화벽 규칙 설정
- [ ] 웹 대시보드 접속 테스트
- [ ] 로그 확인
- [ ] 재부팅 후 자동 시작 확인

---

**문제 발생 시**: 로그 파일 확인 → 서비스 재시작 → 수동 실행 테스트

**지원**: https://github.com/dongyun92/starlink_lte/issues