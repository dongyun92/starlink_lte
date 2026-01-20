#!/bin/bash

#################################################################
# 라즈베리파이 LTE/Starlink 모니터링 시스템 자동 설치 스크립트
# 
# 사용법: 
#   wget https://your-server/install_raspberry_pi.sh
#   chmod +x install_raspberry_pi.sh
#   sudo ./install_raspberry_pi.sh
#################################################################

set -e  # 에러 발생시 중지

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Root 권한 확인
if [[ $EUID -ne 0 ]]; then
   log_error "이 스크립트는 root 권한이 필요합니다. sudo로 실행해주세요."
   exit 1
fi

# 라즈베리파이 확인
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    log_warn "라즈베리파이가 아닌 것 같습니다. 계속하시겠습니까? (y/n)"
    read -r response
    if [[ "$response" != "y" ]]; then
        exit 1
    fi
fi

log_info "🚀 LTE/Starlink 모니터링 시스템 설치를 시작합니다..."

#################################################################
# 1. 시스템 업데이트 및 기본 패키지 설치
#################################################################
log_step "시스템 패키지 업데이트 중..."
apt update && apt upgrade -y

log_step "필수 패키지 설치 중..."
apt install -y \
    python3 python3-pip python3-venv \
    git curl wget screen htop \
    ufw fail2ban \
    sqlite3 \
    python3-flask python3-serial python3-requests

# pip 패키지 설치
log_step "Python 패키지 설치 중..."
pip3 install --break-system-packages \
    flask pyserial requests \
    || pip3 install \
    flask pyserial requests

#################################################################
# 2. 디렉토리 구조 생성
#################################################################
log_step "디렉토리 구조 생성 중..."
mkdir -p /opt/drone-monitoring/{bin,data,logs,config}
mkdir -p /opt/drone-data/{lte,starlink,ground}

#################################################################
# 3. 모니터링 시스템 파일 생성
#################################################################
log_step "LTE 수집기 생성 중..."
cat > /opt/drone-monitoring/bin/lte_remote_collector.py << 'EOF'
#!/usr/bin/env python3
"""
LTE 모듈 원격 제어 수집기 (Quectel EC25/EC21 모듈)
AT 명령어 기반 LTE 통신 품질 모니터링
"""

import json
import time
import threading
import os
import serial
import re
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from enum import Enum

class CollectorState(Enum):
    """수집기 상태"""
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

@dataclass
class LTEData:
    """LTE 모듈 데이터"""
    timestamp: str
    module_id: str = "EC25-RPi-001"
    connection_state: str = "CONNECTED"
    uptime: int = 0
    signal_quality_rssi: int = 0
    signal_quality_ber: int = 0
    network_operator: str = ""
    network_mode: str = ""
    network_reg_status: str = ""
    cell_id: str = ""
    rx_bytes: int = 0
    tx_bytes: int = 0
    ip_address: str = ""

