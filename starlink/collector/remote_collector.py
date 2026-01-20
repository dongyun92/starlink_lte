#!/usr/bin/env python3
"""
테스트용 원격 제어 수집기 (스타링크 없이도 동작)
"""

import json
import time
import threading
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from enum import Enum

try:
    import grpc
    from spacex.api.device import device_pb2_grpc
    from spacex.api.device import device_pb2
    HAS_STARLINK_GRPC = True
except Exception:
    HAS_STARLINK_GRPC = False

class CollectorState(Enum):
    """수집기 상태"""
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

@dataclass
class MockStarlinkData:
    """모의 스타링크 데이터"""
    timestamp: str
    terminal_id: str = "ut01000000-00000000-test123"
    state: str = "CONNECTED"
    uptime: int = 3600
    downlink_throughput_bps: float = 25000000.0
    uplink_throughput_bps: float = 3000000.0
    ping_drop_rate: float = 0.0
    ping_latency_ms: float = 35.5
    snr: float = 8.2
    seconds_to_first_nonempty_slot: int = 15
    azimuth: float = 45.3
    elevation: float = 25.7
    pop_ping_drop_rate: float = 0.0
    pop_ping_latency_ms: float = 28.3
    latitude: float = 37.5665
    longitude: float = 126.9780
    altitude: float = 120.0

