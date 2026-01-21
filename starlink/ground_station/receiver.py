#!/usr/bin/env python3
"""
지상국 데이터 수신 및 모니터링 시스템
- 드론에서 전송된 압축 데이터 수신
- 실시간 대시보드 제공
- 데이터 저장 및 분석
"""

import json
import gzip
import time
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
import logging
import os
from typing import Dict, List
from collections import deque
import sqlite3
import requests
from urllib.parse import urlparse

class GroundStationReceiver:
    """지상국 데이터 수신기"""
    
    def __init__(self, port=8080, data_dir="/opt/ground-station-data"):
        self.port = port
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)

        # Flask 앱
        self.app = Flask(__name__)
        self.setup_routes()
        
        # 최소화된 모니터링용 실시간 데이터 버퍼 (최근 50개만)
        self.realtime_data = deque(maxlen=50)
        
        # 데이터베이스 설정
        self.db_file = self.data_dir / "drone_data.db"
        self.setup_database()
        
        # 로깅 설정
        log_level = logging.DEBUG if os.getenv("STARLINK_GS_DEBUG") == "1" else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / 'ground_station.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Ground station logging level: %s", logging.getLevelName(log_level))

    def setup_database(self):
        """SQLite 데이터베이스 초기화"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drone_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    terminal_id TEXT,
                    state TEXT,
                    uptime INTEGER,
                    downlink_throughput_bps REAL,
                    uplink_throughput_bps REAL,
                    ping_drop_rate REAL,
                    ping_latency_ms REAL,
                    snr REAL,
                    seconds_to_first_nonempty_slot INTEGER,
                    azimuth REAL,
                    elevation REAL,
                    pop_ping_drop_rate REAL,
                    pop_ping_latency_ms REAL,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    received_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON drone_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_received_at ON drone_data(received_at)")

    def setup_routes(self):
        """Flask 라우트 설정"""

        def normalize_target(raw_value: str, default_port: int) -> str:
            """Normalize target address to host:port."""
            if not raw_value:
                raise ValueError("target address is empty")
            value = raw_value.strip()
            if value.startswith("http://") or value.startswith("https://"):
                parsed = urlparse(value)
                if not parsed.hostname:
                    raise ValueError("invalid target address")
                port = parsed.port or default_port
                return f"{parsed.hostname}:{port}"
            if "/" in value:
                value = value.split("/", 1)[0]
            if ":" not in value:
                value = f"{value}:{default_port}"
            return value

        @self.app.before_request
        def log_request():
            payload = request.get_json(silent=True)
            payload_keys = list(payload.keys()) if isinstance(payload, dict) else None
            self.logger.info(
                "REQ %s %s args=%s json_keys=%s",
                request.method,
                request.path,
                dict(request.args),
                payload_keys,
            )

        @self.app.after_request
        def log_response(response):
            self.logger.info("RES %s %s status=%s", request.method, request.path, response.status_code)
            return response
        
        @self.app.route('/upload_status', methods=['POST'])
        def upload_status():
            """드론 상태 정보 수신"""
            try:
                # 압축 해제
                if request.headers.get('Content-Encoding') == 'gzip':
                    data = gzip.decompress(request.data)
                    status_data = json.loads(data.decode('utf-8'))
                else:
                    status_data = request.get_json()
                
                # 드론 상태 정보 처리
                if 'recent_data' in status_data:
                    # 최근 데이터가 있으면 데이터베이스에 저장
                    self.save_to_database(status_data['recent_data'])
                    # 실시간 버퍼 업데이트
                    for item in status_data['recent_data']:
                        self.realtime_data.append(item)
                
                self.logger.info(f"Drone status received: {status_data.get('state', 'UNKNOWN')}")
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"Status ingest error: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/upload_data', methods=['POST'])
        def upload_data():
            """드론에서 전송된 데이터 수신"""
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
                
                self.logger.info(f"Data received: {len(json_data)} records")
                
                return jsonify({"status": "success", "received_count": len(json_data)})
                
            except Exception as e:
                self.logger.error(f"Data ingest error: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/api/latest_data')
        def get_latest_data():
            """최신 데이터 반환 (최소화된 모니터링용)"""
            if self.realtime_data:
                return jsonify(list(self.realtime_data)[-5:])  # 최근 5개만
            return jsonify([])

        @self.app.route('/api/stats')
        def get_stats():
            """통계 정보 반환"""
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                
                # 총 데이터 수
                total_count = conn.execute("SELECT COUNT(*) as count FROM drone_data").fetchone()['count']
                
                # 최근 1시간 데이터 수
                recent_count = conn.execute("""
                    SELECT COUNT(*) as count FROM drone_data 
                    WHERE received_at > datetime('now', '-1 hour')
                """).fetchone()['count']
                
                # 평균 성능 지표 (최근 1시간)
                stats = conn.execute("""
                    SELECT 
                        AVG(downlink_throughput_bps) as avg_downlink,
                        AVG(uplink_throughput_bps) as avg_uplink,
                        AVG(ping_latency_ms) as avg_latency,
                        AVG(snr) as avg_snr
                    FROM drone_data 
                    WHERE received_at > datetime('now', '-1 hour')
                """).fetchone()
                
                return jsonify({
                    "total_records": total_count,
                    "recent_hour_records": recent_count,
                    "avg_downlink_mbps": round((stats['avg_downlink'] or 0) / 1024 / 1024, 2),
                    "avg_uplink_mbps": round((stats['avg_uplink'] or 0) / 1024 / 1024, 2),
                    "avg_latency_ms": round(stats['avg_latency'] or 0, 2),
                    "avg_snr": round(stats['avg_snr'] or 0, 2)
                })

        @self.app.route('/api/drone_control/<action>', methods=['POST'])
        def drone_control(action):
            """드론 제어 (시작/중지)"""
            try:
                payload = request.get_json(silent=True) or {}
                drone_address = normalize_target(
                    payload.get('drone_address', '192.168.1.100:8899'),
                    8899,
                )
                
                if action == 'start':
                    response = requests.post(f"http://{drone_address}/api/start", timeout=10)
                elif action == 'stop':
                    response = requests.post(f"http://{drone_address}/api/stop", timeout=10)
                else:
                    return jsonify({"error": "Invalid action"}), 400
                
                if response.status_code == 200:
                    return jsonify({"success": True, "message": response.json().get('message', 'Success')})
                else:
                    return jsonify({"error": response.json().get('error', 'Unknown error')}), response.status_code
                    
            except ValueError as e:
                return jsonify({"error": f"Invalid address: {str(e)}"}), 400
            except requests.RequestException as e:
                return jsonify({"error": f"Collector connection failed: {str(e)}"}), 500

        @self.app.route('/api/drone_status')
        def drone_status():
            """드론 상태 조회"""
            try:
                drone_address = normalize_target(
                    request.args.get('drone_address', '192.168.1.100:8899'),
                    8899,
                )
                
                response = requests.get(f"http://{drone_address}/api/status", timeout=5)
                if response.status_code != 200:
                    return jsonify({"error": "Status request failed", "detail": response.text}), response.status_code

                try:
                    return jsonify(response.json())
                except ValueError as e:
                    self.logger.exception(f"Status JSON parse failed: {e}")
                    return jsonify({"error": "Status response parse failed", "detail": response.text}), 502

            except ValueError as e:
                return jsonify({"error": f"Invalid address: {str(e)}"}), 400
            except requests.RequestException as e:
                self.logger.exception(f"Collector connection failed: {e}")
                return jsonify({"error": f"Collector connection failed: {str(e)}"}), 500
            except Exception as e:
                self.logger.exception(f"Collector status request error: {e}")
                return jsonify({"error": "Collector status request error", "detail": str(e)}), 500

        @self.app.route('/api/live_data')
        def get_live_data():
            """드론에서 실시간 데이터 가져오기"""
            try:
                drone_address = normalize_target(
                    request.args.get('drone_address', 'localhost:8899'),
                    8899,
                )
                
                response = requests.get(f"http://{drone_address}/api/current_data", timeout=5)
                if response.status_code != 200:
                    return jsonify({"error": "Live data request failed", "detail": response.text}), response.status_code

                try:
                    return jsonify(response.json())
                except ValueError as e:
                    self.logger.exception(f"Live data JSON parse failed: {e}")
                    return jsonify({"error": "Live data response parse failed", "detail": response.text}), 502

            except ValueError as e:
                return jsonify({"error": f"Invalid address: {str(e)}"}), 400
            except requests.RequestException as e:
                self.logger.exception(f"Collector connection failed: {e}")
                return jsonify({"error": f"Collector connection failed: {str(e)}"}), 500
            except Exception as e:
                self.logger.exception(f"Live data request error: {e}")
                return jsonify({"error": "Live data request error", "detail": str(e)}), 500

        @self.app.route('/')
        def dashboard():
            """지상국 대시보드"""
            return render_template_string(DASHBOARD_HTML)

    def save_to_database(self, data_list: List[Dict]):
        """데이터베이스에 저장"""
        with sqlite3.connect(self.db_file) as conn:
            for data in data_list:
                try:
                    conn.execute("""
                        INSERT INTO drone_data (
                            timestamp, terminal_id, state, uptime,
                            downlink_throughput_bps, uplink_throughput_bps,
                            ping_drop_rate, ping_latency_ms, snr,
                            seconds_to_first_nonempty_slot, azimuth, elevation,
                            pop_ping_drop_rate, pop_ping_latency_ms,
                            latitude, longitude, altitude
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.get('timestamp'),
                        data.get('terminal_id'),
                        data.get('state'),
                        data.get('uptime'),
                        data.get('downlink_throughput_bps'),
                        data.get('uplink_throughput_bps'),
                        data.get('ping_drop_rate'),
                        data.get('ping_latency_ms'),
                        data.get('snr'),
                        data.get('seconds_to_first_nonempty_slot'),
                        data.get('azimuth'),
                        data.get('elevation'),
                        data.get('pop_ping_drop_rate'),
                        data.get('pop_ping_latency_ms'),
                        data.get('latitude'),
                        data.get('longitude'),
                        data.get('altitude')
                    ))
                except Exception as e:
                    self.logger.error(f"DB save error: {e}")
                    try:
                        conn.execute("""
                            INSERT INTO drone_data (
                                timestamp, terminal_id, state, uptime,
                                downlink_throughput_bps, uplink_throughput_bps,
                                ping_drop_rate, ping_latency_ms, snr,
                                seconds_to_first_nonempty_slot, azimuth, elevation,
                                pop_ping_drop_rate, pop_ping_latency_ms,
                                latitude, longitude, altitude
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data.get('timestamp'),
                            data.get('terminal_id'),
                            data.get('state'),
                            data.get('uptime'),
                            data.get('downlink_throughput_bps'),
                            data.get('uplink_throughput_bps'),
                            data.get('ping_drop_rate'),
                            data.get('ping_latency_ms'),
                            data.get('snr'),
                            data.get('seconds_to_first_nonempty_slot'),
                            data.get('azimuth'),
                            data.get('elevation'),
                            data.get('pop_ping_drop_rate'),
                            data.get('pop_ping_latency_ms'),
                            data.get('latitude'),
                            data.get('longitude'),
                            data.get('altitude')
                        ))
                    except Exception as retry_error:
                        self.logger.error(f"DB save retry failed: {retry_error}")

    def run(self):
        """지상국 서버 실행"""
        self.logger.info(f"Ground station started: http://0.0.0.0:{self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)


# 대시보드 HTML 템플릿
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Starlink Ground Station Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f1c3e 0%, #1a2851 100%);
            color: #f0f4f8; line-height: 1.6; min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 4px; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .header { text-align: center; margin-bottom: 6px; flex-shrink: 0; }
        .header h1 { 
            font-size: 1.2rem; color: #ffffff; margin-bottom: 2px; 
            font-weight: 700; letter-spacing: -0.02em;
        }
        .header p { color: #8fa3b8; font-size: 0.7rem; font-weight: 400; }
        .stats-grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); 
            gap: 6px; margin-bottom: 6px; 
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1); 
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px; padding: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
        }
        .stat-card:hover { 
            border-color: rgba(255, 255, 255, 0.3); 
            transform: translateY(-2px); 
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }
        .stat-title { 
            font-size: 0.75rem; color: #8fa3b8; margin-bottom: 4px; 
            font-weight: 500; letter-spacing: 0.025em; text-transform: uppercase;
        }
        .stat-value { font-size: 1.1rem; font-weight: 700; color: #ffffff; line-height: 1; }
        .stat-unit { font-size: 0.75rem; color: #8fa3b8; margin-left: 4px; }
        .data-section { 
            background: rgba(255, 255, 255, 0.05); 
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px; padding: 8px; margin-bottom: 4px; 
            backdrop-filter: blur(10px); flex-shrink: 0;
        }
        .section-title {
            font-size: 0.85rem; font-weight: 600; color: #ffffff; 
            margin-bottom: 6px; letter-spacing: -0.01em;
        }
        .data-table { width: 100%; border-collapse: collapse; font-size: 0.7rem; }
        .data-table th, .data-table td { 
            text-align: left; padding: 3px 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); 
        }
        .data-table th { 
            background: rgba(255, 255, 255, 0.05); color: #ffffff; font-weight: 600; 
            font-size: 0.65rem; letter-spacing: 0.025em; text-transform: uppercase;
        }
        .data-table tr:hover { background: rgba(255, 255, 255, 0.05); }
        .status { 
            display: inline-block; padding: 3px 8px; border-radius: 6px; 
            font-size: 0.65rem; font-weight: 600; letter-spacing: 0.025em;
            text-transform: uppercase;
        }
        .status.connected { background: #10b981; color: #ffffff; }
        .status.connecting { background: #f59e0b; color: #ffffff; }
        .status.disconnected { background: #ef4444; color: #ffffff; }
        .update-time { text-align: center; color: #8fa3b8; margin-top: 12px; font-size: 0.75rem; }
        .loading { text-align: center; padding: 24px; color: #8fa3b8; font-size: 0.875rem; }
        
        /* 제어 패널 스타일 */
        .control-panel { display: flex; gap: 6px; margin-bottom: 6px; align-items: center; flex-wrap: wrap; }
        .control-panel input { 
            padding: 6px 10px; border: 1px solid rgba(255, 255, 255, 0.2); 
            background: rgba(255, 255, 255, 0.1); color: #ffffff; 
            border-radius: 6px; flex: 1; min-width: 200px;
            font-size: 0.75rem; backdrop-filter: blur(10px);
        }
        .control-panel input::placeholder { color: #8fa3b8; }
        .control-panel input:focus { 
            outline: none; border-color: rgba(255, 255, 255, 0.4); 
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
        }
        .control-btn {
            padding: 6px 10px; border: none; border-radius: 6px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; font-size: 0.65rem;
            letter-spacing: 0.025em; text-transform: uppercase;
        }
        .start-btn { background: #10b981; color: #ffffff; }
        .start-btn:hover { background: #059669; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3); }
        .stop-btn { background: #ef4444; color: #ffffff; }
        .stop-btn:hover { background: #dc2626; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(239, 68, 68, 0.3); }
        .status-btn { background: #3b82f6; color: #ffffff; }
        .status-btn:hover { background: #2563eb; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3); }
        .control-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .drone-status { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
            gap: 6px; padding: 6px; background: rgba(255, 255, 255, 0.05); 
            border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .status-item { color: #8fa3b8; font-size: 0.75rem; font-weight: 500; }
        .status-item span { color: #ffffff; font-weight: 600; }
        
        /* 테이블 스크롤 */
        .table-container {
            height: 200px;
            overflow-y: auto;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.02);
        }
        .table-container::-webkit-scrollbar {
            width: 6px;
        }
        .table-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }
        .table-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 3px;
        }
        .table-container::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Starlink Ground Station Monitor</h1>
            <p>Real-time monitoring and data collection management</p>
        </div>

        <div class="data-section">
            <h2 class="section-title">Drone Control</h2>
            <div class="control-panel">
                <input type="text" id="droneAddress" placeholder="Drone address (example: 192.168.1.100:8899)" value="localhost:8899">
                <button id="startBtn" class="control-btn start-btn">Start Collection</button>
                <button id="stopBtn" class="control-btn stop-btn">Stop Collection</button>
                <button id="statusBtn" class="control-btn status-btn">Check Status</button>
            </div>
            <div id="droneStatus" class="drone-status">
                <div class="status-item">Status: <span id="droneState">-</span></div>
                <div class="status-item">Current File: <span id="droneFile">-</span></div>
                <div class="status-item">Collection Time: <span id="droneDuration">-</span></div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">Total Received Data</div>
                <div class="stat-value" id="totalRecords">-</div>
                <div class="stat-unit">records</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Last Hour</div>
                <div class="stat-value" id="recentRecords">-</div>
                <div class="stat-unit">records</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Average Download Speed</div>
                <div class="stat-value" id="avgDownlink">-</div>
                <div class="stat-unit">Mbps</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Average Latency</div>
                <div class="stat-value" id="avgLatency">-</div>
                <div class="stat-unit">ms</div>
            </div>
        </div>

        <!-- 실시간 데이터 섹션 -->
        <div class="data-section">
            <h2 class="section-title">Live Starlink Data</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Real-time Download</div>
                    <div class="stat-value" id="liveDownlink">0.00</div>
                    <div class="stat-unit">Mbps</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Real-time Upload</div>
                    <div class="stat-value" id="liveUplink">0.00</div>
                    <div class="stat-unit">Mbps</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Real-time Latency</div>
                    <div class="stat-value" id="liveLatency">0.0</div>
                    <div class="stat-unit">ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Real-time SNR</div>
                    <div class="stat-value" id="liveSNR">0.0</div>
                    <div class="stat-unit">dB</div>
                </div>
            </div>
            <div class="update-time">
                Last Update: <span id="liveTimestamp">-</span>
            </div>
        </div>

        <div class="data-section" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
            <h2 class="section-title">All Fields</h2>
            <div class="table-container" style="flex: 1;">
                <div id="allFieldsContainer" class="loading">Waiting for data...</div>
            </div>
        </div>

        <div class="data-section" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
            <h2 class="section-title">Recent Data</h2>
            <div class="table-container" style="flex: 1;">
                <div id="dataContainer" class="loading">Loading data...</div>
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

        function getStatusClass(state) {
            const normalized = (state || '').toLowerCase();
            if (normalized.includes('connected') || normalized.includes('running')) return 'connected';
            if (normalized.includes('start') || normalized.includes('search')) return 'connecting';
            if (normalized.includes('idle') || normalized.includes('stop')) return 'disconnected';
            if (normalized.includes('error')) return 'disconnected';
            return 'disconnected';
        }

        function flattenObject(obj, prefix = '') {
            const rows = [];
            if (obj === null || obj === undefined) return rows;
            const isPlainObject = (value) => Object.prototype.toString.call(value) === '[object Object]';
            Object.keys(obj).sort().forEach(key => {
                const value = obj[key];
                const fullKey = prefix ? `${prefix}.${key}` : key;
                if (isPlainObject(value)) {
                    rows.push(...flattenObject(value, fullKey));
                } else if (Array.isArray(value)) {
                    rows.push([fullKey, JSON.stringify(value)]);
                } else {
                    rows.push([fullKey, value]);
                }
            });
            return rows;
        }

        function renderAllFields(payload) {
            const rows = flattenObject(payload);
            if (!rows.length) {
                document.getElementById('allFieldsContainer').innerHTML = '<p class="loading">No fields available</p>';
                return;
            }

            let html = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Field</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            rows.forEach(([key, value]) => {
                const display = (value === null || value === undefined) ? '-' : value;
                html += `
                    <tr>
                        <td>${key}</td>
                        <td>${display}</td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            document.getElementById('allFieldsContainer').innerHTML = html;
        }

        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('totalRecords').textContent = stats.total_records.toLocaleString();
                document.getElementById('recentRecords').textContent = stats.recent_hour_records.toLocaleString();
                document.getElementById('avgDownlink').textContent = stats.avg_downlink_mbps;
                document.getElementById('avgLatency').textContent = stats.avg_latency_ms;
            } catch (error) {
                console.error('Statistics update error:', error);
            }
        }

        async function updateData() {
            try {
                // 실시간 데이터로 테이블 표시
                const droneAddress = document.getElementById('droneAddress').value;
                const response = await fetch(`/api/live_data?drone_address=${encodeURIComponent(droneAddress)}`);
                const rawData = await response.json();
                
                if (rawData.error) {
                    const detail = rawData.detail ? `<br>${rawData.detail}` : '';
                    document.getElementById('dataContainer').innerHTML = `<p class="loading">No data received.${detail}</p>`;
                    document.getElementById('allFieldsContainer').innerHTML = '<p class="loading">No data received.</p>';
                    return;
                }

                renderAllFields(rawData);
                
                // 실시간 데이터를 배열 형태로 변환
                const data = [rawData];

                let html = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Status</th>
                                <th>Download</th>
                                <th>Upload</th>
                                <th>Latency</th>
                                <th>SNR</th>
                                <th>Azimuth</th>
                                <th>Elevation</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                data.reverse().forEach(item => {
                    html += `
                        <tr>
                            <td>${formatTimestamp(item.timestamp)}</td>
                            <td><span class="status ${getStatusClass(item.state)}">${item.state}</span></td>
                            <td>${((item.downlink_throughput_bps || 0) / 1024 / 1024).toFixed(2)} Mbps</td>
                            <td>${((item.uplink_throughput_bps || 0) / 1024 / 1024).toFixed(2)} Mbps</td>
                            <td>${(item.ping_latency_ms || 0).toFixed(1)} ms</td>
                            <td>${(item.snr || 0).toFixed(1)} dB</td>
                            <td>${(item.azimuth || 0).toFixed(1)}°</td>
                            <td>${(item.elevation || 0).toFixed(1)}°</td>
                        </tr>
                    `;
                });

                html += '</tbody></table>';
                document.getElementById('dataContainer').innerHTML = html;
                document.getElementById('lastUpdate').textContent = new Date().toLocaleString('ko-KR');

            } catch (error) {
                console.error('Data update error:', error);
                document.getElementById('dataContainer').innerHTML = '<p class="loading">Data loading error</p>';
            }
        }

        // 드론 제어 기능
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
                    alert(`Success: ${result.message}`);
                    updateDroneStatus();  // 상태 즉시 업데이트
                } else {
                    const detail = result.detail ? `\n${result.detail}` : '';
                    alert(`Error: ${result.error}${detail}`);
                }
            } catch (error) {
                alert(`Connection error: ${error.message}`);
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
                    const state = status.state || '-';
                    const stateEl = document.getElementById('droneState');
                    stateEl.textContent = state;
                    stateEl.className = `status ${getStatusClass(state)}`;
                    document.getElementById('droneFile').textContent = status.current_file || '-';
                    document.getElementById('droneDuration').textContent = status.duration || '-';
                } else {
                    const stateEl = document.getElementById('droneState');
                    stateEl.textContent = 'ERROR';
                    stateEl.className = 'status disconnected';
                    document.getElementById('droneFile').textContent = '-';
                    document.getElementById('droneDuration').textContent = '-';
                }
            } catch (error) {
                const stateEl = document.getElementById('droneState');
                stateEl.textContent = 'OFFLINE';
                stateEl.className = 'status disconnected';
                document.getElementById('droneFile').textContent = '-';
                document.getElementById('droneDuration').textContent = '-';
            }
        }

        // 실시간 데이터 업데이트
        async function updateLiveData() {
            const droneAddress = document.getElementById('droneAddress').value;
            
            try {
                const response = await fetch(`/api/live_data?drone_address=${encodeURIComponent(droneAddress)}`);
                const data = await response.json();
                
                if (data.error) {
                    // 실시간 데이터를 가져올 수 없으면 스탯 카드를 0으로 표시
                    document.getElementById('liveDownlink').textContent = '0.00';
                    document.getElementById('liveUplink').textContent = '0.00';
                    document.getElementById('liveLatency').textContent = '0.0';
                    document.getElementById('liveSNR').textContent = '0.0';
                    return;
                }
                
                // 실시간 데이터로 스탯 카드 업데이트
                document.getElementById('liveDownlink').textContent = ((data.downlink_throughput_bps || 0) / 1024 / 1024).toFixed(2);
                document.getElementById('liveUplink').textContent = ((data.uplink_throughput_bps || 0) / 1024 / 1024).toFixed(2);
                document.getElementById('liveLatency').textContent = (data.ping_latency_ms || 0).toFixed(1);
                document.getElementById('liveSNR').textContent = (data.snr || 0).toFixed(1);
                
                // 상단 통계도 실시간 데이터로 업데이트
                document.getElementById('avgDownlink').textContent = ((data.downlink_throughput_bps || 0) / 1024 / 1024).toFixed(2);
                document.getElementById('avgLatency').textContent = (data.ping_latency_ms || 0).toFixed(1);
                document.getElementById('totalRecords').textContent = 'Simulation';
                document.getElementById('recentRecords').textContent = 'LIVE';
                
                // 마지막 업데이트 시간 표시
                document.getElementById('liveTimestamp').textContent = formatTimestamp(data.timestamp);
                
            } catch (error) {
                console.error('Live data update error:', error);
            }
        }

        // 이벤트 리스너
        document.getElementById('startBtn').addEventListener('click', () => controlDrone('start'));
        document.getElementById('stopBtn').addEventListener('click', () => controlDrone('stop'));
        document.getElementById('statusBtn').addEventListener('click', updateDroneStatus);

        // 자동 업데이트
        updateStats();
        updateData();
        updateDroneStatus();  // 드론 상태 초기 로드
        updateLiveData();     // 실시간 데이터 초기 로드
        setInterval(updateStats, 60000);     // 1분마다 통계 업데이트
        setInterval(updateData, 2000);       // 2초마다 데이터 업데이트 (자연스러운 실시간)
        setInterval(updateDroneStatus, 10000); // 10초마다 드론 상태 업데이트
        setInterval(updateLiveData, 1000);   // 1초마다 실시간 데이터 업데이트
    </script>
</body>
</html>
"""

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='지상국 데이터 수신기')
    parser.add_argument('--port', type=int, default=8080, help='수신 포트')
    parser.add_argument('--data-dir', default='/opt/ground-station-data', help='데이터 저장 디렉토리')
    
    args = parser.parse_args()
    
    receiver = GroundStationReceiver(port=args.port, data_dir=args.data_dir)
    receiver.run()

if __name__ == "__main__":
    main()