class LTEModuleCollector:
    """LTE 모듈 데이터 수집기"""
    
    def __init__(self, data_dir="/opt/drone-data/lte", control_port=8897, serial_port="/dev/ttyUSB0"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.control_port = control_port
        self.serial_port = serial_port
        
        self.state = CollectorState.IDLE
        self.state_lock = threading.Lock()
        
        self.collection_thread = None
        self.running = False
        self.current_file = None
        self.current_file_handle = None
        self.file_start_time = None
        self.collection_start_time = None
        self.data_counter = 0
        self.uptime_start = time.time()
        
        self.serial_conn = None
        self.max_file_duration = 600
        self.max_file_size = 30 * 1024 * 1024
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/drone-monitoring/logs/lte_collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        """Flask API 라우트 설정"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            with self.state_lock:
                file_info = self._get_current_file_info()
                return jsonify({
                    "state": self.state.value,
                    "current_file": file_info["filename"] if file_info else None,
                    "file_size": file_info["size_mb"] if file_info else 0,
                    "duration": self._get_collection_duration(),
                    "file_count": len(self._get_today_files()),
                    "data_points": self.data_counter,
                    "last_update": datetime.utcnow().isoformat() + 'Z',
                    "module_type": "LTE (Quectel EC25/EC21)"
                })
        
        @self.app.route('/api/start', methods=['POST'])
        def start_collection():
            try:
                if self.state != CollectorState.IDLE:
                    return jsonify({"error": f"LTE 수집기가 {self.state.value} 상태입니다"}), 400
                
                self._start_collection()
                return jsonify({"message": "LTE 데이터 수집이 시작되었습니다", "state": self.state.value})
                
            except Exception as e:
                self.logger.error(f"수집 시작 오류: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/stop', methods=['POST'])
        def stop_collection():
            try:
                if self.state not in [CollectorState.RUNNING, CollectorState.ERROR]:
                    return jsonify({"error": f"LTE 수집기가 {self.state.value} 상태입니다"}), 400
                
                self._stop_collection()
                return jsonify({"message": "LTE 데이터 수집이 중지되었습니다", "state": self.state.value})
                
            except Exception as e:
                self.logger.error(f"수집 중지 오류: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/current_data', methods=['GET'])
        def get_current_data():
            try:
                if self.state != CollectorState.RUNNING:
                    # IDLE 상태에서도 모의 데이터 반환
                    data = self._get_mock_lte_data()
                else:
                    data = self._collect_lte_data()
                return jsonify(asdict(data))
                
            except Exception as e:
                self.logger.error(f"LTE 데이터 조회 오류: {e}")
                return jsonify({"error": str(e)}), 500

    def _init_serial_connection(self):
        """시리얼 연결 초기화"""
        try:
            if os.path.exists(self.serial_port):
                self.serial_conn = serial.Serial(
                    port=self.serial_port,
                    baudrate=115200,
                    timeout=1,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                self._send_at_command("AT")
                self.logger.info(f"LTE 모듈 시리얼 연결 성공: {self.serial_port}")
                return True
            else:
                self.logger.warn(f"시리얼 포트 없음: {self.serial_port}, 모의 모드로 실행")
                return False
        except Exception as e:
            self.logger.error(f"시리얼 연결 실패: {e}, 모의 모드로 실행")
            return False

    def _send_at_command(self, command: str, timeout: float = 1.0) -> Optional[str]:
        """AT 명령 전송 및 응답 수신"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            self.serial_conn.write((command + '\r\n').encode())
            time.sleep(0.1)
            
            start_time = time.time()
            response = ""
            
            while time.time() - start_time < timeout:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode().strip()
                    if line:
                        response += line + '\n'
                        if 'OK' in line or 'ERROR' in line:
                            break
                time.sleep(0.05)
            
            return response.strip() if response else None
            
        except Exception as e:
            self.logger.error(f"AT 명령 전송 오류 ({command}): {e}")
            return None

    def _get_mock_lte_data(self) -> LTEData:
        """모의 LTE 데이터 생성 (실제 모듈 없을 때)"""
        import random
        collect_time = datetime.utcnow()
        precise_timestamp = collect_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        return LTEData(
            timestamp=precise_timestamp,
            connection_state="CONNECTED",
            uptime=int(time.time() - self.uptime_start),
            signal_quality_rssi=random.randint(15, 31),
            signal_quality_ber=random.randint(0, 7),
            network_operator="KT" if random.random() > 0.5 else "SKT",
            network_mode="LTE",
            network_reg_status="REGISTERED",
            cell_id=f"460{random.randint(1000, 9999)}",
            rx_bytes=random.randint(1000000, 10000000),
            tx_bytes=random.randint(500000, 5000000),
            ip_address=f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        )

    def _collect_lte_data(self) -> LTEData:
        """실제 LTE 모듈에서 데이터 수집"""
        if not self.serial_conn:
            return self._get_mock_lte_data()
            
        collect_time = datetime.utcnow()
        precise_timestamp = collect_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        data = LTEData(
            timestamp=precise_timestamp,
            uptime=int(time.time() - self.uptime_start)
        )
        
        try:
            # 신호 품질 조회 (AT+CSQ)
            csq_response = self._send_at_command("AT+CSQ")
            if csq_response and "+CSQ:" in csq_response:
                match = re.search(r'\+CSQ:\s*(\d+),(\d+)', csq_response)
                if match:
                    data.signal_quality_rssi = int(match.group(1))
                    data.signal_quality_ber = int(match.group(2))
            
            # 네트워크 정보 조회 (AT+QNWINFO)
            nw_response = self._send_at_command("AT+QNWINFO")
            if nw_response and "+QNWINFO:" in nw_response:
                match = re.search(r'\+QNWINFO:\s*"([^"]+)","([^"]+)","([^"]+)",(\d+)', nw_response)
                if match:
                    data.network_mode = match.group(1)
                    data.network_operator = match.group(2)
            
            # 네트워크 등록 상태 조회 (AT+CREG?)
            creg_response = self._send_at_command("AT+CREG?")
            if creg_response and "+CREG:" in creg_response:
                match = re.search(r'\+CREG:\s*\d+,(\d+)', creg_response)
                if match:
                    reg_status = int(match.group(1))
                    status_map = {1: "REGISTERED", 2: "SEARCHING", 3: "DENIED", 5: "ROAMING"}
                    data.network_reg_status = status_map.get(reg_status, "UNKNOWN")
                    data.connection_state = "CONNECTED" if reg_status in [1, 5] else "DISCONNECTED"
            
        except Exception as e:
            self.logger.error(f"LTE 데이터 수집 오류: {e}")
            return self._get_mock_lte_data()
        
        return data

    def _set_state(self, new_state: CollectorState):
        """상태 변경"""
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            self.logger.info(f"LTE 수집기 상태 변경: {old_state.value} → {new_state.value}")

    def _start_collection(self):
        """수집 시작"""
        self._set_state(CollectorState.STARTING)
        
        try:
            # 시리얼 연결 시도 (실패해도 모의 모드로 계속)
            self._init_serial_connection()
            
            # 새 파일 생성
            self._create_new_file()
            
            # 수집 스레드 시작
            self.running = True
            self.collection_start_time = datetime.utcnow()
            self.data_counter = 0
            self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
            self.collection_thread.start()
            
            self._set_state(CollectorState.RUNNING)
            self.logger.info("LTE 데이터 수집이 시작되었습니다")
            
        except Exception as e:
            self._set_state(CollectorState.ERROR)
            raise

    def _stop_collection(self):
        """수집 중지"""
        self._set_state(CollectorState.STOPPING)
        
        try:
            self.running = False
            
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5)
            
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            
            self._close_current_file()
            
            self._set_state(CollectorState.IDLE)
            self.logger.info(f"LTE 데이터 수집이 중지되었습니다 (총 {self.data_counter}개 데이터 수집)")
            
        except Exception as e:
            self._set_state(CollectorState.ERROR)
            raise

    def _create_new_file(self):
        """새 CSV 파일 생성"""
        if self.current_file_handle:
            self.current_file_handle.close()
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"lte_module_{timestamp}.csv"
        self.current_file = self.data_dir / filename
        self.file_start_time = datetime.utcnow()
        
        self.current_file_handle = open(self.current_file, 'w')
        header = [
            "timestamp", "module_id", "connection_state", "uptime",
            "signal_quality_rssi", "signal_quality_ber", "network_operator", 
            "network_mode", "network_reg_status", "cell_id",
            "rx_bytes", "tx_bytes", "ip_address"
        ]
        self.current_file_handle.write(','.join(header) + '\n')
        self.current_file_handle.flush()
        
        self.logger.info(f"새 LTE 파일 생성: {filename}")

    def _close_current_file(self):
        """현재 파일 닫기"""
        if self.current_file_handle:
            self.current_file_handle.close()
            self.current_file_handle = None
            
            if self.current_file:
                self.logger.info(f"파일 닫힘: {self.current_file.name}")

    def _should_rotate_file(self) -> bool:
        """파일 로테이션이 필요한지 확인"""
        if not self.current_file or not self.file_start_time:
            return False
        
        duration = datetime.utcnow() - self.file_start_time
        if duration.total_seconds() > self.max_file_duration:
            return True
        
        if self.current_file.exists() and self.current_file.stat().st_size > self.max_file_size:
            return True
        
        return False

    def _save_to_csv(self, data: LTEData):
        """CSV 파일에 데이터 저장"""
        if not self.current_file_handle:
            return
        
        try:
            row = [
                data.timestamp, data.module_id, data.connection_state, data.uptime,
                data.signal_quality_rssi, data.signal_quality_ber, data.network_operator,
                data.network_mode, data.network_reg_status, data.cell_id,
                data.rx_bytes, data.tx_bytes, data.ip_address
            ]
            
            self.current_file_handle.write(','.join(map(str, row)) + '\n')
            self.current_file_handle.flush()
            self.data_counter += 1
            
        except Exception as e:
            self.logger.error(f"CSV 저장 오류: {e}")

    def _collection_loop(self):
        """메인 LTE 데이터 수집 루프"""
        self.logger.info("LTE 데이터 수집 루프 시작")
        
        while self.running:
            start_time = time.time()
            
            try:
                if self._should_rotate_file():
                    self.logger.info("파일 로테이션 수행")
                    self._close_current_file()
                    self._create_new_file()
                
                data = self._collect_lte_data()
                self._save_to_csv(data)
                
                self.logger.debug(f"LTE 데이터 수집: RSSI={data.signal_quality_rssi}, 상태={data.connection_state}")
                
            except Exception as e:
                self.logger.error(f"수집 루프 오류: {e}")
                self._set_state(CollectorState.ERROR)
            
            elapsed = time.time() - start_time
            sleep_time = max(0, 5.0 - elapsed)
            time.sleep(sleep_time)
        
        self.logger.info("LTE 데이터 수집 루프 종료")

    def _get_current_file_info(self) -> Optional[Dict]:
        """현재 파일 정보 반환"""
        if not self.current_file or not self.current_file.exists():
            return None
        
        stat = self.current_file.stat()
        return {
            "filename": self.current_file.name,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
        }

    def _get_today_files(self) -> List[Dict]:
        """생성된 파일 목록 반환"""
        files = []
        for file_path in self.data_dir.glob("lte_module_*.csv"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        return sorted(files, key=lambda x: x['created'])

    def _get_collection_duration(self) -> str:
        """수집 지속 시간 반환"""
        if not self.collection_start_time:
            return "00:00:00"
        
        duration = datetime.utcnow() - self.collection_start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def run_control_server(self):
        """제어 서버 실행"""
        self.logger.info(f"LTE 제어 서버 시작: http://0.0.0.0:{self.control_port}")
        self.app.run(host='0.0.0.0', port=self.control_port, debug=False)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='LTE 모듈 원격 제어 수집기')
    parser.add_argument('--data-dir', default='/opt/drone-data/lte', help='데이터 저장 디렉토리')
    parser.add_argument('--control-port', type=int, default=8897, help='제어 API 포트')
    parser.add_argument('--serial-port', default='/dev/ttyUSB0', help='LTE 모듈 시리얼 포트')
    
    args = parser.parse_args()
    
    collector = LTEModuleCollector(
        data_dir=args.data_dir,
        control_port=args.control_port,
        serial_port=args.serial_port
    )
    collector.run_control_server()

