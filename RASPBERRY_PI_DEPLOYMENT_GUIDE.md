# 🚀 Raspberry Pi 기체 탑재 가이드
## Starlink + LTE 이중화 네트워크 모니터링 시스템

---

## 📋 시스템 개요

이 시스템은 항공기에 탑재되어 **Starlink**와 **LTE** 두 개의 네트워크를 동시에 모니터링합니다.

### 🎯 주요 기능
- **이중화 네트워크**: Starlink + LTE 동시 모니터링
- **실시간 데이터 수집**: 10분 단위 CSV 파일 로테이션
- **원격 모니터링**: 웹 대시보드를 통한 실시간 상태 확인
- **자동 복구**: 시스템 재시작 시 자동 실행
- **보안 강화**: 방화벽 + Fail2ban 침입 방지

### 🔌 포트 구성
| 서비스 | 포트 | 용도 |
|--------|------|------|
| LTE Collector | 8897 | LTE 데이터 수집 API |
| LTE Dashboard | 8079 | LTE 모니터링 대시보드 |
| Starlink Collector | 8899 | Starlink 데이터 수집 API |
| Starlink Dashboard | 8080 | Starlink 모니터링 대시보드 |

---

## 🛠️ 설치 방법

### 1️⃣ 스크립트 전송
```bash
# 개발 PC에서 Raspberry Pi로 설치 스크립트 전송
scp install_raspberry_pi.sh pi@[라즈베리파이_IP]:/home/pi/

# 필요한 파일들도 함께 전송
scp lte_remote_collector.py pi@[라즈베리파이_IP]:/home/pi/
scp lte_ground_station.py pi@[라즈베리파이_IP]:/home/pi/
```

### 2️⃣ Raspberry Pi 접속
```bash
ssh pi@[라즈베리파이_IP]
```

### 3️⃣ 설치 실행
```bash
# 스크립트 실행 권한 부여
chmod +x install_raspberry_pi.sh

# 설치 시작 (자동 시작 옵션 포함)
sudo ./install_raspberry_pi.sh --auto-start

# 또는 수동 시작 선택
sudo ./install_raspberry_pi.sh
```

### 4️⃣ 설치 완료 확인
설치가 완료되면 다음 정보가 표시됩니다:
- 외부 IP 주소
- 접속 가능한 URL들
- 서비스 상태

---

## 📡 하드웨어 연결

### LTE 모듈 (Quectel EC25/EC21)
```
Raspberry Pi USB → LTE 모듈 USB
- 자동 인식: /dev/ttyUSB0
- 테스트: sudo screen /dev/ttyUSB0 115200
- AT 명령 테스트: AT+CSQ (신호 강도 확인)
```

### Starlink 디시
```
Raspberry Pi Ethernet → Starlink Router
- gRPC 연결: 192.168.100.1:9200
- 자동 감지 및 연결
```

---

## 🌐 접속 방법

### 내부 네트워크 (VPN 연결 시)
```
# LTE 모니터링
http://[라즈베리파이_IP]:8079

# Starlink 모니터링  
http://[라즈베리파이_IP]:8080
```

### 외부 네트워크 (공인 IP)
```
# LTE 모니터링
http://[외부_IP]:8079

# Starlink 모니터링
http://[외부_IP]:8080
```

---

## 🔧 서비스 관리

### 서비스 상태 확인
```bash
# 모든 서비스 상태
sudo systemctl status lte-collector
sudo systemctl status lte-dashboard
sudo systemctl status starlink-collector
sudo systemctl status starlink-dashboard

# 한번에 모두 확인
for service in lte-collector lte-dashboard starlink-collector starlink-dashboard; do
    echo "=== $service ==="
    sudo systemctl status $service --no-pager | head -5
done
```

### 서비스 재시작
```bash
# 개별 서비스 재시작
sudo systemctl restart lte-collector
sudo systemctl restart lte-dashboard

# 모든 서비스 재시작
sudo systemctl restart lte-collector lte-dashboard starlink-collector starlink-dashboard
```

### 로그 확인
```bash
# 실시간 로그 (Ctrl+C로 종료)
sudo journalctl -u lte-collector -f
sudo journalctl -u lte-dashboard -f

# 최근 100줄 로그
sudo journalctl -u lte-collector -n 100
```

---

## 📊 데이터 파일 위치

### CSV 파일 (10분 단위 로테이션)
```
/home/pi/lte-data/
├── lte_data_20260120_1030.csv
├── lte_data_20260120_1040.csv
└── ...

/home/pi/starlink-data/
├── starlink_data_20260120_1030.csv
├── starlink_data_20260120_1040.csv
└── ...
```

### SQLite 데이터베이스
```
/home/pi/lte-ground-data/
└── lte_monitoring.db

/home/pi/starlink-ground-data/
└── starlink_monitoring.db
```

---

## 🛡️ 보안 설정

