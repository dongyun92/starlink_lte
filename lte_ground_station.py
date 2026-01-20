#!/usr/bin/env python3
"""
LTE 지상국 데이터 수신 및 모니터링 시스템
- 드론에서 전송된 LTE 통신 품질 데이터 수신
- 실시간 LTE 대시보드 제공
- LTE 데이터 저장 및 분석
"""

import json
import gzip
import time
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
import logging
from typing import Dict, List
from collections import deque
import sqlite3
import requests

class LTEGroundStationReceiver:
    """LTE 지상국 데이터 수신기"""
    
    def __init__(self, port=8079, data_dir="/opt/lte-ground-station-data"):
        self.port = port
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Flask 앱
        self.app = Flask(__name__)
        self.setup_routes()
        
        # 최소화된 모니터링용 실시간 데이터 버퍼 (최근 50개만)
        self.realtime_data = deque(maxlen=50)
        
        # 데이터베이스 설정
        self.db_file = self.data_dir / "lte_drone_data.db"
        self.setup_database()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / 'lte_ground_station.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """SQLite 데이터베이스 초기화"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lte_drone_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    module_id TEXT,
                    connection_state TEXT,
                    uptime INTEGER,
                    signal_quality_rssi INTEGER,
                    signal_quality_ber INTEGER,
                    network_operator TEXT,
                    network_mode TEXT,
                    network_reg_status TEXT,
                    eps_reg_status TEXT,
                    cell_id TEXT,
                    lac TEXT,
                    rx_bytes INTEGER,
                    tx_bytes INTEGER,
                    ip_address TEXT,
                    frequency_band TEXT,
                    earfcn INTEGER,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    received_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lte_timestamp ON lte_drone_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lte_received_at ON lte_drone_data(received_at)")

    def setup_routes(self):
        """Flask 라우트 설정"""
        
        @self.app.route('/upload_status', methods=['POST'])
        def upload_status():
            """드론 LTE 상태 정보 수신"""
            try:
                # 압축 해제
                if request.headers.get('Content-Encoding') == 'gzip':
                    data = gzip.decompress(request.data)
                    status_data = json.loads(data.decode('utf-8'))
                else:
                    status_data = request.get_json()
                
                # 드론 LTE 상태 정보 처리
                if 'recent_data' in status_data:
                    # 최근 데이터가 있으면 데이터베이스에 저장
                    self.save_to_database(status_data['recent_data'])
                    # 실시간 버퍼 업데이트
                    for item in status_data['recent_data']:
                        self.realtime_data.append(item)
                
                self.logger.info(f"드론 LTE 상태 수신: {status_data.get('connection_state', 'UNKNOWN')}")
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"LTE 상태 수신 오류: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/upload_data', methods=['POST'])
        def upload_data():
            """드론에서 전송된 LTE 데이터 수신"""
            try:
                # 압축 해제
                if request.headers.get('Content-Encoding') == 'gzip':
                    data = gzip.decompress(request.data)
                else:
                    data = request.data
                
                # JSON 파싱
                json_data = json.loads(data.decode('utf-8'))
                
                # 데이터베이스 저장
                self.save_to_database(json_data)
                
                # 실시간 버퍼 업데이트
                for item in json_data:
                    self.realtime_data.append(item)
                
                self.logger.info(f"수신된 LTE 데이터: {len(json_data)}개")
                
                return jsonify({"status": "success", "received_count": len(json_data)})
                
            except Exception as e:
                self.logger.error(f"LTE 데이터 수신 오류: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/api/latest_data')
        def get_latest_data():
            """최신 LTE 데이터 반환 (최소화된 모니터링용)"""
            if self.realtime_data:
                return jsonify(list(self.realtime_data)[-5:])  # 최근 5개만
            return jsonify([])

        @self.app.route('/api/stats')
        def get_stats():
            """LTE 통계 정보 반환"""
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                
                # 총 데이터 수
                total_count = conn.execute("SELECT COUNT(*) as count FROM lte_drone_data").fetchone()['count']
                
                # 최근 1시간 데이터 수
                recent_count = conn.execute("""
                    SELECT COUNT(*) as count FROM lte_drone_data 
                    WHERE received_at > datetime('now', '-1 hour')
                """).fetchone()['count']
                
                # 평균 성능 지표 (최근 1시간)
                stats = conn.execute("""
                    SELECT 
                        AVG(signal_quality_rssi) as avg_rssi,
                        AVG(rx_bytes) as avg_rx,
                        AVG(tx_bytes) as avg_tx,
                        COUNT(DISTINCT network_operator) as operator_count
                    FROM lte_drone_data 
                    WHERE received_at > datetime('now', '-1 hour')
                """).fetchone()
                
                return jsonify({
                    "total_records": total_count,
                    "recent_hour_records": recent_count,
                    "avg_rssi": round(stats['avg_rssi'] or 0, 1),
                    "avg_rx_kb": round((stats['avg_rx'] or 0) / 1024, 2),
                    "avg_tx_kb": round((stats['avg_tx'] or 0) / 1024, 2),
                    "operator_count": stats['operator_count'] or 0
                })

        @self.app.route('/api/drone_control/<action>', methods=['POST'])
        def drone_control(action):
            """드론 LTE 제어 (시작/중지)"""
            try:
                drone_address = request.json.get('drone_address', '192.168.1.100:8897')  # LTE 포트
                
                # 포트가 포함되지 않은 경우 LTE 기본 포트 추가
                if ':' not in drone_address:
                    drone_address += ':8897'
                
                if action == 'start':
                    # Try English collector endpoint first (without /api prefix)
                    try:
                        response = requests.post(f"http://{drone_address}/start", timeout=10)
                    except requests.RequestException:
                        # Fallback to Korean collector endpoint (with /api prefix)
                        try:
                            response = requests.post(f"http://{drone_address}/api/start", timeout=10)
                        except requests.RequestException as e:
                            return jsonify({"error": f"드론 LTE 연결 실패: {str(e)}"}), 500
                elif action == 'stop':
                    # Try English collector endpoint first (without /api prefix)
                    try:
                        response = requests.post(f"http://{drone_address}/stop", timeout=10)
                    except requests.RequestException:
                        # Fallback to Korean collector endpoint (with /api prefix)
                        try:
                            response = requests.post(f"http://{drone_address}/api/stop", timeout=10)
                        except requests.RequestException as e:
                            return jsonify({"error": f"드론 LTE 연결 실패: {str(e)}"}), 500
                else:
                    return jsonify({"error": "잘못된 액션입니다"}), 400
                
                # Check response and handle JSON parsing
                try:
                    if response.status_code == 200:
                        result = response.json()
                        return jsonify({"success": result.get('success', True), "message": result.get('message', 'Success')})
                    else:
                        # Try to parse error response
                        try:
                            error_data = response.json()
                            return jsonify({"error": error_data.get('error', 'Unknown error')}), response.status_code
                        except:
                            return jsonify({"error": f"HTTP {response.status_code}: {response.text}"}), response.status_code
                except json.JSONDecodeError:
                    return jsonify({"error": f"Invalid JSON response: {response.text}"}), 500
                    
            except requests.RequestException as e:
                return jsonify({"error": f"드론 LTE 연결 실패: {str(e)}"}), 500

        @self.app.route('/api/drone_status')
        def drone_status():
            """드론 LTE 상태 조회"""
            try:
                drone_address = request.args.get('drone_address', '192.168.1.100:8897')
                
                # 포트가 포함되지 않은 경우 LTE 기본 포트 추가
                if ':' not in drone_address:
                    drone_address += ':8897'
                
                # Try English collector endpoint first (without /api prefix)
                try:
                    response = requests.get(f"http://{drone_address}/status", timeout=5)
                except requests.RequestException:
                    # Fallback to Korean collector endpoint (with /api prefix)
                    response = requests.get(f"http://{drone_address}/api/status", timeout=5)
                
                if response.status_code == 200:
                    return jsonify(response.json())
                else:
                    return jsonify({"error": "LTE 상태 조회 실패"}), response.status_code
                    
            except requests.RequestException as e:
                return jsonify({"error": f"드론 LTE 연결 실패: {str(e)}"}), 500

        @self.app.route('/api/live_data')
        def get_live_data():
            """드론에서 실시간 LTE 데이터 가져오기"""
            try:
                drone_address = request.args.get('drone_address', 'localhost:8897')
                
                # 포트가 포함되지 않은 경우 LTE 기본 포트 추가
                if ':' not in drone_address:
                    drone_address += ':8897'
                
                response = requests.get(f"http://{drone_address}/api/current_data", timeout=5)
                
                if response.status_code == 200:
                    return jsonify(response.json())
                else:
                    return jsonify({"error": "실시간 LTE 데이터 조회 실패"}), response.status_code
                    
            except requests.RequestException as e:
                return jsonify({"error": f"드론 LTE 연결 실패: {str(e)}"}), 500

        @self.app.route('/')
        def dashboard():
            """LTE 지상국 대시보드"""
            return render_template_string(LTE_DASHBOARD_HTML)

    def save_to_database(self, data_list: List[Dict]):
        """데이터베이스에 LTE 데이터 저장"""
        with sqlite3.connect(self.db_file) as conn:
            for data in data_list:
                conn.execute("""
                    INSERT INTO lte_drone_data (
                        timestamp, module_id, connection_state, uptime,
                        signal_quality_rssi, signal_quality_ber, network_operator, network_mode,
                        network_reg_status, eps_reg_status, cell_id, lac,
                        rx_bytes, tx_bytes, ip_address, frequency_band, earfcn,
                        latitude, longitude, altitude
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('timestamp'),
                    data.get('module_id'),
                    data.get('connection_state'),
                    data.get('uptime'),
                    data.get('signal_quality_rssi'),
                    data.get('signal_quality_ber'),
                    data.get('network_operator'),
                    data.get('network_mode'),
                    data.get('network_reg_status'),
                    data.get('eps_reg_status'),
                    data.get('cell_id'),
                    data.get('lac'),
                    data.get('rx_bytes'),
                    data.get('tx_bytes'),
                    data.get('ip_address'),
                    data.get('frequency_band'),
                    data.get('earfcn'),
                    data.get('latitude'),
                    data.get('longitude'),
                    data.get('altitude')
                ))

    def run(self):
        """LTE 지상국 서버 실행"""
        self.logger.info(f"LTE 지상국 수신기 시작: http://0.0.0.0:{self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)


# LTE 대시보드 HTML 템플릿
LTE_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LTE Ground Station Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #3e0f1c 0%, #512851 100%);
            color: #f0f4f8; line-height: 1.6; min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 4px; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .header { text-align: center; margin-bottom: 6px; flex-shrink: 0; }
        .header h1 { 
            font-size: 1.2rem; color: #ffffff; margin-bottom: 2px; 
            font-weight: 700; letter-spacing: -0.02em;
        }
        .header p { color: #8fa3b8; font-size: 0.7rem; font-weight: 400; }
        .header .lte-badge {
            display: inline-block;
            background: linear-gradient(45deg, #e91e63, #9c27b0);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.6rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 8px;
        }
        .stats-grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); 
            gap: 6px; margin-bottom: 6px; 
        }
        .stat-card {
            background: rgba(233, 30, 99, 0.15); 
            border: 1px solid rgba(233, 30, 99, 0.25);
            border-radius: 6px; padding: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
        }
        .stat-card:hover { 
            border-color: rgba(233, 30, 99, 0.4); 
            transform: translateY(-2px); 
            box-shadow: 0 8px 24px rgba(233, 30, 99, 0.2);
        }
        .stat-title { 
            font-size: 0.75rem; color: #e8a3b8; margin-bottom: 4px; 
            font-weight: 500; letter-spacing: 0.025em; text-transform: uppercase;
        }
        .stat-value { font-size: 1.1rem; font-weight: 700; color: #ffffff; line-height: 1; }
        .stat-unit { font-size: 0.75rem; color: #e8a3b8; margin-left: 4px; }
        .data-section { 
            background: rgba(233, 30, 99, 0.08); 
            border: 1px solid rgba(233, 30, 99, 0.15);
            border-radius: 6px; padding: 8px; margin-bottom: 4px; 
            backdrop-filter: blur(10px); flex-shrink: 0;
        }
        .section-title {
            font-size: 0.85rem; font-weight: 600; color: #ffffff; 
            margin-bottom: 6px; letter-spacing: -0.01em;
        }
        .data-table { width: 100%; border-collapse: collapse; font-size: 0.7rem; }
        .data-table th, .data-table td { 
            text-align: left; padding: 3px 6px; border-bottom: 1px solid rgba(233, 30, 99, 0.1); 
        }
        .data-table th { 
            background: rgba(233, 30, 99, 0.1); color: #ffffff; font-weight: 600; 
            font-size: 0.65rem; letter-spacing: 0.025em; text-transform: uppercase;
        }
        .data-table tr:hover { background: rgba(233, 30, 99, 0.08); }
        .status { 
            display: inline-block; padding: 3px 8px; border-radius: 6px; 
            font-size: 0.65rem; font-weight: 600; letter-spacing: 0.025em;
            text-transform: uppercase;
        }
        .status.connected { background: #4caf50; color: #ffffff; }
        .status.registered { background: #2196f3; color: #ffffff; }
        .status.searching { background: #ff9800; color: #ffffff; }
        .status.disconnected { background: #f44336; color: #ffffff; }
        .update-time { text-align: center; color: #e8a3b8; margin-top: 12px; font-size: 0.75rem; }
        .loading { text-align: center; padding: 24px; color: #e8a3b8; font-size: 0.875rem; }
        
        /* 제어 패널 스타일 */
        .control-panel { display: flex; gap: 6px; margin-bottom: 6px; align-items: center; flex-wrap: wrap; }
        .control-panel input { 
            padding: 6px 10px; border: 1px solid rgba(233, 30, 99, 0.3); 
            background: rgba(233, 30, 99, 0.1); color: #ffffff; 
            border-radius: 6px; flex: 1; min-width: 200px;
            font-size: 0.75rem; backdrop-filter: blur(10px);
        }
        .control-panel input::placeholder { color: #e8a3b8; }
        .control-panel input:focus { 
            outline: none; border-color: rgba(233, 30, 99, 0.5); 
            box-shadow: 0 0 0 2px rgba(233, 30, 99, 0.1);
        }
        .control-btn {
            padding: 6px 10px; border: none; border-radius: 6px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; font-size: 0.65rem;
            letter-spacing: 0.025em; text-transform: uppercase;
        }
        .start-btn { background: #4caf50; color: #ffffff; }
        .start-btn:hover { background: #45a049; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(76, 175, 80, 0.3); }
        .stop-btn { background: #f44336; color: #ffffff; }
        .stop-btn:hover { background: #da190b; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(244, 67, 54, 0.3); }
        .status-btn { background: #e91e63; color: #ffffff; }
        .status-btn:hover { background: #c2185b; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(233, 30, 99, 0.3); }
        .control-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .drone-status { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
            gap: 6px; padding: 6px; background: rgba(233, 30, 99, 0.08); 
            border-radius: 6px; border: 1px solid rgba(233, 30, 99, 0.15);
        }
        .status-item { color: #e8a3b8; font-size: 0.75rem; font-weight: 500; }
        .status-item span { color: #ffffff; font-weight: 600; }
        
        /* 테이블 스크롤 */
        .table-container {
            height: 200px;
            overflow-y: auto;
            border-radius: 6px;
            background: rgba(233, 30, 99, 0.05);
        }
        .table-container::-webkit-scrollbar {
            width: 6px;
        }
        .table-container::-webkit-scrollbar-track {
            background: rgba(233, 30, 99, 0.1);
            border-radius: 3px;
        }
        .table-container::-webkit-scrollbar-thumb {
            background: rgba(233, 30, 99, 0.3);
            border-radius: 3px;
        }
        .table-container::-webkit-scrollbar-thumb:hover {
            background: rgba(233, 30, 99, 0.5);
        }
        
        /* LTE 특화 스타일 */
        .lte-indicator {
            background: linear-gradient(45deg, #e91e63, #9c27b0);
            background-size: 200% 200%;
            animation: gradientShift 2s ease-in-out infinite alternate;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            100% { background-position: 100% 50%; }
        }
        .signal-bar {
            display: inline-block;
            width: 3px;
            height: 12px;
            background: #e91e63;
            margin-right: 2px;
            border-radius: 1px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LTE Ground Station Monitor <span class="lte-badge lte-indicator">LTE</span></h1>
            <p>Real-time LTE communication quality monitoring and data collection</p>
        </div>

        <div class="data-section">
            <h2 class="section-title">🔗 Drone LTE Control</h2>
            <div class="control-panel">
                <input type="text" id="droneAddress" placeholder="Drone LTE address (example: 192.168.1.100:8897)" value="localhost:8897">
                <button id="startBtn" class="control-btn start-btn">Start LTE</button>
                <button id="stopBtn" class="control-btn stop-btn">Stop LTE</button>
                <button id="statusBtn" class="control-btn status-btn">Check Status</button>
            </div>
            <div id="droneStatus" class="drone-status">
                <div class="status-item">LTE State: <span id="droneState">-</span></div>
                <div class="status-item">Current File: <span id="droneFile">-</span></div>
                <div class="status-item">Collection Time: <span id="droneDuration">-</span></div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">📊 Total LTE Records</div>
                <div class="stat-value" id="totalRecords">-</div>
                <div class="stat-unit">records</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">🕐 Last Hour</div>
                <div class="stat-value" id="recentRecords">-</div>
                <div class="stat-unit">records</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">📶 Average RSSI</div>
                <div class="stat-value" id="avgRssi">-</div>
                <div class="stat-unit">dBm</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">🌐 Network Operators</div>
                <div class="stat-value" id="operatorCount">-</div>
                <div class="stat-unit">operators</div>
            </div>
        </div>

        <!-- 실시간 LTE 데이터 섹션 -->
        <div class="data-section">
            <h2 class="section-title">📡 Live LTE Module Data</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Signal Quality (RSSI)</div>
                    <div class="stat-value" id="liveRssi">0</div>
                    <div class="stat-unit">dBm</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Bit Error Rate</div>
                    <div class="stat-value" id="liveBer">0</div>
                    <div class="stat-unit">%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">RX Data</div>
                    <div class="stat-value" id="liveRx">0.0</div>
                    <div class="stat-unit">KB</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">TX Data</div>
                    <div class="stat-value" id="liveTx">0.0</div>
                    <div class="stat-unit">KB</div>
                </div>
            </div>
            <div class="update-time">
                Last Update: <span id="liveTimestamp">-</span>
            </div>
        </div>

        <div class="data-section" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
            <h2 class="section-title">📋 Recent LTE Data</h2>
            <div class="table-container" style="flex: 1;">
                <div id="dataContainer" class="loading">Loading LTE data...</div>
            </div>
        </div>

        <div class="update-time">
            Last Update: <span id="lastUpdate">-</span>
        </div>
    </div>

    <script>
        function formatTimestamp(timestamp) {
            return new Date(timestamp).toLocaleString('ko-KR');
        }

        function getConnectionStatusClass(state) {
            if (state === 'CONNECTED') return 'connected';
            if (state === 'REGISTERED') return 'registered';
            if (state === 'SEARCHING') return 'searching';
            return 'disconnected';
        }

        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('totalRecords').textContent = stats.total_records.toLocaleString();
                document.getElementById('recentRecords').textContent = stats.recent_hour_records.toLocaleString();
                document.getElementById('avgRssi').textContent = stats.avg_rssi;
                document.getElementById('operatorCount').textContent = stats.operator_count;
            } catch (error) {
                console.error('LTE Statistics update error:', error);
            }
        }

        async function updateData() {
            try {
                // 실시간 LTE 데이터로 테이블 표시
                const droneAddress = document.getElementById('droneAddress').value;
                const response = await fetch(`/api/live_data?drone_address=${encodeURIComponent(droneAddress)}`);
                const rawData = await response.json();
                
                if (rawData.error) {
                    document.getElementById('dataContainer').innerHTML = '<p class="loading">No LTE data received.</p>';
                    return;
                }
                
                // 실시간 데이터를 배열 형태로 변환
                const data = [rawData];

                let html = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>State</th>
                                <th>RSSI</th>
                                <th>Operator</th>
                                <th>Mode</th>
                                <th>IP Address</th>
                                <th>RX/TX (KB)</th>
                                <th>Band</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                data.reverse().forEach(item => {
                    html += `
                        <tr>
                            <td>${formatTimestamp(item.timestamp)}</td>
                            <td><span class="status ${getConnectionStatusClass(item.connection_state)}">${item.connection_state}</span></td>
                            <td>${item.signal_quality_rssi || 0} dBm</td>
                            <td>${item.network_operator || '-'}</td>
                            <td>${item.network_mode || '-'}</td>
                            <td>${item.ip_address || '-'}</td>
                            <td>${((item.rx_bytes || 0) / 1024).toFixed(1)} / ${((item.tx_bytes || 0) / 1024).toFixed(1)}</td>
                            <td>${item.frequency_band || '-'}</td>
                        </tr>
                    `;
                });

                html += '</tbody></table>';
                document.getElementById('dataContainer').innerHTML = html;
                document.getElementById('lastUpdate').textContent = new Date().toLocaleString('ko-KR');

            } catch (error) {
                console.error('LTE Data update error:', error);
                document.getElementById('dataContainer').innerHTML = '<p class="loading">LTE data loading error</p>';
            }
        }

        // 드론 LTE 제어 기능
        async function controlDrone(action) {
            const droneAddress = document.getElementById('droneAddress').value;
            const buttons = document.querySelectorAll('.control-btn');
            
            // 버튼 비활성화
            buttons.forEach(btn => btn.disabled = true);
            
            try {
                const response = await fetch(`/api/drone_control/${action}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({drone_address: droneAddress})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`LTE Success: ${result.message}`);
                    updateDroneStatus();  // 상태 즉시 업데이트
                } else {
                    alert(`LTE Error: ${result.error}`);
                }
            } catch (error) {
                alert(`LTE Connection error: ${error.message}`);
            } finally {
                // 버튼 활성화
                buttons.forEach(btn => btn.disabled = false);
            }
        }

        async function updateDroneStatus() {
            const droneAddress = document.getElementById('droneAddress').value;
            
            try {
                const response = await fetch(`/api/drone_status?drone_address=${encodeURIComponent(droneAddress)}`);
                const status = await response.json();
                
                if (!status.error) {
                    document.getElementById('droneState').textContent = status.state || '-';
                    document.getElementById('droneFile').textContent = status.current_file || '-';
                    document.getElementById('droneDuration').textContent = status.duration || '-';
                } else {
                    document.getElementById('droneState').textContent = 'ERROR';
                    document.getElementById('droneFile').textContent = '-';
                    document.getElementById('droneDuration').textContent = '-';
                }
            } catch (error) {
                document.getElementById('droneState').textContent = 'OFFLINE';
                document.getElementById('droneFile').textContent = '-';
                document.getElementById('droneDuration').textContent = '-';
            }
        }

        // 실시간 LTE 데이터 업데이트
        async function updateLiveData() {
            const droneAddress = document.getElementById('droneAddress').value;
            
            try {
                const response = await fetch(`/api/live_data?drone_address=${encodeURIComponent(droneAddress)}`);
                const data = await response.json();
                
                if (data.error) {
                    // 실시간 데이터를 가져올 수 없으면 스탯 카드를 0으로 표시
                    document.getElementById('liveRssi').textContent = '0';
                    document.getElementById('liveBer').textContent = '0';
                    document.getElementById('liveRx').textContent = '0.0';
                    document.getElementById('liveTx').textContent = '0.0';
                    return;
                }
                
                // 실시간 LTE 데이터로 스탯 카드 업데이트
                document.getElementById('liveRssi').textContent = data.signal_quality_rssi || 0;
                document.getElementById('liveBer').textContent = data.signal_quality_ber || 0;
                document.getElementById('liveRx').textContent = ((data.rx_bytes || 0) / 1024).toFixed(1);
                document.getElementById('liveTx').textContent = ((data.tx_bytes || 0) / 1024).toFixed(1);
                
                // 상단 통계도 실시간 데이터로 업데이트
                document.getElementById('avgRssi').textContent = data.signal_quality_rssi || 0;
                document.getElementById('totalRecords').textContent = 'Live';
                document.getElementById('recentRecords').textContent = 'LTE';
                document.getElementById('operatorCount').textContent = data.network_operator ? '1' : '0';
                
                // 마지막 업데이트 시간 표시
                document.getElementById('liveTimestamp').textContent = formatTimestamp(data.timestamp);
                
            } catch (error) {
                console.error('Live LTE data update error:', error);
            }
        }

        // 이벤트 리스너
        document.getElementById('startBtn').addEventListener('click', () => controlDrone('start'));
        document.getElementById('stopBtn').addEventListener('click', () => controlDrone('stop'));
        document.getElementById('statusBtn').addEventListener('click', updateDroneStatus);

        // 자동 업데이트
        updateStats();
        updateData();
        updateDroneStatus();  // 드론 LTE 상태 초기 로드
        updateLiveData();     // 실시간 LTE 데이터 초기 로드
        setInterval(updateStats, 60000);     // 1분마다 통계 업데이트
        setInterval(updateData, 3000);       // 3초마다 데이터 업데이트 (LTE는 조금 느림)
        setInterval(updateDroneStatus, 15000); // 15초마다 드론 상태 업데이트
        setInterval(updateLiveData, 2000);   // 2초마다 실시간 LTE 데이터 업데이트
    </script>
</body>
</html>
"""

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='LTE 지상국 데이터 수신기')
    parser.add_argument('--port', type=int, default=8079, help='수신 포트')
    parser.add_argument('--data-dir', default='/opt/lte-ground-station-data', help='데이터 저장 디렉토리')
    
    args = parser.parse_args()
    
    receiver = LTEGroundStationReceiver(port=args.port, data_dir=args.data_dir)
    receiver.run()

if __name__ == "__main__":
    main()