class TestRemoteControlledCollector:
    """원격 제어 수집기"""
    
    def __init__(self, data_dir="./test-data", control_port=8899, mode="real", dish_ip="192.168.100.1", dish_port=9200, interval=1.0):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.control_port = control_port
        self.mode = mode
        self.dish_ip = dish_ip
        self.dish_port = dish_port
        self.collection_interval = interval
        
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
        
        # 파일 관리 설정
        self.max_file_duration = 600  # 10분 (600초)
        self.max_file_size = 30 * 1024 * 1024  # 30MB
        
        # Starlink gRPC
        self.grpc_channel = None
        self.grpc_stub = None
        
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
                    "mode": self.mode,
                    "current_file": file_info["filename"] if file_info else None,
                    "file_size": file_info["size_mb"] if file_info else 0,
                    "duration": self._get_collection_duration(),
                    "file_count": len(self._get_today_files()),
                    "data_points": self.data_counter,
                    "last_update": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                })
        
        @self.app.route('/api/start', methods=['POST'])
        def start_collection():
            """수집 시작"""
            try:
                if self.state != CollectorState.IDLE:
                    return jsonify({"error": f"수집기가 {self.state.value} 상태입니다"}), 400
                
                self._start_collection()
                return jsonify({"message": "테스트 수집이 시작되었습니다", "state": self.state.value})
                
            except Exception as e:
                self.logger.error(f"수집 시작 오류: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/stop', methods=['POST'])
        def stop_collection():
            """수집 중지"""
            try:
                if self.state not in [CollectorState.RUNNING, CollectorState.ERROR]:
                    return jsonify({"error": f"수집기가 {self.state.value} 상태입니다"}), 400
                
                self._stop_collection()
                return jsonify({"message": "테스트 수집이 중지되었습니다", "state": self.state.value})
                
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
            """현재 실시간 데이터 반환"""
            try:
                if self.state != CollectorState.RUNNING:
                    return jsonify({"error": "수집기가 실행 중이 아닙니다"})
                
                if self.mode == "real":
                    data = self._get_real_data()
                    if not data:
                        return jsonify({"error": "실데이터 수집 실패"})
                else:
                    data = self._generate_mock_data()
                return jsonify(asdict(data))
                
            except Exception as e:
                self.logger.error(f"현재 데이터 조회 오류: {e}")
                return jsonify({"error": str(e)}), 500

    def _set_state(self, new_state: CollectorState):
        """상태 변경"""
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            self.logger.info(f"상태 변경: {old_state.value} → {new_state.value}")

    def _start_collection(self):
        """수집 시작"""
        self._set_state(CollectorState.STARTING)
        
        try:
            if self.mode == "real" and not HAS_STARLINK_GRPC:
                raise RuntimeError("starlink-grpc not installed (pip install starlink-grpc)")

            # 새 파일 생성
            self._create_new_file()
            
            # 수집 스레드 시작
            self.running = True
            self.collection_start_time = datetime.now(timezone.utc)
            self.data_counter = 0
            self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
            self.collection_thread.start()
            
            self._set_state(CollectorState.RUNNING)
            self.logger.info("테스트 데이터 수집이 시작되었습니다")
            
        except Exception as e:
            self._set_state(CollectorState.ERROR)
            raise

    def _connect_grpc(self):
        if not HAS_STARLINK_GRPC:
            return False
        try:
            self.grpc_channel = grpc.insecure_channel(f"{self.dish_ip}:{self.dish_port}")
            self.grpc_stub = device_pb2_grpc.DeviceStub(self.grpc_channel)
            return True
        except Exception as e:
            self.logger.error(f"gRPC 연결 실패: {e}")
            self.grpc_channel = None
            self.grpc_stub = None
            return False

    def _get_real_data(self) -> Optional[MockStarlinkData]:
        if not self.grpc_stub and not self._connect_grpc():
            return None
        try:
            request = device_pb2.Request()
            request.get_status.CopyFrom(device_pb2.GetStatusRequest())
            response = self.grpc_stub.Handle(request)

            status = response.dish_get_status
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            return MockStarlinkData(
                timestamp=timestamp,
                terminal_id=getattr(status.device_info, "id", "") or "",
                state=str(getattr(status, "state", "")),
                uptime=getattr(status.device_info, "uptime_s", 0),
                downlink_throughput_bps=getattr(status, "downlink_throughput_bps", 0.0),
                uplink_throughput_bps=getattr(status, "uplink_throughput_bps", 0.0),
                ping_drop_rate=getattr(status, "pop_ping_drop_rate", 0.0),
                ping_latency_ms=getattr(status, "pop_ping_latency_ms", 0.0),
                snr=getattr(status, "snr", 0.0),
                seconds_to_first_nonempty_slot=getattr(status, "seconds_to_first_nonempty_slot", 0),
                azimuth=getattr(status, "azimuth_deg", 0.0),
                elevation=getattr(status, "elevation_deg", 0.0),
                pop_ping_drop_rate=getattr(status, "pop_ping_drop_rate", 0.0),
                pop_ping_latency_ms=getattr(status, "pop_ping_latency_ms", 0.0),
                latitude=getattr(status.gps_stats, "latitude", 0.0),
                longitude=getattr(status.gps_stats, "longitude", 0.0),
                altitude=getattr(status.gps_stats, "altitude", 0.0),
            )
        except Exception as e:
            self.logger.error(f"실데이터 수집 실패: {e}")
            self.grpc_stub = None
            return None

    def _stop_collection(self):
        """수집 중지"""
        self._set_state(CollectorState.STOPPING)
        
        try:
            # 수집 중지
            self.running = False
            
            # 스레드 종료 대기
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5)
            
            # 현재 파일 안전하게 닫기
            self._close_current_file()
            
            self._set_state(CollectorState.IDLE)
            self.logger.info(f"테스트 데이터 수집이 중지되었습니다 (총 {self.data_counter}개 데이터 수집)")
            
        except Exception as e:
            self._set_state(CollectorState.ERROR)
            raise

    def _create_new_file(self):
        """새 CSV 파일 생성"""
        # 기존 파일 닫기
        if self.current_file_handle:
            self.current_file_handle.close()
        
        # 새 파일명 생성
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"test_starlink_{timestamp}.csv"
        self.current_file = self.data_dir / filename
        self.file_start_time = datetime.now(timezone.utc)
        
        # 헤더 작성
        self.current_file_handle = open(self.current_file, 'w')
        header = [
            "timestamp", "terminal_id", "state", "uptime",
            "downlink_throughput_bps", "uplink_throughput_bps",
            "ping_drop_rate", "ping_latency_ms", "snr",
            "seconds_to_first_nonempty_slot", "azimuth", "elevation",
            "pop_ping_drop_rate", "pop_ping_latency_ms",
            "latitude", "longitude", "altitude"
        ]
        self.current_file_handle.write(','.join(header) + '\n')
        self.current_file_handle.flush()
        
        self.logger.info(f"새 테스트 파일 생성: {filename}")

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
        
        # 시간 체크 (테스트: 1분)
        duration = datetime.now(timezone.utc) - self.file_start_time
        if duration.total_seconds() > self.max_file_duration:
            return True
        
        # 크기 체크 (테스트: 1MB)
        if self.current_file.exists() and self.current_file.stat().st_size > self.max_file_size:
            return True
        
        return False

    def _generate_mock_data(self) -> MockStarlinkData:
        """모의 스타링크 데이터 생성"""
        # 실제와 유사한 랜덤 데이터 생성
        collect_time = datetime.now(timezone.utc)
        precise_timestamp = collect_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        return MockStarlinkData(
            timestamp=precise_timestamp,
            downlink_throughput_bps=random.uniform(20000000, 30000000),
            uplink_throughput_bps=random.uniform(2500000, 3500000),
            ping_latency_ms=random.uniform(30, 45),
            snr=random.uniform(7.5, 9.0),
            azimuth=random.uniform(0, 360),
            elevation=random.uniform(20, 30),
            pop_ping_latency_ms=random.uniform(25, 35)
        )

    def _save_to_csv(self, data: MockStarlinkData):
        """CSV 파일에 데이터 저장"""
        if not self.current_file_handle:
            return
        
        try:
            row = [
                data.timestamp, data.terminal_id, data.state, data.uptime,
                data.downlink_throughput_bps, data.uplink_throughput_bps,
                data.ping_drop_rate, data.ping_latency_ms, data.snr,
                data.seconds_to_first_nonempty_slot, data.azimuth, data.elevation,
                data.pop_ping_drop_rate, data.pop_ping_latency_ms,
                data.latitude, data.longitude, data.altitude
            ]
            
            self.current_file_handle.write(','.join(map(str, row)) + '\n')
            self.current_file_handle.flush()
            self.data_counter += 1
            
        except Exception as e:
            self.logger.error(f"CSV 저장 오류: {e}")
            try:
                self._close_current_file()
                self._create_new_file()
                self.current_file_handle.write(','.join(map(str, row)) + '\n')
                self.current_file_handle.flush()
                self.data_counter += 1
            except Exception as retry_error:
                self.logger.error(f"CSV 저장 재시도 실패: {retry_error}")

    def _collection_loop(self):
        """메인 데이터 수집 루프"""
        self.logger.info("테스트 데이터 수집 루프 시작")
        
        while self.running:
            start_time = time.time()
            
            try:
                # 파일 로테이션 확인
                if self._should_rotate_file():
                    self.logger.info("파일 로테이션 수행")
                    self._close_current_file()
                    self._create_new_file()
                
                # 데이터 생성 및 저장
                if self.mode == "real":
                    data = self._get_real_data()
                else:
                    data = self._generate_mock_data()

                if data:
                    self._save_to_csv(data)
                    self._set_state(CollectorState.RUNNING)
                else:
                    self._set_state(CollectorState.ERROR)
                
            except Exception as e:
                self.logger.error(f"수집 루프 오류: {e}")
                self._set_state(CollectorState.ERROR)
                try:
                    if not self.current_file_handle:
                        self._create_new_file()
                except Exception as retry_error:
                    self.logger.error(f"파일 복구 실패: {retry_error}")
            
            # 주기 유지
            elapsed = time.time() - start_time
            sleep_time = max(0, self.collection_interval - elapsed)
            time.sleep(sleep_time)
        
        self.logger.info("테스트 데이터 수집 루프 종료")

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
        for file_path in self.data_dir.glob("test_starlink_*.csv"):
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
        
        duration = datetime.now(timezone.utc) - self.collection_start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def run_control_server(self):
        """제어 서버 실행"""
        self.logger.info(f"테스트 제어 서버 시작: http://0.0.0.0:{self.control_port}")
        self.app.run(host='0.0.0.0', port=self.control_port, debug=False)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='원격 제어 수집기')
    parser.add_argument('--data-dir', default='./test-data', help='데이터 저장 디렉토리')
    parser.add_argument('--control-port', type=int, default=8899, help='제어 API 포트')
    parser.add_argument('--mode', choices=['real', 'mock'], default='real', help='수집 모드')
    parser.add_argument('--dish-ip', default='192.168.100.1', help='Starlink dish IP')
    parser.add_argument('--dish-port', type=int, default=9200, help='Starlink dish gRPC port')
    parser.add_argument('--interval', type=float, default=1.0, help='수집 주기 (초)')
    
    args = parser.parse_args()
    
    collector = TestRemoteControlledCollector(
        data_dir=args.data_dir,
        control_port=args.control_port,
        mode=args.mode,
        dish_ip=args.dish_ip,
        dish_port=args.dish_port,
        interval=args.interval,
    )
    collector.run_control_server()

if __name__ == "__main__":
    main()