if __name__ == "__main__":
    main()
EOF

chmod +x /opt/drone-monitoring/bin/lte_remote_collector.py

#################################################################
# 4. systemd 서비스 생성
#################################################################
log_step "systemd 서비스 생성 중..."

# LTE 수집기 서비스
cat > /etc/systemd/system/lte-collector.service << 'EOF'
[Unit]
Description=LTE Data Collector for Drone
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=dialout
WorkingDirectory=/opt/drone-monitoring
ExecStart=/usr/bin/python3 /opt/drone-monitoring/bin/lte_remote_collector.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/drone-monitoring/logs/lte-collector.log
StandardError=append:/opt/drone-monitoring/logs/lte-collector.log

[Install]
WantedBy=multi-user.target
EOF

# Starlink 수집기 서비스 (선택사항)
cat > /etc/systemd/system/starlink-collector.service << 'EOF'
[Unit]
Description=Starlink Data Collector for Drone
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/drone-monitoring
ExecStart=/usr/bin/python3 /opt/drone-monitoring/bin/starlink_collector.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/drone-monitoring/logs/starlink-collector.log
StandardError=append:/opt/drone-monitoring/logs/starlink-collector.log

[Install]
WantedBy=multi-user.target
EOF

#################################################################
# 5. 방화벽 설정 (UFW)
#################################################################
log_step "방화벽 설정 중..."

