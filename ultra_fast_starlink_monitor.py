#!/usr/bin/env python3
"""
🚀 Ultra-Fast Starlink Monitor - 100ms Realtime Dashboard
9000x faster than the original 15-minute limitation!

기능:
- 100ms 간격 실시간 데이터 수집 (vs 기존 15분)
- 실제 스타링크 gRPC API 사용
- WebSocket 실시간 대시보드
- 고정 포트: 8888
- 모든 메트릭 수집 및 시각화
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import json
import time
import threading
import csv
import os
from datetime import datetime, timezone
from typing import Dict, Any
import logging
import sys

class UltraFastStarlinkMonitor:
    def __init__(self, dish_ip: str = "192.168.100.1", update_interval: float = 0.1):
        self.dish_ip = dish_ip
        self.update_interval = update_interval  # 100ms = 0.1초
        self.grpc_tools_path = "starlink-grpc-tools"
        
        # Flask app setup (포트 8888 고정)
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'ultra_fast_starlink_8888'
        self.socketio = SocketIO(self.app, 
                                cors_allowed_origins="*", 
                                logger=False,  # 성능을 위해 로그 최소화
                                engineio_logger=False)
        
        # Data storage
        self.latest_data = {}
        self.data_history = []
        self.update_count = 0
        
        # Monitoring flags
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Performance tracking
        self.start_time = time.time()
        self.last_update_time = 0
        
        # Setup
        self.setup_logging()
        self.setup_routes()
        self.setup_csv_logging()
        
    def setup_logging(self):
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def setup_csv_logging(self):
        """CSV 로깅 설정 (Ultra-fast 버전)"""
        self.csv_filename = f"ultrafast_starlink_data_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # CSV 헤더 작성 (실제 스타링크 필드들)
        if not os.path.exists(self.csv_filename):
            headers = [
                'timestamp', 'update_count', 'interval_ms',
                'id', 'hardware_version', 'software_version', 'state', 'uptime',
                'pop_ping_drop_rate', 'pop_ping_latency_ms', 'downlink_throughput_bps', 
                'uplink_throughput_bps', 'seconds_to_first_nonempty_slot',
                'alerts_bit_field', 'fraction_obstructed', 'currently_obstructed',
                'obstruction_duration', 'obstruction_interval',
                'direction_azimuth', 'direction_elevation',
                'is_snr_above_noise_floor', 'gps_ready', 'gps_enabled', 'gps_sats'
            ]
            
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def setup_routes(self):
        """Flask 라우트 설정"""
        
        @self.app.route('/')
        def dashboard():
            return render_template('ultra_fast_dashboard.html')
        
        @self.app.route('/api/data')
        def get_data():
            return jsonify(self.latest_data)
        
        @self.app.route('/api/start')
        def start_monitoring():
            self.start_monitoring()
            return jsonify({"status": "started", "interval_ms": int(self.update_interval * 1000)})
        
        @self.app.route('/api/stop') 
        def stop_monitoring():
            self.stop_monitoring()
            return jsonify({"status": "stopped"})
        
        @self.app.route('/api/stats')
        def get_stats():
            runtime = time.time() - self.start_time
            return jsonify({
                "update_count": self.update_count,
                "runtime_seconds": runtime,
                "updates_per_second": self.update_count / runtime if runtime > 0 else 0,
                "interval_ms": int(self.update_interval * 1000),
                "csv_file": self.csv_filename
            })
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('🚀 Ultra-Fast WebSocket 클라이언트 연결')
            emit('status', {'data': self.latest_data})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info('🛑 Ultra-Fast WebSocket 클라이언트 해제')
    
    def start_monitoring(self):
        """초고속 모니터링 시작 (100ms)"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self.ultra_fast_monitoring_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.logger.warning(f"🚀 Ultra-Fast 모니터링 시작 - {int(self.update_interval * 1000)}ms 간격")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.logger.warning("🛑 Ultra-Fast 모니터링 중지")
    
    def ultra_fast_monitoring_loop(self):
        """🔥 Ultra-Fast 메인 모니터링 루프 (100ms)"""
        while self.monitoring_active:
            try:
                loop_start = time.time()
                
                # 실제 스타링크 데이터 수집
                data = self.collect_real_starlink_data()
                
                if data:
                    # 업데이트 카운트 및 성능 메트릭
                    self.update_count += 1
                    current_time = time.time()
                    interval_ms = (current_time - self.last_update_time) * 1000 if self.last_update_time > 0 else 0
                    self.last_update_time = current_time
                    
                    data['update_count'] = self.update_count
                    data['interval_ms'] = interval_ms
                    data['timestamp'] = datetime.now(timezone.utc).isoformat()
                    
                    # 최신 데이터 업데이트
                    self.latest_data = data
                    
                    # CSV에 저장 (매 100회마다 - 성능 최적화)
                    if self.update_count % 100 == 0:
                        self.save_to_csv(data)
                    
                    # WebSocket 실시간 업데이트
                    self.socketio.emit('ultra_update', data)
                    
                    # 데이터 히스토리 (최근 1000개)
                    self.data_history.append(data)
                    if len(self.data_history) > 1000:
                        self.data_history.pop(0)
                    
                    # 성능 로그 (1000회마다)
                    if self.update_count % 1000 == 0:
                        runtime = time.time() - self.start_time
                        ups = self.update_count / runtime if runtime > 0 else 0
                        self.logger.warning(f"🔥 {self.update_count}회 업데이트 완료 - {ups:.1f} UPS")
                
                # 정확한 100ms 간격 유지
                loop_time = time.time() - loop_start
                sleep_time = max(0, self.update_interval - loop_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Ultra-Fast 루프 오류: {e}")
                time.sleep(self.update_interval)
    
    def collect_real_starlink_data(self) -> Dict[str, Any]:
        """🛰️ 실제 스타링크 gRPC API에서 데이터 수집"""
        try:
            # 오픈소스 gRPC 도구 호출
            cmd = [
                sys.executable, 'dish_grpc_text.py',
                '-g', f'{self.dish_ip}:9200',
                'status'
            ]
            
            result = subprocess.run(cmd, 
                                   cwd=self.grpc_tools_path,
                                   capture_output=True, 
                                   text=True, 
                                   timeout=0.05)  # 50ms 타임아웃
            
            if result.returncode == 0:
                return self.parse_grpc_output(result.stdout)
            else:
                return self.create_error_data(f"gRPC 오류: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            return self.create_error_data("50ms 타임아웃")
        except Exception as e:
            return self.create_error_data(f"수집 오류: {e}")
    
    def parse_grpc_output(self, output: str) -> Dict[str, Any]:
        """gRPC 출력을 파싱하여 딕셔너리로 변환"""
        try:
            lines = output.strip().split(',')
            if len(lines) >= 20:  # 최소 필수 필드 확인
                return {
                    'status': 'success',
                    'id': lines[1] if len(lines) > 1 else '',
                    'hardware_version': lines[2] if len(lines) > 2 else '',
                    'software_version': lines[3] if len(lines) > 3 else '',
                    'state': lines[4] if len(lines) > 4 else '',
                    'uptime': int(lines[5]) if len(lines) > 5 and lines[5].isdigit() else 0,
                    'seconds_to_first_nonempty_slot': float(lines[6]) if len(lines) > 6 and lines[6] else 0,
                    'pop_ping_drop_rate': float(lines[7]) if len(lines) > 7 and lines[7] else 0,
                    'pop_ping_latency_ms': float(lines[8]) if len(lines) > 8 and lines[8] else 0,
                    'downlink_throughput_bps': float(lines[9]) if len(lines) > 9 and lines[9] else 0,
                    'uplink_throughput_bps': float(lines[10]) if len(lines) > 10 and lines[10] else 0,
                    'fraction_obstructed': float(lines[11]) if len(lines) > 11 and lines[11] else 0,
                    'alerts_bit_field': int(lines[12]) if len(lines) > 12 and lines[12].isdigit() else 0,
                    'currently_obstructed': lines[13] == 'True' if len(lines) > 13 else False,
                    'obstruction_duration': float(lines[15]) if len(lines) > 15 and lines[15] else 0,
                    'obstruction_interval': float(lines[16]) if len(lines) > 16 and lines[16] else 0,
                    'direction_azimuth': float(lines[17]) if len(lines) > 17 and lines[17] else 0,
                    'direction_elevation': float(lines[18]) if len(lines) > 18 and lines[18] else 0,
                    'is_snr_above_noise_floor': lines[19] == 'True' if len(lines) > 19 else False,
                    'gps_ready': lines[20] == 'True' if len(lines) > 20 else False,
                    'gps_enabled': lines[21] == 'True' if len(lines) > 21 else False,
                    'gps_sats': int(lines[22]) if len(lines) > 22 and lines[22].isdigit() else 0
                }
            else:
                return self.create_error_data("데이터 파싱 실패")
        except Exception as e:
            return self.create_error_data(f"파싱 오류: {e}")
    
    def create_error_data(self, error_msg: str) -> Dict[str, Any]:
        """오류 상황에서 기본 데이터 구조"""
        return {
            'status': 'error',
            'error': error_msg,
            'id': 'unknown',
            'state': 'ERROR',
            'pop_ping_latency_ms': 0,
            'downlink_throughput_bps': 0,
            'uplink_throughput_bps': 0,
            'direction_azimuth': 0,
            'direction_elevation': 0,
            'gps_sats': 0
        }
    
    def save_to_csv(self, data: Dict[str, Any]):
        """CSV 파일에 데이터 저장 (배치 처리로 성능 최적화)"""
        try:
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                row = [
                    data.get('timestamp', ''),
                    data.get('update_count', 0),
                    data.get('interval_ms', 0),
                    data.get('id', ''),
                    data.get('hardware_version', ''),
                    data.get('software_version', ''),
                    data.get('state', ''),
                    data.get('uptime', 0),
                    data.get('pop_ping_drop_rate', 0),
                    data.get('pop_ping_latency_ms', 0),
                    data.get('downlink_throughput_bps', 0),
                    data.get('uplink_throughput_bps', 0),
                    data.get('seconds_to_first_nonempty_slot', 0),
                    data.get('alerts_bit_field', 0),
                    data.get('fraction_obstructed', 0),
                    data.get('currently_obstructed', False),
                    data.get('obstruction_duration', 0),
                    data.get('obstruction_interval', 0),
                    data.get('direction_azimuth', 0),
                    data.get('direction_elevation', 0),
                    data.get('is_snr_above_noise_floor', False),
                    data.get('gps_ready', False),
                    data.get('gps_enabled', False),
                    data.get('gps_sats', 0)
                ]
                writer.writerow(row)
        except Exception as e:
            self.logger.error(f"CSV 저장 실패: {e}")

# Ultra-Fast HTML 템플릿 (고성능 최적화)
ULTRA_FAST_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Ultra-Fast Starlink Monitor (100ms)</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Monaco', 'Consolas', monospace;
            background: linear-gradient(135deg, #000000 0%, #1a1a2e 50%, #16213e 100%);
            color: #00ff41; min-height: 100vh; padding: 10px;
            overflow-x: hidden;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { 
            text-align: center; margin-bottom: 20px; 
            border: 2px solid #00ff41; padding: 15px; border-radius: 10px;
            background: rgba(0, 255, 65, 0.1);
        }
        .header h1 { 
            color: #00ff41; margin-bottom: 5px; font-size: 2em; 
            text-shadow: 0 0 10px #00ff41;
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 10px #00ff41; }
            to { text-shadow: 0 0 20px #00ff41, 0 0 30px #00ff41; }
        }
        .perf-bar { 
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(0, 255, 65, 0.1); padding: 10px; border-radius: 5px;
            margin-bottom: 15px; border: 1px solid #00ff41;
        }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 15px; }
        .card { 
            background: rgba(0, 255, 65, 0.05); border-radius: 10px; padding: 15px;
            border: 1px solid #00ff41; backdrop-filter: blur(5px);
        }
        .card h3 { 
            color: #00ff41; margin-bottom: 10px; font-size: 1.2em;
            text-shadow: 0 0 5px #00ff41;
        }
        .metric { 
            display: flex; justify-content: space-between; margin: 8px 0; 
            padding: 5px; border-bottom: 1px solid rgba(0, 255, 65, 0.2);
        }
        .metric-value { 
            font-weight: bold; color: #ffffff;
            font-family: 'Monaco', monospace;
        }
        .status-good { color: #00ff41; }
        .status-warning { color: #ffaa00; }
        .status-error { color: #ff4444; }
        .controls { text-align: center; margin: 15px 0; }
        .btn { 
            background: linear-gradient(45deg, #00ff41, #00cc33); 
            color: #000; border: none; padding: 12px 20px;
            border-radius: 5px; margin: 0 5px; cursor: pointer; font-size: 14px;
            font-weight: bold; text-transform: uppercase;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            background: linear-gradient(45deg, #00cc33, #00ff41);
            transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0, 255, 65, 0.3);
        }
        .btn.stop { background: linear-gradient(45deg, #ff4444, #cc0000); color: white; }
        .btn.stop:hover { background: linear-gradient(45deg, #cc0000, #ff4444); }
        .chart-container { height: 200px; margin-top: 10px; }
        .realtime-indicator { 
            position: fixed; top: 10px; right: 10px; 
            background: #00ff41; color: #000; padding: 8px 12px; 
            border-radius: 5px; font-size: 12px; font-weight: bold;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        .fps-counter { 
            font-size: 16px; font-weight: bold; color: #00ff41;
            text-shadow: 0 0 5px #00ff41;
        }
        .data-flash {
            animation: flash 0.1s ease-in-out;
        }
        @keyframes flash {
            0% { background-color: rgba(0, 255, 65, 0.3); }
            100% { background-color: transparent; }
        }
    </style>
</head>
<body>
    <div class="realtime-indicator" id="realtime-status">🔴 대기중</div>
    
    <div class="container">
        <div class="header">
            <h1>🚀 Ultra-Fast Starlink Monitor</h1>
            <p>⚡ 100ms 실시간 수집 - 15분 제한의 9000배 향상!</p>
        </div>
        
        <div class="perf-bar">
            <div>
                <span class="fps-counter">업데이트: <span id="update-count">0</span>회</span>
                <span style="margin-left: 20px;">FPS: <span id="fps-display" class="fps-counter">0</span></span>
            </div>
            <div>
                <span>간격: <span id="interval">100</span>ms</span>
                <span style="margin-left: 20px;">상태: <span id="connection-status" class="status-good">대기</span></span>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn" onclick="startUltraFast()">🚀 초고속 시작</button>
            <button class="btn stop" onclick="stopUltraFast()">⏹️ 중지</button>
            <button class="btn" onclick="showStats()">📊 통계</button>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🛰️ 실시간 상태</h3>
                <div class="metric">
                    <span>디바이스 ID:</span>
                    <span id="device-id" class="metric-value">-</span>
                </div>
                <div class="metric">
                    <span>상태:</span>
                    <span id="dish-state" class="metric-value">-</span>
                </div>
                <div class="metric">
                    <span>업타임:</span>
                    <span id="uptime" class="metric-value">0초</span>
                </div>
                <div class="metric">
                    <span>소프트웨어:</span>
                    <span id="software-version" class="metric-value">-</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🌐 네트워크 성능</h3>
                <div class="metric">
                    <span>다운로드:</span>
                    <span id="download-speed" class="metric-value">0 Mbps</span>
                </div>
                <div class="metric">
                    <span>업로드:</span>
                    <span id="upload-speed" class="metric-value">0 Mbps</span>
                </div>
                <div class="metric">
                    <span>Ping 지연:</span>
                    <span id="ping-latency" class="metric-value">0 ms</span>
                </div>
                <div class="metric">
                    <span>패킷 드롭율:</span>
                    <span id="drop-rate" class="metric-value">0%</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📡 디시 방향</h3>
                <div class="metric">
                    <span>방위각:</span>
                    <span id="azimuth" class="metric-value">0°</span>
                </div>
                <div class="metric">
                    <span>고도각:</span>
                    <span id="elevation" class="metric-value">0°</span>
                </div>
                <div class="metric">
                    <span>GPS 위성:</span>
                    <span id="gps-sats" class="metric-value">0</span>
                </div>
                <div class="metric">
                    <span>장애물 비율:</span>
                    <span id="obstruction" class="metric-value">0%</span>
                </div>
            </div>
            
            <div class="card">
                <h3>⚡ 실시간 메트릭</h3>
                <div class="metric">
                    <span>업데이트 횟수:</span>
                    <span id="metric-updates" class="metric-value status-good">0</span>
                </div>
                <div class="metric">
                    <span>실제 간격:</span>
                    <span id="actual-interval" class="metric-value">0 ms</span>
                </div>
                <div class="metric">
                    <span>마지막 업데이트:</span>
                    <span id="last-update" class="metric-value">-</span>
                </div>
                <div class="metric">
                    <span>데이터 소스:</span>
                    <span id="data-source" class="metric-value">Ultra-Fast gRPC</span>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>📊 실시간 성능 차트 (100ms)</h3>
            <div class="chart-container">
                <canvas id="ultraChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        // Ultra-Fast WebSocket 연결 (포트 8888 고정)
        const socket = io(':8888');
        let chart;
        let updateCount = 0;
        let lastUpdateTime = Date.now();
        let fpsCounter = 0;
        let fpsStartTime = Date.now();
        
        const chartData = {
            labels: [],
            datasets: [
                {
                    label: '다운로드 (Mbps)',
                    data: [],
                    borderColor: '#00ff41',
                    backgroundColor: 'rgba(0, 255, 65, 0.1)',
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: 'Ping (ms)',
                    data: [],
                    borderColor: '#ffaa00', 
                    backgroundColor: 'rgba(255, 170, 0, 0.1)',
                    tension: 0.1,
                    pointRadius: 0
                }
            ]
        };
        
        function initChart() {
            const ctx = document.getElementById('ultraChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,  // 성능을 위해 애니메이션 비활성화
                    plugins: { legend: { labels: { color: '#00ff41' } } },
                    scales: {
                        x: { 
                            ticks: { color: '#00ff41', maxTicksLimit: 10 }, 
                            grid: { color: 'rgba(0, 255, 65, 0.2)' } 
                        },
                        y: { 
                            ticks: { color: '#00ff41' }, 
                            grid: { color: 'rgba(0, 255, 65, 0.2)' } 
                        }
                    }
                }
            });
        }
        
        function updateUltraData(data) {
            updateCount++;
            fpsCounter++;
            
            // FPS 계산
            const now = Date.now();
            if (now - fpsStartTime >= 1000) {
                document.getElementById('fps-display').textContent = fpsCounter;
                fpsCounter = 0;
                fpsStartTime = now;
            }
            
            // 실제 간격 계산
            const actualInterval = now - lastUpdateTime;
            lastUpdateTime = now;
            
            // 메트릭 업데이트 (플래시 효과)
            const elements = document.querySelectorAll('.metric');
            elements.forEach(el => {
                el.classList.add('data-flash');
                setTimeout(() => el.classList.remove('data-flash'), 100);
            });
            
            // 데이터 업데이트
            document.getElementById('update-count').textContent = updateCount;
            document.getElementById('device-id').textContent = data.id || '-';
            document.getElementById('dish-state').textContent = data.state || '-';
            document.getElementById('uptime').textContent = (data.uptime || 0) + '초';
            document.getElementById('software-version').textContent = data.software_version || '-';
            
            // 네트워크 성능
            const downloadMbps = ((data.downlink_throughput_bps || 0) / 1000000).toFixed(1);
            const uploadMbps = ((data.uplink_throughput_bps || 0) / 1000000).toFixed(1);
            document.getElementById('download-speed').textContent = downloadMbps + ' Mbps';
            document.getElementById('upload-speed').textContent = uploadMbps + ' Mbps';
            document.getElementById('ping-latency').textContent = (data.pop_ping_latency_ms || 0).toFixed(1) + ' ms';
            document.getElementById('drop-rate').textContent = ((data.pop_ping_drop_rate || 0) * 100).toFixed(2) + '%';
            
            // 디시 방향
            document.getElementById('azimuth').textContent = (data.direction_azimuth || 0).toFixed(1) + '°';
            document.getElementById('elevation').textContent = (data.direction_elevation || 0).toFixed(1) + '°';
            document.getElementById('gps-sats').textContent = data.gps_sats || 0;
            document.getElementById('obstruction').textContent = ((data.fraction_obstructed || 0) * 100).toFixed(2) + '%';
            
            // 실시간 메트릭
            document.getElementById('metric-updates').textContent = updateCount;
            document.getElementById('actual-interval').textContent = actualInterval.toFixed(0) + ' ms';
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            // 차트 업데이트 (최근 100개만 유지)
            const timeLabel = new Date().toLocaleTimeString();
            chartData.labels.push(timeLabel);
            chartData.datasets[0].data.push(parseFloat(downloadMbps));
            chartData.datasets[1].data.push(data.pop_ping_latency_ms || 0);
            
            if (chartData.labels.length > 100) {
                chartData.labels.shift();
                chartData.datasets[0].data.shift();
                chartData.datasets[1].data.shift();
            }
            
            if (chart) chart.update('none');  // 애니메이션 없이 업데이트
            
            // 상태 표시기 업데이트
            document.getElementById('realtime-status').innerHTML = 
                `🟢 ${updateCount} (${actualInterval.toFixed(0)}ms)`;
            
            // 상태에 따른 색상 변경
            const statusElement = document.getElementById('connection-status');
            if (data.state === 'CONNECTED') {
                statusElement.textContent = 'CONNECTED';
                statusElement.className = 'status-good';
            } else if (data.status === 'error') {
                statusElement.textContent = 'ERROR';
                statusElement.className = 'status-error';
            } else {
                statusElement.textContent = data.state || '알수없음';
                statusElement.className = 'status-warning';
            }
        }
        
        function startUltraFast() {
            fetch('/api/start').then(r => r.json()).then(data => {
                console.log('🚀 Ultra-Fast 모니터링 시작:', data);
                document.getElementById('interval').textContent = data.interval_ms || 100;
            });
        }
        
        function stopUltraFast() {
            fetch('/api/stop').then(r => r.json()).then(data => {
                console.log('🛑 Ultra-Fast 모니터링 중지:', data);
            });
        }
        
        function showStats() {
            fetch('/api/stats').then(r => r.json()).then(data => {
                alert(`📊 Ultra-Fast 통계:
• 총 업데이트: ${data.update_count}회
• 실행 시간: ${data.runtime_seconds.toFixed(1)}초  
• 초당 업데이트: ${data.updates_per_second.toFixed(1)} UPS
• 설정 간격: ${data.interval_ms}ms
• CSV 파일: ${data.csv_file}`);
            });
        }
        
        // WebSocket 이벤트 처리
        socket.on('connect', function() {
            console.log('✅ Ultra-Fast WebSocket 연결:', socket.id);
            document.getElementById('realtime-status').innerHTML = '🟢 연결됨';
        });
        
        socket.on('disconnect', function() {
            console.log('❌ Ultra-Fast WebSocket 해제');
            document.getElementById('realtime-status').innerHTML = '🔴 연결끊김';
        });
        
        socket.on('ultra_update', function(data) {
            updateUltraData(data);
        });
        
        socket.on('status', function(msg) {
            if (msg.data) updateUltraData(msg.data);
        });
        
        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 Ultra-Fast Starlink Monitor 로드 완료');
            initChart();
        });
    </script>
</body>
</html>
"""

def create_ultra_fast_system():
    """🚀 Ultra-Fast 시스템 생성 및 실행"""
    # 템플릿 폴더 생성
    os.makedirs('templates', exist_ok=True)
    
    # HTML 템플릿 저장
    with open('templates/ultra_fast_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(ULTRA_FAST_HTML)
    
    # Ultra-Fast 모니터링 시스템 실행
    monitor = UltraFastStarlinkMonitor()
    print("🚀" * 20)
    print("   ULTRA-FAST STARLINK MONITOR")
    print("🚀" * 20)
    print(f"📊 대시보드: http://localhost:8888 (고정 포트)")
    print(f"⚡ 수집 간격: 100ms (vs 기존 15분)")
    print(f"🔥 성능 향상: 9000x faster")
    print(f"💾 CSV 로그: ultrafast_starlink_data_YYYYMMDD.csv")
    print(f"🛰️ 실제 gRPC API 사용")
    print(f"🎯 실시간 WebSocket 업데이트")
    print("🚀" * 20)
    
    monitor.socketio.run(monitor.app, host='0.0.0.0', port=8888, debug=False)

if __name__ == "__main__":
    create_ultra_fast_system()