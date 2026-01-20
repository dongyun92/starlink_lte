#!/usr/bin/env python3
"""
확실히 작동하는 HTTP 폴링 기반 실시간 대시보드
"""
from flask import Flask, render_template_string, jsonify
import time
import csv
import os

app = Flask(__name__)

def get_latest_csv_data():
    """최신 CSV 데이터 가져오기"""
    csv_file = 'ultrafast_starlink_data_20260106.csv'
    
    if not os.path.exists(csv_file):
        return None
        
    try:
        with open(csv_file, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return None
                
            # 마지막 라인 파싱
            last_line = lines[-1].strip().split(',')
            
            return {
                'timestamp': last_line[0],
                'update_count': int(last_line[1]) if last_line[1] else 0,
                'interval_ms': float(last_line[2]) if last_line[2] else 0,
                'device_id': last_line[3],
                'state': last_line[6],
                'uptime': int(last_line[7]) if last_line[7] else 0,
                'download_speed_mbps': round(float(last_line[11]) / 1000000, 2) if last_line[11] else 0,
                'upload_speed_mbps': round(float(last_line[12]) / 1000000, 2) if last_line[12] else 0,
                'ping_latency': float(last_line[9]) if last_line[9] else 0,
                'drop_rate': float(last_line[8]) if last_line[8] else 0,
                'direction_azimuth': float(last_line[18]) if last_line[18] else 0,
                'direction_elevation': float(last_line[19]) if last_line[19] else 0,
                'gps_sats': int(last_line[23]) if last_line[23] else 0,
                'obstruction': float(last_line[14]) if last_line[14] else 0,
                'server_time': time.strftime('%H:%M:%S')
            }
    except Exception as e:
        print(f"CSV 읽기 오류: {e}")
        return None

@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 작동하는 실시간 스타링크 대시보드</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Monaco', 'Consolas', monospace;
            background: linear-gradient(135deg, #000000 0%, #1a1a2e 50%, #16213e 100%);
            color: #00ff41; min-height: 100vh; padding: 20px;
        }
        .header { 
            text-align: center; margin-bottom: 30px; 
            border: 2px solid #00ff41; padding: 20px; border-radius: 10px;
            background: rgba(0, 255, 65, 0.1);
        }
        .header h1 { 
            color: #00ff41; margin-bottom: 10px; font-size: 2.5em; 
            text-shadow: 0 0 20px #00ff41;
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 20px #00ff41; }
            to { text-shadow: 0 0 40px #00ff41, 0 0 60px #00ff41; }
        }
        .status-bar { 
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(0, 255, 65, 0.1); padding: 15px; border-radius: 10px;
            margin-bottom: 20px; border: 1px solid #00ff41; font-size: 1.2em;
        }
        .grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 20px; margin-bottom: 30px;
        }
        .card { 
            background: rgba(0, 255, 65, 0.05); border-radius: 15px; padding: 20px;
            border: 2px solid #00ff41; backdrop-filter: blur(5px);
        }
        .card h3 { 
            color: #00ff41; margin-bottom: 15px; font-size: 1.4em;
            text-shadow: 0 0 10px #00ff41; border-bottom: 1px solid #00ff41;
            padding-bottom: 10px;
        }
        .metric { 
            display: flex; justify-content: space-between; margin: 12px 0; 
            padding: 8px; border-bottom: 1px solid rgba(0, 255, 65, 0.2);
            font-size: 1.1em;
        }
        .metric-value { 
            font-weight: bold; color: #ffffff;
            font-family: 'Monaco', monospace;
        }
        .status-good { color: #00ff41; }
        .status-warning { color: #ffaa00; }
        .status-error { color: #ff4444; }
        .realtime-indicator { 
            position: fixed; top: 20px; right: 20px; 
            background: #00ff41; color: #000; padding: 12px 18px; 
            border-radius: 10px; font-size: 14px; font-weight: bold;
            animation: pulse 1s infinite; z-index: 1000;
        }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.05); }
            100% { opacity: 1; transform: scale(1); }
        }
        .update-flash {
            animation: flash 0.3s ease-in-out;
        }
        @keyframes flash {
            0% { background-color: rgba(0, 255, 65, 0.5); }
            100% { background-color: rgba(0, 255, 65, 0.05); }
        }
    </style>
</head>
<body>
    <div class="realtime-indicator" id="realtime-status">🔄 로딩중</div>
    
    <div class="header">
        <h1>🚀 작동하는 실시간 스타링크 대시보드</h1>
        <p>✅ HTTP 폴링 기반 - 확실한 실시간 업데이트!</p>
    </div>
    
    <div class="status-bar">
        <div>
            <span>📊 업데이트: <span id="update-count" class="status-good">0</span>회</span>
            <span style="margin-left: 30px;">⏱️ 간격: <span id="interval">0</span>ms</span>
        </div>
        <div>
            <span>🔄 폴링: <span id="polling-status" class="status-good">정상</span></span>
            <span style="margin-left: 30px;">⌚ 서버시간: <span id="server-time">--:--:--</span></span>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>🛰️ 기본 정보</h3>
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
                <span>마지막 업데이트:</span>
                <span id="timestamp" class="metric-value">-</span>
            </div>
        </div>
        
        <div class="card">
            <h3>🌐 네트워크 성능</h3>
            <div class="metric">
                <span>다운로드 속도:</span>
                <span id="download-speed" class="metric-value">0 Mbps</span>
            </div>
            <div class="metric">
                <span>업로드 속도:</span>
                <span id="upload-speed" class="metric-value">0 Mbps</span>
            </div>
            <div class="metric">
                <span>Ping 지연시간:</span>
                <span id="ping-latency" class="metric-value">0 ms</span>
            </div>
            <div class="metric">
                <span>패킷 드롭율:</span>
                <span id="drop-rate" class="metric-value">0%</span>
            </div>
        </div>
        
        <div class="card">
            <h3>📡 디시 방향 정보</h3>
            <div class="metric">
                <span>방위각:</span>
                <span id="azimuth" class="metric-value">0°</span>
            </div>
            <div class="metric">
                <span>고도각:</span>
                <span id="elevation" class="metric-value">0°</span>
            </div>
            <div class="metric">
                <span>GPS 위성 수:</span>
                <span id="gps-sats" class="metric-value">0</span>
            </div>
            <div class="metric">
                <span>장애물 비율:</span>
                <span id="obstruction" class="metric-value">0%</span>
            </div>
        </div>
        
        <div class="card">
            <h3>⚡ 실시간 통계</h3>
            <div class="metric">
                <span>총 수집 횟수:</span>
                <span id="total-updates" class="metric-value status-good">0</span>
            </div>
            <div class="metric">
                <span>실제 간격:</span>
                <span id="actual-interval" class="metric-value">0 ms</span>
            </div>
            <div class="metric">
                <span>수집 방식:</span>
                <span class="metric-value">HTTP 폴링</span>
            </div>
            <div class="metric">
                <span>데이터 소스:</span>
                <span class="metric-value">CSV 파일</span>
            </div>
        </div>
    </div>

    <script>
        let updateCount = 0;
        let lastUpdateTime = Date.now();
        let pollCount = 0;
        
        function updateData(data) {
            if (!data) return;
            
            updateCount++;
            const now = Date.now();
            const actualInterval = now - lastUpdateTime;
            lastUpdateTime = now;
            
            // 플래시 효과
            document.querySelectorAll('.card').forEach(card => {
                card.classList.add('update-flash');
                setTimeout(() => card.classList.remove('update-flash'), 300);
            });
            
            // 데이터 업데이트
            document.getElementById('update-count').textContent = data.update_count;
            document.getElementById('interval').textContent = Math.round(data.interval_ms);
            document.getElementById('device-id').textContent = data.device_id || 'unknown';
            document.getElementById('dish-state').textContent = data.state || 'ERROR';
            document.getElementById('uptime').textContent = data.uptime + '초';
            document.getElementById('timestamp').textContent = data.timestamp.split('T')[1].split('.')[0];
            
            document.getElementById('download-speed').textContent = data.download_speed_mbps + ' Mbps';
            document.getElementById('upload-speed').textContent = data.upload_speed_mbps + ' Mbps';
            document.getElementById('ping-latency').textContent = data.ping_latency + ' ms';
            document.getElementById('drop-rate').textContent = (data.drop_rate * 100).toFixed(2) + '%';
            
            document.getElementById('azimuth').textContent = data.direction_azimuth.toFixed(1) + '°';
            document.getElementById('elevation').textContent = data.direction_elevation.toFixed(1) + '°';
            document.getElementById('gps-sats').textContent = data.gps_sats;
            document.getElementById('obstruction').textContent = (data.obstruction * 100).toFixed(2) + '%';
            
            document.getElementById('total-updates').textContent = data.update_count;
            document.getElementById('actual-interval').textContent = actualInterval.toFixed(0) + ' ms';
            document.getElementById('server-time').textContent = data.server_time;
            
            // 상태 표시기 업데이트
            document.getElementById('realtime-status').innerHTML = 
                `🟢 업데이트 ${updateCount} (${actualInterval.toFixed(0)}ms)`;
            
            document.getElementById('polling-status').textContent = '정상';
            document.getElementById('polling-status').className = 'status-good';
        }
        
        function fetchData() {
            pollCount++;
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    updateData(data);
                })
                .catch(error => {
                    console.error('데이터 가져오기 실패:', error);
                    document.getElementById('polling-status').textContent = '오류';
                    document.getElementById('polling-status').className = 'status-error';
                    document.getElementById('realtime-status').innerHTML = '🔴 연결 오류';
                });
        }
        
        // 1초마다 폴링
        setInterval(fetchData, 1000);
        
        // 초기 데이터 로드
        fetchData();
        
        console.log('🚀 HTTP 폴링 기반 실시간 대시보드 시작');
    </script>
</body>
</html>
    ''')

@app.route('/api/data')
def get_data():
    """API 엔드포인트"""
    data = get_latest_csv_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'No data available'}), 404

if __name__ == '__main__':
    print("🚀 HTTP 폴링 기반 실시간 대시보드 시작")
    print("📡 URL: http://localhost:8890")
    print("✅ CSV 파일에서 직접 데이터를 읽어 실시간 표시")
    app.run(host='0.0.0.0', port=8890, debug=False)