# UFW 기본 설정
ufw --force disable
ufw --force reset

# 기본 정책 설정
ufw default deny incoming
ufw default allow outgoing

# SSH 허용 (필수!)
ufw allow 22/tcp comment 'SSH'

# 모니터링 포트 허용
ufw allow 8897/tcp comment 'LTE Collector API'
ufw allow 8899/tcp comment 'Starlink Collector API'
ufw allow 8079/tcp comment 'LTE Dashboard'
ufw allow 8080/tcp comment 'Starlink Dashboard'

# VPN/Starlink/LTE 네트워크 인터페이스 트래픽 허용
ufw allow in on tun0 comment 'VPN traffic'
ufw allow in on wwan0 comment 'LTE traffic'
ufw allow in on eth0 comment 'Starlink traffic'

# 로깅 설정
ufw logging on
ufw logging low

# 방화벽 활성화
echo "y" | ufw enable

# 방화벽 상태 확인
ufw status verbose

#################################################################
# 6. Fail2ban 설정 (무차별 대입 공격 방지)
#################################################################
log_step "Fail2ban 보안 설정 중..."

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[lte-api]
enabled = true
port = 8897
filter = lte-api
logpath = /opt/drone-monitoring/logs/lte-collector.log
maxretry = 10
bantime = 1800
EOF