### 방화벽 상태
```bash
# 방화벽 규칙 확인
sudo ufw status verbose

# 특정 IP만 허용하기
sudo ufw allow from [신뢰_IP] to any port 8079
sudo ufw allow from [신뢰_IP] to any port 8080
```

### Fail2ban 상태
```bash
# 차단된 IP 확인
sudo fail2ban-client status sshd

# IP 차단 해제
sudo fail2ban-client set sshd unbanip [IP_주소]
```

---

## 🔍 문제 해결

### LTE 모듈이 인식되지 않을 때
```bash
# USB 장치 확인
lsusb | grep Quectel

# 시리얼 포트 확인
ls -la /dev/ttyUSB*

# 권한 문제 해결
sudo usermod -a -G dialout pi
sudo chmod 666 /dev/ttyUSB0
```

### Starlink 연결 실패
```bash
# 네트워크 연결 확인
ping 192.168.100.1

# gRPC 포트 확인
nc -zv 192.168.100.1 9200
```

### 서비스가 시작되지 않을 때
```bash
# 상세 오류 확인
sudo journalctl -xe -u lte-collector

# Python 패키지 재설치
pip3 install --break-system-packages flask pyserial requests grpcio
```

---

## 🚁 기체 탑재 시 체크리스트

### 탑재 전
- [ ] Raspberry Pi SD 카드 준비 (32GB 이상 권장)
- [ ] 전원 케이블 및 어댑터 확인
- [ ] LTE 모듈 USB 케이블 준비
- [ ] Starlink 이더넷 케이블 준비
- [ ] 진동 방지 마운트 준비

### 탑재 후
- [ ] 전원 연결 확인 (5V/3A 이상)
- [ ] LTE 모듈 USB 연결 확인
- [ ] Starlink 이더넷 연결 확인
- [ ] 시스템 부팅 대기 (약 1-2분)
- [ ] LED 상태 확인 (녹색 점등)

### 비행 전 테스트
- [ ] 웹 대시보드 접속 확인
- [ ] LTE 신호 강도 확인 (RSSI > -85 dBm)
- [ ] Starlink 연결 상태 확인
- [ ] 데이터 수집 확인 (CSV 파일 생성)
- [ ] 원격 제어 기능 테스트

---

## 📞 모니터링 화면 설명

### LTE 대시보드 (포트 8079)
- **색상**: 분홍색/보라색 테마 (구분 용이)
- **주요 지표**:
  - RSSI: 신호 강도 (-113 ~ -51 dBm)
  - BER: 비트 오류율 (낮을수록 좋음)
  - Network: 현재 연결된 네트워크 (LTE/3G/2G)
  - RX/TX: 데이터 송수신량

### Starlink 대시보드 (포트 8080)
- **색상**: 네이비/흰색 테마
- **주요 지표**:
  - Uptime: 연결 시간
  - Latency: 지연 시간 (ms)
  - Download/Upload: 속도 (Mbps)
  - Obstruction: 장애물 비율 (%)

---

## 🔄 업데이트 방법

### 소프트웨어 업데이트
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 모니터링 스크립트 업데이트
# 1. 새 버전 다운로드
wget [업데이트_URL]/lte_remote_collector.py -O lte_remote_collector_new.py

# 2. 백업
cp lte_remote_collector.py lte_remote_collector_backup.py

# 3. 교체
mv lte_remote_collector_new.py lte_remote_collector.py

# 4. 서비스 재시작
sudo systemctl restart lte-collector
```

---

## 📝 참고 사항

### 성능 최적화
- **SD 카드**: Class 10 이상 사용 권장
- **전원**: 안정적인 5V/3A 전원 공급 필수
- **냉각**: 방열판 또는 쿨링팬 설치 권장
- **진동**: 항공기 탑재 시 진동 방지 마운트 필수

### 데이터 백업
```bash
# 매일 자동 백업 설정
crontab -e
# 추가: 0 2 * * * tar -czf /backup/monitoring_$(date +\%Y\%m\%d).tar.gz /home/pi/*-data/
```

### 원격 지원
- SSH 접속 가능 (포트 22)
- VNC 설정 가능 (추가 설정 필요)
- TeamViewer 설치 가능

---

## ⚠️ 주의 사항

1. **비행 중 재시작 금지**: 비행 중에는 시스템 재시작을 하지 마세요
2. **전원 안정성**: 전원 변동이 심한 환경에서는 UPS 사용 권장
3. **데이터 저장 공간**: SD 카드 용량 80% 초과 시 자동 삭제 설정
4. **네트워크 보안**: 공개 네트워크에서는 VPN 사용 필수
5. **온도 관리**: 작동 온도 0°C ~ 70°C 유지

---

## 📧 문제 발생 시 연락처

기술 지원이 필요한 경우:
1. 시스템 로그 수집: `sudo journalctl -b > system_log.txt`
2. 네트워크 상태 확인: `ip addr > network_info.txt`
3. 수집된 정보와 함께 문의

---

**마지막 업데이트**: 2026년 1월 20일
**버전**: 1.0.0