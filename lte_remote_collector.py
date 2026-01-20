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
    module_id: str = "EC25-00000000-lte001"
    connection_state: str = "CONNECTED"
    uptime: int = 3600
    signal_quality_rssi: int = 0  # CSQ 값
    signal_quality_ber: int = 0   # BER 값
    network_operator: str = ""
    network_mode: str = ""
    network_reg_status: str = ""
    eps_reg_status: str = ""
    cell_id: str = ""
    lac: str = ""
    rx_bytes: int = 0
    tx_bytes: int = 0
    ip_address: str = ""
    frequency_band: str = ""
    earfcn: int = 0
    latitude: float = 37.5665
    longitude: float = 126.9780
    altitude: float = 120.0

class LTEModuleCollector:
    """LTE 모듈 데이터 수집기"""
    
    def __init__(self, data_dir="./lte-data", control_port=8897, serial_port="/dev/ttyUSB0"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.control_port = control_port
        self.serial_port = serial_port
        
        # 상태 관리
        self.state = CollectorState.IDLE
        self.state_lock = threading.Lock()
        
        # 수집 관련
        self.collection_thread = None
        self.running = False
        self.current_file = None
        self.current_file_handle = None
        self.file_start_time = None
        self.collection_start_time = None
        self.data_counter = 0
        
        # 시리얼 포트 관리
        self.serial_conn = None
        
        # 파일 관리 설정
        self.max_file_duration = 600  # 10분 (600초)
        self.max_file_size = 30 * 1024 * 1024  # 30MB
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Flask 앱 설정
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        """Flask API 라우트 설정"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """현재 상태 반환"""
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
            """수집 시작"""
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
            """수집 중지"""
            try:
                if self.state not in [CollectorState.RUNNING, CollectorState.ERROR]:
                    return jsonify({"error": f"LTE 수집기가 {self.state.value} 상태입니다"}), 400
                
                self._stop_collection()
                return jsonify({"message": "LTE 데이터 수집이 중지되었습니다", "state": self.state.value})
                
            except Exception as e:
                self.logger.error(f"수집 중지 오류: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/files', methods=['GET'])
        def get_files():
            """저장된 파일 목록 반환"""
            files = self._get_today_files()
            return jsonify(files)
        
        @self.app.route('/api/current_data', methods=['GET'])
        def get_current_data():
            """현재 실시간 LTE 데이터 반환"""
            try:
                if self.state != CollectorState.RUNNING:
                    return jsonify({"error": "LTE 수집기가 실행 중이 아닙니다"})
                
                # 실제 LTE 모듈에서 데이터 수집
                data = self._collect_lte_data()
                return jsonify(asdict(data))
                
            except Exception as e:
                self.logger.error(f"LTE 데이터 조회 오류: {e}")
                return jsonify({"error": str(e)}), 500

    def _init_serial_connection(self):
        """시리얼 연결 초기화"""
        try:
            if self.serial_conn:
                self.serial_conn.close()
            
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=115200,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # 모듈 초기화 확인
            self._send_at_command("AT")
            self.logger.info(f"LTE 모듈 시리얼 연결 성공: {self.serial_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"시리얼 연결 실패: {e}")
            return False

    def _send_at_command(self, command: str, timeout: float = 1.0) -> Optional[str]:
        """AT 명령 전송 및 응답 수신"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            # 명령 전송
            self.serial_conn.write((command + '\r\n').encode())
            time.sleep(0.1)
            
            # 응답 수신
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

    def _collect_lte_data(self) -> LTEData:
        """실제 LTE 모듈에서 데이터 수집"""
        collect_time = datetime.utcnow()
        precise_timestamp = collect_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        data = LTEData(timestamp=precise_timestamp)
        
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
                    data.frequency_band = match.group(3)
                    data.earfcn = int(match.group(4))
            
            # 네트워크 등록 상태 조회 (AT+CREG?)
            creg_response = self._send_at_command("AT+CREG?")
            if creg_response and "+CREG:" in creg_response:
                match = re.search(r'\+CREG:\s*\d+,(\d+)', creg_response)
                if match:
                    reg_status = int(match.group(1))
                    status_map = {1: "REGISTERED", 2: "SEARCHING", 3: "DENIED", 5: "ROAMING"}
                    data.network_reg_status = status_map.get(reg_status, "UNKNOWN")
                    data.connection_state = "CONNECTED" if reg_status in [1, 5] else "DISCONNECTED"
            
            # EPS 네트워크 등록 상태 조회 (AT+CEREG?)
            cereg_response = self._send_at_command("AT+CEREG?")
            if cereg_response and "+CEREG:" in cereg_response:
                match = re.search(r'\+CEREG:\s*\d+,(\d+)', cereg_response)
                if match:
                    eps_status = int(match.group(1))
                    status_map = {1: "REGISTERED", 2: "SEARCHING", 3: "DENIED", 5: "ROAMING"}
                    data.eps_reg_status = status_map.get(eps_status, "UNKNOWN")
            
            # 패킷 데이터 카운터 조회 (AT+QGDCNT?)
            cnt_response = self._send_at_command("AT+QGDCNT?")
            if cnt_response and "+QGDCNT:" in cnt_response:
                match = re.search(r'\+QGDCNT:\s*(\d+),(\d+)', cnt_response)
                if match:
                    data.tx_bytes = int(match.group(1))
                    data.rx_bytes = int(match.group(2))
            
            # IP 주소 조회 (AT+CGPADDR=1)
            ip_response = self._send_at_command("AT+CGPADDR=1")
            if ip_response and "+CGPADDR:" in ip_response:
                match = re.search(r'\+CGPADDR:\s*1,"([^"]+)"', ip_response)
                if match:
                    data.ip_address = match.group(1)
            
            # 통신사 정보 조회 (AT+COPS?)
            cops_response = self._send_at_command("AT+COPS?")
            if cops_response and "+COPS:" in cops_response:
                match = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', cops_response)
                if match:
                    data.network_operator = match.group(1)
            
        except Exception as e:
            self.logger.error(f"LTE 데이터 수집 오류: {e}")
        
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
            # 시리얼 연결 초기화
            if not self._init_serial_connection():
                raise Exception("LTE 모듈 시리얼 연결 실패")
            
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
            if self.serial_conn:
                self.serial_conn.close()
            raise

    def _stop_collection(self):
        """수집 중지"""
        self._set_state(CollectorState.STOPPING)
        
        try:
            # 수집 중지
            self.running = False
            
            # 스레드 종료 대기
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5)
            
            # 시리얼 연결 종료
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            
            # 현재 파일 안전하게 닫기
            self._close_current_file()
            
            self._set_state(CollectorState.IDLE)
            self.logger.info(f"LTE 데이터 수집이 중지되었습니다 (총 {self.data_counter}개 데이터 수집)")
            
        except Exception as e:
            self._set_state(CollectorState.ERROR)
            raise

    def _create_new_file(self):
        """새 CSV 파일 생성"""
        # 기존 파일 닫기
        if self.current_file_handle:
            self.current_file_handle.close()
        
        # 새 파일명 생성
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"lte_module_{timestamp}.csv"
        self.current_file = self.data_dir / filename
        self.file_start_time = datetime.utcnow()
        
        # 헤더 작성
        self.current_file_handle = open(self.current_file, 'w')
        header = [
            "timestamp", "module_id", "connection_state", "uptime",
            "signal_quality_rssi", "signal_quality_ber", "network_operator", "network_mode",
            "network_reg_status", "eps_reg_status", "cell_id", "lac",
            "rx_bytes", "tx_bytes", "ip_address", "frequency_band", "earfcn",
            "latitude", "longitude", "altitude"
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
        
        # 시간 체크 (10분)
        duration = datetime.utcnow() - self.file_start_time
        if duration.total_seconds() > self.max_file_duration:
            return True
        
        # 크기 체크 (30MB)
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
                data.signal_quality_rssi, data.signal_quality_ber, data.network_operator, data.network_mode,
                data.network_reg_status, data.eps_reg_status, data.cell_id, data.lac,
                data.rx_bytes, data.tx_bytes, data.ip_address, data.frequency_band, data.earfcn,
                data.latitude, data.longitude, data.altitude
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
                # 파일 로테이션 확인
                if self._should_rotate_file():
                    self.logger.info("파일 로테이션 수행")
                    self._close_current_file()
                    self._create_new_file()
                
                # LTE 데이터 수집 및 저장
                data = self._collect_lte_data()
                self._save_to_csv(data)
                
                self.logger.debug(f"LTE 데이터 수집: RSSI={data.signal_quality_rssi}, 상태={data.connection_state}")
                
            except Exception as e:
                self.logger.error(f"수집 루프 오류: {e}")
                self._set_state(CollectorState.ERROR)
            
            # 5초 주기 유지 (LTE는 빠른 변화가 적음)
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
    parser.add_argument('--data-dir', default='./lte-data', help='데이터 저장 디렉토리')
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