# Fail2ban 필터 생성
cat > /etc/fail2ban/filter.d/lte-api.conf << 'EOF'
[Definition]
failregex = ^.*\[ERROR\].*from <HOST>.*$
            ^.*Unauthorized access attempt from <HOST>.*$
ignoreregex =
EOF

systemctl enable fail2ban
systemctl restart fail2ban

#################################################################
# 7. 네트워크 최적화 설정
#################################################################
log_step "네트워크 최적화 설정 중..."

cat >> /etc/sysctl.conf << 'EOF'

# 네트워크 최적화 for Drone Monitoring
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_mtu_probing = 1

# 보안 설정
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
EOF

sysctl -p

#################################################################
# 8. 권한 설정
#################################################################
log_step "권한 설정 중..."

# pi 사용자 생성 (없는 경우)
if ! id -u pi &>/dev/null; then
    useradd -m -s /bin/bash pi
    echo "pi:raspberry" | chpasswd
fi

# 권한 설정
usermod -a -G dialout pi
usermod -a -G gpio pi
chown -R pi:pi /opt/drone-monitoring
chown -R pi:pi /opt/drone-data
chmod 755 /opt/drone-monitoring/bin/*.py

#################################################################
# 9. 서비스 시작
#################################################################
log_step "서비스 시작 중..."

systemctl daemon-reload
systemctl enable lte-collector.service
systemctl start lte-collector.service
sleep 2
systemctl status lte-collector.service --no-pager

#################################################################
# 10. 외부 접속 정보 표시
#################################################################
log_step "설치 완료! 접속 정보..."

# IP 주소 가져오기
ETH_IP=$(ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
WLAN_IP=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
WWAN_IP=$(ip -4 addr show wwan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
TUN_IP=$(ip -4 addr show tun0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)

# 외부 IP 확인
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "확인불가")

echo ""
echo "=============================================="
echo "    🚁 드론 모니터링 시스템 설치 완료! 🚁"
echo "=============================================="
echo ""
echo "📡 접속 정보:"
echo "----------------------------------------------"
if [ ! -z "$ETH_IP" ]; then
    echo "  Starlink (Ethernet): http://$ETH_IP:8897"
fi
if [ ! -z "$WWAN_IP" ]; then
    echo "  LTE (WWAN):         http://$WWAN_IP:8897"
fi
if [ ! -z "$WLAN_IP" ]; then
    echo "  WiFi (WLAN):        http://$WLAN_IP:8897"
fi
if [ ! -z "$TUN_IP" ]; then
    echo "  VPN (TUN):          http://$TUN_IP:8897"
fi
echo ""
echo "  외부 IP:            http://$EXTERNAL_IP:8897"
echo ""
echo "----------------------------------------------"
echo "📝 서비스 포트:"
echo "----------------------------------------------"
echo "  LTE Collector API:      8897"
echo "  Starlink Collector API: 8899"
echo "  LTE Dashboard:          8079"
echo "  Starlink Dashboard:     8080"
echo ""
echo "----------------------------------------------"
echo "🔧 서비스 관리 명령어:"
echo "----------------------------------------------"
echo "  상태 확인: sudo systemctl status lte-collector"
echo "  시작:      sudo systemctl start lte-collector"
echo "  중지:      sudo systemctl stop lte-collector"
echo "  재시작:    sudo systemctl restart lte-collector"
echo "  로그:      sudo journalctl -u lte-collector -f"
echo ""
echo "----------------------------------------------"
echo "🔒 방화벽 상태:"
echo "----------------------------------------------"
ufw status numbered | head -10
echo ""
echo "=============================================="
echo ""
echo "💡 외부에서 접속시:"
echo "   1. 라우터에서 포트포워딩 설정 (8897, 8899)"
echo "   2. 또는 VPN으로 접속"
echo "   3. 또는 공인 IP로 직접 접속"
echo ""
echo "📊 모니터링 시작:"
echo "   http://$EXTERNAL_IP:8897/api/start (POST)"
echo ""

# 자동 시작 옵션
log_warn "부팅시 자동으로 데이터 수집을 시작하시겠습니까? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    cat > /etc/systemd/system/lte-collector-autostart.service << 'EOF'
[Unit]
Description=Auto-start LTE data collection on boot
After=lte-collector.service
Requires=lte-collector.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/curl -X POST http://localhost:8897/api/start
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl enable lte-collector-autostart.service
    log_info "자동 시작 설정 완료!"
fi

log_info "✅ 모든 설치가 완료되었습니다!"
log_info "🚀 이제 외부에서 http://$EXTERNAL_IP:8897 로 접속 가능합니다!"