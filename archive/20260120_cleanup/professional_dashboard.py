#!/usr/bin/env python3
"""
Professional Starlink Dashboard - Compact & Ultra-Fast
실시간 모니터링 (1초 업데이트) + 전문적인 디자인
"""

import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from collections import deque
import logging

from starlink_grpc_web import StarlinkGrpcWebMonitor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'professional_starlink_monitor_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# 전역 데이터 저장
data_history = deque(maxlen=300)  # 5분간 1초 데이터 (300포인트)
current_data = {}
monitor = None
monitoring_thread = None
is_monitoring = False

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('professional_dashboard.log'),
            logging.StreamHandler()
        ]
    )

def ultra_fast_collector():
    """초고속 데이터 수집 (1초마다)"""
    global current_data, is_monitoring
    
    while is_monitoring:
        try:
            if monitor:
                data = monitor.collect_data()
                if data:
                    current_data = data
                    data_history.append(data)
                    
                    # WebSocket으로 즉시 전송
                    socketio.emit('live_update', data)
                    
        except Exception as e:
            logging.error(f"데이터 수집 오류: {e}")
        
        time.sleep(1)  # 1초마다 업데이트

@app.route('/')
def professional_dashboard():
    """전문적인 컴팩트 대시보드"""
    return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Starlink Pro Monitor</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1d2e 100%);
            color: #e2e8f0;
            min-height: 100vh;
            font-size: 13px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 12px;
            display: grid;
            grid-template-columns: 1fr 1fr 350px;
            grid-template-rows: auto 1fr;
            gap: 12px;
            min-height: 100vh;
        }
        
        .header {
            grid-column: 1 / -1;
            background: linear-gradient(90deg, #1e40af 0%, #3b82f6 100%);
            padding: 15px 25px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(30, 64, 175, 0.3);
        }
        
        .header h1 {
            font-size: 22px;
            font-weight: 600;
            color: white;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .header-info {
            display: flex;
            gap: 20px;
            font-size: 12px;
            color: rgba(255,255,255,0.9);
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            padding: 8px;
            background: rgba(30, 41, 59, 0.4);
            border-radius: 12px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        .metric-card {
            background: linear-gradient(145deg, #1e293b 0%, #334155 100%);
            padding: 16px;
            border-radius: 10px;
            border: 1px solid rgba(71, 85, 105, 0.3);
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #3b82f6, transparent);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            border-color: #3b82f6;
        }
        
        .metric-title {
            font-size: 11px;
            color: #94a3b8;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 4px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .metric-unit {
            font-size: 10px;
            color: #64748b;
            font-weight: 500;
        }
        
        .metric-good { color: #10b981; }
        .metric-warning { color: #f59e0b; }
        .metric-bad { color: #ef4444; }
        
        .charts-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: rgba(30, 41, 59, 0.4);
            border-radius: 12px;
            padding: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        .chart-wrapper {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 8px;
            padding: 12px;
            height: 180px;
        }
        
        .info-panel {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .system-info, .alerts-panel {
            background: rgba(30, 41, 59, 0.4);
            border-radius: 12px;
            padding: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        .panel-title {
            font-size: 14px;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid rgba(71, 85, 105, 0.2);
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            font-size: 11px;
            color: #94a3b8;
        }
        
        .info-value {
            font-size: 11px;
            color: #f1f5f9;
            font-weight: 500;
        }
        
        .alert {
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .alert-warning {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #fbbf24;
        }
        
        .alert-good {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
        }
        
        .data-fresh {
            animation: dataUpdate 0.5s ease;
        }
        
        @keyframes dataUpdate {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }
        
        .connection-status {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }
        
        @media (max-width: 1400px) {
            .container {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto auto auto;
            }
            
            .metrics-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>
                <span class="status-indicator" id="connectionStatus"></span>
                🛰️ Starlink Professional Monitor
            </h1>
            <div class="header-info">
                <div class="connection-status">LIVE</div>
                <div id="lastUpdate">마지막 업데이트: --:--:--</div>
                <div id="updateRate">업데이트: 1초</div>
            </div>
        </header>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">다운로드 속도</div>
                <div class="metric-value" id="downloadSpeed">-</div>
                <div class="metric-unit">Mbps</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">업로드 속도</div>
                <div class="metric-value" id="uploadSpeed">-</div>
                <div class="metric-unit">Mbps</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">핑 지연시간</div>
                <div class="metric-value" id="pingLatency">-</div>
                <div class="metric-unit">ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">패킷 손실률</div>
                <div class="metric-value" id="packetLoss">-</div>
                <div class="metric-unit">%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">신호 대 잡음비</div>
                <div class="metric-value" id="snrValue">-</div>
                <div class="metric-unit">dB</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">GPS 위성</div>
                <div class="metric-value" id="gpsSats">-</div>
                <div class="metric-unit">개</div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-wrapper">
                <canvas id="speedChart"></canvas>
            </div>
            <div class="chart-wrapper">
                <canvas id="latencyChart"></canvas>
            </div>
        </div>
        
        <div class="info-panel">
            <div class="system-info">
                <div class="panel-title">🖥️ 시스템 정보</div>
                <div class="info-row">
                    <span class="info-label">가동시간</span>
                    <span class="info-value" id="uptime">--:--:--</span>
                </div>
                <div class="info-row">
                    <span class="info-label">하드웨어</span>
                    <span class="info-value" id="hardware">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">소프트웨어</span>
                    <span class="info-value" id="software">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">상태</span>
                    <span class="info-value" id="state">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">위성 ID</span>
                    <span class="info-value" id="satelliteId">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">빔 ID</span>
                    <span class="info-value" id="beamId">-</span>
                </div>
            </div>
            
            <div class="alerts-panel">
                <div class="panel-title">⚠️ 상태 및 경고</div>
                <div id="alertsContainer">
                    <div class="alert alert-good">
                        ✅ 모든 시스템 정상 작동
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        
        // 차트 설정
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: {
                    grid: { color: 'rgba(71, 85, 105, 0.2)' },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                }
            },
            elements: { point: { radius: 0 } }
        };
        
        // 속도 차트
        const speedCtx = document.getElementById('speedChart').getContext('2d');
        const speedChart = new Chart(speedCtx, {
            type: 'line',
            data: {
                labels: Array(60).fill(''),
                datasets: [{
                    label: '다운로드',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true
                }, {
                    label: '업로드',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: chartOptions
        });
        
        // 지연시간 차트
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        const latencyChart = new Chart(latencyCtx, {
            type: 'line',
            data: {
                labels: Array(60).fill(''),
                datasets: [{
                    label: '핑 지연시간',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: chartOptions
        });
        
        socket.on('live_update', function(data) {
            updateDashboard(data);
        });
        
        function updateDashboard(data) {
            // 메트릭 업데이트
            const downloadMbps = (data.downlink_throughput_bps / 1000000).toFixed(1);
            const uploadMbps = (data.uplink_throughput_bps / 1000000).toFixed(1);
            const ping = data.pop_ping_latency_ms.toFixed(1);
            const loss = (data.pop_ping_drop_rate * 100).toFixed(3);
            
            updateMetric('downloadSpeed', downloadMbps, getSpeedColor(downloadMbps));
            updateMetric('uploadSpeed', uploadMbps, getSpeedColor(uploadMbps / 5));
            updateMetric('pingLatency', ping, getPingColor(ping));
            updateMetric('packetLoss', loss, getLossColor(loss));
            updateMetric('snrValue', data.snr.toFixed(1), getSNRColor(data.snr));
            updateMetric('gpsSats', data.gps_sats, data.gps_sats >= 10 ? 'metric-good' : 'metric-warning');
            
            // 시스템 정보 업데이트
            document.getElementById('uptime').textContent = data.uptime_formatted || '--:--:--';
            document.getElementById('hardware').textContent = data.hardware_version || '-';
            document.getElementById('software').textContent = data.software_version?.substring(0, 15) + '...' || '-';
            document.getElementById('state').textContent = data.state || '-';
            document.getElementById('satelliteId').textContent = data.satellite_id || '-';
            document.getElementById('beamId').textContent = data.beam_id || '-';
            
            // 차트 업데이트
            updateChart(speedChart, [parseFloat(downloadMbps), parseFloat(uploadMbps)]);
            updateChart(latencyChart, [parseFloat(ping)]);
            
            // 경고 업데이트
            updateAlerts(data);
            
            // 마지막 업데이트 시간
            document.getElementById('lastUpdate').textContent = 
                '마지막 업데이트: ' + new Date().toLocaleTimeString();
        }
        
        function updateMetric(elementId, value, colorClass) {
            const element = document.getElementById(elementId);
            element.textContent = value;
            element.className = 'metric-value ' + colorClass;
            element.parentElement.classList.add('data-fresh');
            setTimeout(() => element.parentElement.classList.remove('data-fresh'), 500);
        }
        
        function updateChart(chart, values) {
            if (chart.data.datasets[0].data.length >= 60) {
                chart.data.datasets.forEach(dataset => dataset.data.shift());
            }
            
            values.forEach((value, index) => {
                if (chart.data.datasets[index]) {
                    chart.data.datasets[index].data.push(value);
                }
            });
            
            chart.update('none');
        }
        
        function updateAlerts(data) {
            const container = document.getElementById('alertsContainer');
            container.innerHTML = '';
            
            const alerts = [];
            if (data.alerts_thermal_throttle) alerts.push({type: 'warning', text: '🔥 열 제한 활성'});
            if (data.alerts_mast_not_near_vertical) alerts.push({type: 'warning', text: '📐 안테나 기울기 경고'});
            if (data.alerts_slow_ethernet_speeds) alerts.push({type: 'warning', text: '🐌 느린 이더넷 속도'});
            
            if (alerts.length === 0) {
                container.innerHTML = '<div class="alert alert-good">✅ 모든 시스템 정상 작동</div>';
            } else {
                alerts.forEach(alert => {
                    container.innerHTML += \`<div class="alert alert-\${alert.type}">\${alert.text}</div>\`;
                });
            }
        }
        
        function getSpeedColor(speed) {
            if (speed >= 100) return 'metric-good';
            if (speed >= 50) return 'metric-warning';
            return 'metric-bad';
        }
        
        function getPingColor(ping) {
            if (ping <= 30) return 'metric-good';
            if (ping <= 60) return 'metric-warning';
            return 'metric-bad';
        }
        
        function getLossColor(loss) {
            if (loss <= 1) return 'metric-good';
            if (loss <= 3) return 'metric-warning';
            return 'metric-bad';
        }
        
        function getSNRColor(snr) {
            if (snr >= 10) return 'metric-good';
            if (snr >= 7) return 'metric-warning';
            return 'metric-bad';
        }
    </script>
</body>
</html>
    '''

@app.route('/api/data')
def get_current_data():
    """현재 데이터 반환"""
    return jsonify(current_data)

@app.route('/api/history')
def get_history():
    """데이터 히스토리 반환"""
    return jsonify(list(data_history))

@socketio.on('connect')
def handle_connect():
    """클라이언트 연결시"""
    logging.info('클라이언트 연결됨')
    emit('status', {'message': '실시간 모니터링 연결됨'})
    if current_data:
        emit('live_update', current_data)

def start_monitoring():
    """모니터링 시작"""
    global monitor, monitoring_thread, is_monitoring
    
    try:
        monitor = StarlinkGrpcWebMonitor()
        is_monitoring = True
        monitoring_thread = threading.Thread(target=ultra_fast_collector, daemon=True)
        monitoring_thread.start()
        logging.info("초고속 모니터링 시작됨 (1초 업데이트)")
        return True
    except Exception as e:
        logging.error(f"모니터링 시작 실패: {e}")
        return False

if __name__ == '__main__':
    setup_logging()
    
    print("=" * 80)
    print("🛰️  Starlink Professional Dashboard")
    print("=" * 80)
    print("📡 API: Enhanced gRPC-Web (192.168.100.1:9201)")
    print("🌐 웹 주소: http://localhost:5777")
    print("⚡ 업데이트: 1초마다 실시간 (초고속)")
    print("📊 차트: 실시간 라이브 업데이트")
    print("💾 CSV: 자동 저장 (모든 메트릭 포함)")
    print("🎨 디자인: 프로페셔널 컴팩트")
    print("=" * 80)
    print("⏳ 브라우저에서 http://localhost:5777 접속")
    print("🛑 종료: Ctrl+C")
    print("=" * 80)
    
    if start_monitoring():
        try:
            socketio.run(app, host='0.0.0.0', port=5777, debug=False, allow_unsafe_werkzeug=True)
        finally:
            is_monitoring = False
    else:
        print("❌ 모니터링 시작 실패")