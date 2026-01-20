#!/usr/bin/env python3
"""
실제 Starlink 실시간 WebSocket 대시보드
- 실제 gRPC-Web API 연결
- 30초마다 자동 실시간 갱신
- WebSocket으로 브라우저 자동 업데이트
"""

import json
import threading
import time
import logging
from datetime import datetime
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from collections import deque

from real_starlink_api import RealStarlinkAPI

app = Flask(__name__)
app.config['SECRET_KEY'] = 'starlink_realtime_50001'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 전역 데이터
data_history = deque(maxlen=50)
current_data = {}
api = None
monitoring_thread = None
is_monitoring = False

# HTML 템플릿 (내장)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Starlink 실시간 모니터링</title>
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
            margin: 0; padding: 20px; background: #0a0e1a; color: white; 
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { 
            text-align: center; background: linear-gradient(135deg, #1e40af, #3b82f6); 
            padding: 30px; border-radius: 15px; margin-bottom: 25px; 
            box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
        }
        .header h1 { margin: 0; font-size: 2.5em; font-weight: 700; }
        .header .subtitle { opacity: 0.9; margin-top: 10px; }
        
        .status-bar { 
            display: flex; justify-content: space-between; align-items: center; 
            background: #1f2937; padding: 15px 25px; border-radius: 10px; 
            margin-bottom: 25px; border-left: 4px solid #10b981;
        }
        .connection-status { display: flex; align-items: center; gap: 8px; }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .status-connected { background: #10b981; animation: pulse 2s infinite; }
        .status-disconnected { background: #ef4444; }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .metrics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
            gap: 20px; margin-bottom: 25px; 
        }
        .metric-card { 
            background: linear-gradient(145deg, #1f2937, #374151); 
            padding: 25px; border-radius: 12px; text-align: center; 
            border: 1px solid #4b5563; position: relative; overflow: hidden;
        }
        .metric-card:before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; 
            height: 3px; background: var(--accent-color, #3b82f6);
        }
        .metric-icon { font-size: 2.5em; margin-bottom: 10px; }
        .metric-value { font-size: 2.2em; font-weight: 700; margin: 10px 0; }
        .metric-label { font-size: 0.95em; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }
        .metric-unit { font-size: 0.85em; opacity: 0.7; margin-top: 5px; }
        
        .chart-section { 
            background: #1f2937; padding: 25px; border-radius: 12px; 
            margin-bottom: 25px; border: 1px solid #4b5563;
        }
        .chart-title { font-size: 1.3em; font-weight: 600; margin-bottom: 15px; }
        
        .alerts-section {
            background: #1f2937; padding: 25px; border-radius: 12px;
            border: 1px solid #4b5563;
        }
        .alert-item { 
            padding: 12px 15px; margin: 8px 0; border-radius: 8px; 
            display: flex; align-items: center; gap: 10px;
        }
        .alert-success { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .alert-warning { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .alert-error { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        
        /* 색상 테마 */
        .download-card { --accent-color: #10b981; }
        .upload-card { --accent-color: #06b6d4; }
        .ping-card { --accent-color: #f59e0b; }
        .snr-card { --accent-color: #3b82f6; }
        .loss-card { --accent-color: #ef4444; }
        .gps-card { --accent-color: #8b5cf6; }
        
        .auto-refresh { 
            position: fixed; bottom: 20px; right: 20px; 
            background: #3b82f6; color: white; border: none; 
            padding: 12px 20px; border-radius: 50px; cursor: pointer;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
        .auto-refresh:hover { background: #2563eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛰️ Starlink 실시간 모니터링</h1>
            <div class="subtitle">gRPC-Web API • 실시간 업데이트 • 30초 간격</div>
        </div>
        
        <div class="status-bar">
            <div class="connection-status">
                <div class="status-dot status-disconnected" id="status-dot"></div>
                <span id="connection-text">연결 대기중...</span>
            </div>
            <div id="last-update">마지막 업데이트: -</div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card download-card">
                <div class="metric-icon">📥</div>
                <div class="metric-value" id="download-speed">-</div>
                <div class="metric-label">다운로드</div>
                <div class="metric-unit">Mbps</div>
            </div>
            
            <div class="metric-card upload-card">
                <div class="metric-icon">📤</div>
                <div class="metric-value" id="upload-speed">-</div>
                <div class="metric-label">업로드</div>
                <div class="metric-unit">Mbps</div>
            </div>
            
            <div class="metric-card ping-card">
                <div class="metric-icon">⚡</div>
                <div class="metric-value" id="ping-latency">-</div>
                <div class="metric-label">핑 지연시간</div>
                <div class="metric-unit">ms</div>
            </div>
            
            <div class="metric-card snr-card">
                <div class="metric-icon">📡</div>
                <div class="metric-value" id="snr-value">-</div>
                <div class="metric-label">신호 품질 (SNR)</div>
                <div class="metric-unit">dB</div>
            </div>
            
            <div class="metric-card loss-card">
                <div class="metric-icon">⚠️</div>
                <div class="metric-value" id="packet-loss">-</div>
                <div class="metric-label">패킷 손실</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card gps-card">
                <div class="metric-icon">🛰️</div>
                <div class="metric-value" id="gps-satellites">-</div>
                <div class="metric-label">GPS 위성</div>
                <div class="metric-unit">개</div>
            </div>
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📊 성능 히스토리</div>
            <div id="performance-chart">실시간 차트가 여기에 표시됩니다...</div>
        </div>
        
        <div class="alerts-section">
            <div class="chart-title">🚨 시스템 상태 및 경고</div>
            <div id="alerts-container">
                <div class="alert-item alert-success">
                    <span>✅</span>
                    <span>시스템 상태 확인 중...</span>
                </div>
            </div>
        </div>
    </div>
    
    <button class="auto-refresh" onclick="requestUpdate()">🔄 수동 업데이트</button>
    
    <script>
        // Socket.IO 연결
        const socket = io();
        
        socket.on('connect', function() {
            console.log('서버에 연결됨');
            document.getElementById('status-dot').className = 'status-dot status-connected';
            document.getElementById('connection-text').textContent = '연결됨';
        });
        
        socket.on('disconnect', function() {
            console.log('서버 연결 끊김');
            document.getElementById('status-dot').className = 'status-dot status-disconnected';
            document.getElementById('connection-text').textContent = '연결 끊김';
        });
        
        socket.on('data_update', function(data) {
            console.log('실시간 데이터 수신:', data);
            updateDashboard(data);
        });
        
        function updateDashboard(data) {
            // 메트릭 업데이트
            const downloadMbps = (data.downlink_throughput_bps / 1000000).toFixed(1);
            const uploadMbps = (data.uplink_throughput_bps / 1000000).toFixed(1);
            const pingMs = data.pop_ping_latency_ms.toFixed(1);
            const snrDb = data.snr.toFixed(1);
            const lossPercent = (data.pop_ping_drop_rate * 100).toFixed(2);
            const gpsSats = data.gps_sats;
            
            document.getElementById('download-speed').textContent = downloadMbps;
            document.getElementById('upload-speed').textContent = uploadMbps;
            document.getElementById('ping-latency').textContent = pingMs;
            document.getElementById('snr-value').textContent = snrDb;
            document.getElementById('packet-loss').textContent = lossPercent;
            document.getElementById('gps-satellites').textContent = gpsSats;
            
            // 마지막 업데이트 시간
            const now = new Date();
            document.getElementById('last-update').textContent = 
                `마지막 업데이트: ${now.toLocaleTimeString()}`;
            
            // 경고 업데이트
            updateAlerts(data);
        }
        
        function updateAlerts(data) {
            const container = document.getElementById('alerts-container');
            let alertsHtml = '';
            
            // 시스템 정보
            const uptimeHours = Math.floor(data.uptime_s / 3600);
            const uptimeMinutes = Math.floor((data.uptime_s % 3600) / 60);
            
            alertsHtml += `
                <div class="alert-item alert-success">
                    <span>✅</span>
                    <span>연결 상태: ${data.state} (가동시간: ${uptimeHours}시간 ${uptimeMinutes}분)</span>
                </div>
            `;
            
            alertsHtml += `
                <div class="alert-item alert-success">
                    <span>📦</span>
                    <span>소프트웨어: ${data.software_version}</span>
                </div>
            `;
            
            // 경고 확인
            if (data.alerts_thermal_throttle) {
                alertsHtml += `
                    <div class="alert-item alert-warning">
                        <span>🔥</span>
                        <span>열 제한 활성화 - 성능이 제한될 수 있습니다</span>
                    </div>
                `;
            }
            
            if (data.alerts_mast_not_near_vertical) {
                alertsHtml += `
                    <div class="alert-item alert-warning">
                        <span>📐</span>
                        <span>안테나 기울기 문제 - 위치를 조정하세요</span>
                    </div>
                `;
            }
            
            if (data.alerts_slow_ethernet_speeds) {
                alertsHtml += `
                    <div class="alert-item alert-warning">
                        <span>🐌</span>
                        <span>이더넷 속도 저하 - 케이블 연결을 확인하세요</span>
                    </div>
                `;
            }
            
            // 성능 경고
            if (data.pop_ping_drop_rate > 0.05) {
                alertsHtml += `
                    <div class="alert-item alert-error">
                        <span>⚠️</span>
                        <span>높은 패킷 손실률 (${(data.pop_ping_drop_rate * 100).toFixed(1)}%)</span>
                    </div>
                `;
            }
            
            if (data.pop_ping_latency_ms > 100) {
                alertsHtml += `
                    <div class="alert-item alert-warning">
                        <span>🐌</span>
                        <span>높은 핑 지연시간 (${data.pop_ping_latency_ms.toFixed(0)}ms)</span>
                    </div>
                `;
            }
            
            container.innerHTML = alertsHtml;
        }
        
        function requestUpdate() {
            socket.emit('request_update');
        }
    </script>
</body>
</html>
'''

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s'
    )

def data_collector():
    """백그라운드 실시간 데이터 수집"""
    global current_data, is_monitoring
    
    while is_monitoring:
        try:
            if api:
                # 실제 스타링크 API 호출
                data = api.get_status_with_fallback()
                if data:
                    current_data = data
                    data_history.append(data)
                    
                    # WebSocket으로 모든 클라이언트에게 실시간 전송
                    socketio.emit('data_update', data)
                    
                    # 로그
                    down_mbps = data.get('downlink_throughput_bps', 0) / 1000000
                    ping = data.get('pop_ping_latency_ms', 0)
                    source = data.get('data_source', 'unknown')
                    print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] {down_mbps:.1f}Mbps, {ping:.1f}ms ({source})")
                    
        except Exception as e:
            logging.error(f"데이터 수집 오류: {e}")
        
        # 30초 대기
        time.sleep(30)

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def handle_connect():
    print(f"🌐 클라이언트 연결: {datetime.now().strftime('%H:%M:%S')}")
    
    # 현재 데이터 즉시 전송
    if current_data:
        emit('data_update', current_data)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"🔌 클라이언트 연결 해제: {datetime.now().strftime('%H:%M:%S')}")

@socketio.on('request_update')
def handle_request_update():
    """수동 업데이트 요청 처리"""
    if api:
        data = api.get_status_with_fallback()
        if data:
            emit('data_update', data)

def start_monitoring():
    global api, monitoring_thread, is_monitoring
    
    try:
        api = RealStarlinkAPI()
        is_monitoring = True
        
        # 백그라운드 스레드 시작
        monitoring_thread = threading.Thread(target=data_collector, daemon=True)
        monitoring_thread.start()
        
        print("🛰️ 실시간 모니터링 시작됨")
        return True
        
    except Exception as e:
        logging.error(f"모니터링 시작 실패: {e}")
        return False

def stop_monitoring():
    global is_monitoring
    is_monitoring = False

if __name__ == '__main__':
    setup_logging()
    
    print("=" * 70)
    print("🛰️  Starlink 실시간 WebSocket 대시보드")
    print("=" * 70)
    print("🌐 웹 주소: http://localhost:8947")
    print("📡 API: 실제 gRPC-Web (192.168.100.1:9201)")
    print("⚡ 실시간: WebSocket 자동 갱신 (30초 간격)")
    print("📊 기능: 클릭 없이 자동 업데이트")
    print("=" * 70)
    print("⏳ 브라우저에서 http://localhost:8947 접속하세요!")
    print("🛑 종료: Ctrl+C")
    print("=" * 70)
    
    if start_monitoring():
        try:
            socketio.run(app, host='0.0.0.0', port=8947, debug=False, allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            print("\n🛑 대시보드 종료됨")
        finally:
            stop_monitoring()
    else:
        print("❌ 모니터링 시작 실패")
