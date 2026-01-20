#!/usr/bin/env python3
"""
실제 데이터 재생 대시보드 - CSV 파일의 실제 데이터를 사용
포트 8899 고정, 단위 변환 ÷125,000 적용
"""
import pandas as pd
import time
import threading
import json
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

class WorkingDataDashboard:
    def __init__(self):
        self.csv_file = '/Users/dykim/dev/starlink/real_starlink_data_20260106.csv'
        self.current_index = 0
        self.data = None
        self.latest_data = {}
        self.monitoring_active = False
        self.load_csv_data()
        
    def load_csv_data(self):
        """CSV 데이터 로드"""
        try:
            self.data = pd.read_csv(self.csv_file)
            print(f"✅ CSV 데이터 로드: {len(self.data)} 행")
            # 샘플 데이터 확인
            sample = self.data.iloc[0]
            print(f"샘플 다운로드: {sample['download_throughput']} bytes/sec -> {sample['download_throughput']/125000:.1f} Mbps")
            print(f"샘플 업로드: {sample['upload_throughput']} bytes/sec -> {sample['upload_throughput']/125000:.1f} Mbps")
        except Exception as e:
            print(f"❌ CSV 로드 실패: {e}")
            
    def start_data_playback(self):
        """CSV 데이터 재생 시작"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        print("🚀 실제 데이터 재생 시작")
        
    def _playback_loop(self):
        """CSV 데이터를 순환하며 재생"""
        while self.monitoring_active:
            if self.data is not None and len(self.data) > 0:
                # 현재 인덱스의 데이터 가져오기
                row = self.data.iloc[self.current_index]
                
                self.latest_data = {
                    'timestamp': datetime.now().isoformat(),
                    'terminal_id': row['terminal_id'],
                    'hardware_version': row['hardware_version'],
                    'software_version': row['software_version'],
                    'state': row['state'],
                    'uptime': int(row['uptime']),
                    'download_throughput': float(row['download_throughput']),
                    'upload_throughput': float(row['upload_throughput']),
                    'ping_latency': float(row['ping_latency']) if pd.notna(row['ping_latency']) else None,
                    'snr': float(row['snr']) if pd.notna(row['snr']) else 0,
                    'azimuth': float(row['azimuth']) if pd.notna(row['azimuth']) else 0,
                    'elevation': float(row['elevation']) if pd.notna(row['elevation']) else 0,
                    'current_index': self.current_index,
                    'total_rows': len(self.data)
                }
                
                # 다음 인덱스로 이동 (순환)
                self.current_index = (self.current_index + 1) % len(self.data)
                
                print(f"📊 재생 #{self.current_index}: "
                      f"⬇️{self.latest_data['download_throughput']/125000:.1f}Mbps "
                      f"⬆️{self.latest_data['upload_throughput']/125000:.1f}Mbps")
            
            time.sleep(2)  # 2초마다 업데이트

# Flask 웹 인터페이스
dashboard = WorkingDataDashboard()

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Working Data Dashboard - Real CSV Data</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
            margin: 0; 
            background: #0B0E11; 
            color: #EAECEF; 
            padding: 20px;
        }
        .header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 30px; 
            padding: 20px; 
            background: #1E2329; 
            border-radius: 8px; 
        }
        .status-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .status-card { 
            background: #1E2329; 
            border-radius: 8px; 
            padding: 20px; 
            border-left: 4px solid #F0B90B; 
        }
        .metric-title { 
            font-size: 14px; 
            color: #848E9C; 
            margin-bottom: 8px; 
        }
        .metric-value { 
            font-size: 24px; 
            font-weight: bold; 
            color: #EAECEF; 
        }
        .metric-unit { 
            font-size: 16px; 
            color: #848E9C; 
            margin-left: 5px; 
        }
        .connected { color: #2EBD85; }
        .disconnected { color: #F6465D; }
        .disclaimer { 
            background: #2A2E39; 
            border: 1px solid #2EBD85; 
            border-radius: 8px; 
            padding: 15px; 
            margin-bottom: 20px; 
            color: #2EBD85; 
            text-align: center; 
            font-weight: bold; 
        }
    </style>
</head>
<body>
    <div class="disclaimer">
        ✅ WORKING: 실제 CSV 데이터 재생 | 올바른 단위 변환 (÷125,000) | 포트 8899
    </div>
    
    <div class="header">
        <h1>🛰️ Working Data Dashboard</h1>
        <div>
            <span id="status-indicator" class="connected">●</span>
            <span id="connection-status">Playing Data</span>
            <span style="margin-left: 20px;">Row: <span id="current-index">0</span>/<span id="total-rows">0</span></span>
        </div>
    </div>

    <div class="status-grid">
        <div class="status-card">
            <div class="metric-title">연결 상태</div>
            <div class="metric-value" id="state">CONNECTING</div>
        </div>
        
        <div class="status-card">
            <div class="metric-title">다운로드 속도</div>
            <div class="metric-value" id="download-speed">0.0<span class="metric-unit">Mbps</span></div>
        </div>
        
        <div class="status-card">
            <div class="metric-title">업로드 속도</div>
            <div class="metric-value" id="upload-speed">0.0<span class="metric-unit">Mbps</span></div>
        </div>
        
        <div class="status-card">
            <div class="metric-title">스타링크 핑</div>
            <div class="metric-value" id="ping-latency">측정중<span class="metric-unit"></span></div>
        </div>
        
        <div class="status-card">
            <div class="metric-title">신호 강도 (SNR)</div>
            <div class="metric-value" id="snr">0.0<span class="metric-unit">dB</span></div>
        </div>
        
        <div class="status-card">
            <div class="metric-title">업타임</div>
            <div class="metric-value" id="uptime">0h 0m 0s</div>
        </div>
    </div>

    <script>
        // 실시간 데이터 업데이트
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    console.log('Data received:', data);
                    
                    // 연결 상태
                    document.getElementById('state').textContent = data.state || 'UNKNOWN';
                    
                    // 속도 (올바른 단위 변환: ÷125,000)
                    const downloadMbps = (data.download_throughput || 0) / 125000;
                    const uploadMbps = (data.upload_throughput || 0) / 125000;
                    
                    document.getElementById('download-speed').innerHTML = `${downloadMbps.toFixed(1)}<span class="metric-unit">Mbps</span>`;
                    document.getElementById('upload-speed').innerHTML = `${uploadMbps.toFixed(1)}<span class="metric-unit">Mbps</span>`;
                    
                    // 핑
                    if (data.ping_latency !== null && data.ping_latency !== undefined) {
                        document.getElementById('ping-latency').innerHTML = `${data.ping_latency.toFixed(1)}<span class="metric-unit">ms</span>`;
                    } else {
                        document.getElementById('ping-latency').innerHTML = `측정중<span class="metric-unit"></span>`;
                    }
                    
                    // SNR
                    document.getElementById('snr').innerHTML = `${(data.snr || 0).toFixed(1)}<span class="metric-unit">dB</span>`;
                    
                    // 업타임
                    const uptime = data.uptime || 0;
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    const seconds = uptime % 60;
                    document.getElementById('uptime').textContent = `${hours}h ${minutes}m ${seconds}s`;
                    
                    // 재생 정보
                    document.getElementById('current-index').textContent = data.current_index || 0;
                    document.getElementById('total-rows').textContent = data.total_rows || 0;
                })
                .catch(error => {
                    console.error('데이터 업데이트 오류:', error);
                });
        }

        // 1초마다 업데이트
        setInterval(updateDashboard, 1000);
        updateDashboard(); // 즉시 첫 업데이트
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    """실제 CSV 데이터 API"""
    return jsonify(dashboard.latest_data)

if __name__ == '__main__':
    print("🚀 Working Data Dashboard 시작 (실제 CSV 데이터)")
    print("📊 대시보드: http://localhost:8899")
    print("📈 실제 속도 데이터 재생")
    
    # 자동으로 데이터 재생 시작
    dashboard.start_data_playback()
    
    try:
        app.run(host='0.0.0.0', port=8899, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 대시보드 종료")
        dashboard.monitoring_active = False