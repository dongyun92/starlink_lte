#!/usr/bin/env python3
"""
Quick Starlink 대시보드 - 간단한 Flask 버전
"""

from flask import Flask, render_template, jsonify
import json
from starlink_grpc_web import StarlinkGrpcWebMonitor

app = Flask(__name__)

# 전역 모니터
monitor = StarlinkGrpcWebMonitor()

@app.route('/')
def dashboard():
    """메인 페이지"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Starlink 실시간 모니터링</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; background: #1e3a8a; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        .card h3 { margin: 0; color: #333; font-size: 14px; }
        .card .value { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .card .unit { font-size: 12px; color: #666; }
        .refresh { background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 20px auto; display: block; }
        .refresh:hover { background: #059669; }
        .log { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .timestamp { color: #666; font-size: 12px; }
        .status-good { color: #10b981; }
        .status-warning { color: #f59e0b; }
        .status-bad { color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛰️ Starlink 실시간 모니터링</h1>
            <p>gRPC-Web API (192.168.100.1:9201)</p>
        </div>
        
        <div class="cards" id="cards">
            <div class="card">
                <h3>다운로드 속도</h3>
                <div class="value" id="download">-</div>
                <div class="unit">Mbps</div>
            </div>
            <div class="card">
                <h3>업로드 속도</h3>
                <div class="value" id="upload">-</div>
                <div class="unit">Mbps</div>
            </div>
            <div class="card">
                <h3>핑 지연시간</h3>
                <div class="value" id="ping">-</div>
                <div class="unit">ms</div>
            </div>
            <div class="card">
                <h3>SNR</h3>
                <div class="value" id="snr">-</div>
                <div class="unit">dB</div>
            </div>
            <div class="card">
                <h3>패킷 손실</h3>
                <div class="value" id="packet_loss">-</div>
                <div class="unit">%</div>
            </div>
            <div class="card">
                <h3>GPS 위성</h3>
                <div class="value" id="gps_sats">-</div>
                <div class="unit">개</div>
            </div>
        </div>
        
        <button class="refresh" onclick="loadData()">🔄 새로고침</button>
        
        <div class="log">
            <h3>📊 실시간 상태</h3>
            <div id="status">데이터를 불러오는 중...</div>
        </div>
    </div>

    <script>
        function loadData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // 값 업데이트
                    document.getElementById('download').textContent = (data.downlink_throughput_bps / 1000000).toFixed(1);
                    document.getElementById('upload').textContent = (data.uplink_throughput_bps / 1000000).toFixed(1);
                    document.getElementById('ping').textContent = data.pop_ping_latency_ms.toFixed(1);
                    document.getElementById('snr').textContent = data.snr.toFixed(1);
                    document.getElementById('packet_loss').textContent = (data.pop_ping_drop_rate * 100).toFixed(2);
                    document.getElementById('gps_sats').textContent = data.gps_sats;
                    
                    // 상태 업데이트
                    const time = new Date().toLocaleTimeString();
                    let status = `<div class="timestamp">${time}</div>`;
                    status += `<div class="status-good">✅ 연결됨</div>`;
                    status += `<div>상태: ${data.state}</div>`;
                    status += `<div>가동시간: ${Math.floor(data.uptime_s / 3600)}시간 ${Math.floor((data.uptime_s % 3600) / 60)}분</div>`;
                    
                    // 경고 확인
                    if (data.alerts_thermal_throttle) status += '<div class="status-warning">⚠️ 열 제한</div>';
                    if (data.alerts_mast_not_near_vertical) status += '<div class="status-warning">⚠️ 안테나 기울기</div>';
                    if (data.alerts_slow_ethernet_speeds) status += '<div class="status-warning">⚠️ 느린 이더넷</div>';
                    
                    document.getElementById('status').innerHTML = status;
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = `<div class="status-bad">❌ 데이터 로드 실패: ${error.message}</div>`;
                });
        }
        
        // 페이지 로드시 데이터 로드
        loadData();
        
        // 30초마다 자동 새로고침
        setInterval(loadData, 30000);
    </script>
</body>
</html>
    '''

@app.route('/api/data')
def get_data():
    """현재 데이터 반환"""
    try:
        data = monitor.collect_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🛰️  Quick Starlink 대시보드 시작")
    print("🌐 http://localhost:9999")
    print("📊 30초마다 자동 새로고침")
    print("🛑 Ctrl+C로 종료")
    app.run(host='0.0.0.0', port=9999, debug=False)