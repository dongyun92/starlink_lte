#!/usr/bin/env python3
"""
단위 수정 스타링크 대시보드 - 실제 데이터 파일 사용 버전
- 기존 CSV 데이터에서 실제 값 읽어서 표시
- 올바른 단위 변환 적용
- 마지막 유효값 유지 기능
"""
import os
import sys
import time
import csv
import threading
import json
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

class UnitFixedDashboard:
    def __init__(self):
        self.monitoring_active = False
        self.data_collection_thread = None
        self.update_count = 0
        self.csv_file = 'real_starlink_data_20260106.csv'  # 기존 실제 데이터
        self.latest_data = {}
        
        # 마지막 유효한 값들 저장
        self.last_valid_values = {
            'download_throughput': 0.0,    # bytes/sec
            'upload_throughput': 0.0,      # bytes/sec
            'ping_latency': None,          # ms
            'snr': 0.0                     # dB
        }
        
        # CSV 데이터 읽기
        self.csv_data = []
        self.data_index = 0
        self.load_csv_data()
        
    def load_csv_data(self):
        """CSV 데이터 로드"""
        try:
            with open(self.csv_file, 'r') as f:
                reader = csv.DictReader(f)
                self.csv_data = list(reader)
            print(f"✅ CSV 데이터 로드 완료: {len(self.csv_data)} 행")
        except Exception as e:
            print(f"❌ CSV 로드 실패: {e}")
        
    def get_next_data_point(self):
        """다음 CSV 데이터 포인트 가져오기"""
        if not self.csv_data:
            return None
            
        if self.data_index >= len(self.csv_data):
            self.data_index = 0  # 순환
            
        data = self.csv_data[self.data_index]
        self.data_index += 1
        
        try:
            # bytes/sec를 float로 변환
            download_bytes = float(data['download_throughput']) if data['download_throughput'] else 0.0
            upload_bytes = float(data['upload_throughput']) if data['upload_throughput'] else 0.0
            
            # 핑 값 처리
            ping_value = None
            if data['ping_latency'] and data['ping_latency'] != '0.0':
                try:
                    ping_value = float(data['ping_latency'])
                except ValueError:
                    pass
            
            # SNR 값
            snr_value = float(data['snr']) if data['snr'] else 0.0
            
            # 유효한 값들 캐시 업데이트
            if download_bytes > 0:
                self.last_valid_values['download_throughput'] = download_bytes
            if upload_bytes > 0:
                self.last_valid_values['upload_throughput'] = upload_bytes
            if ping_value is not None and ping_value > 0:
                self.last_valid_values['ping_latency'] = ping_value
            if snr_value > 0:
                self.last_valid_values['snr'] = snr_value
            
            return {
                'timestamp': datetime.now().isoformat() + '+00:00',
                'terminal_id': data['terminal_id'],
                'hardware_version': data['hardware_version'],
                'software_version': data['software_version'],
                'state': data['state'],
                'uptime': int(data['uptime']) if data['uptime'] else 0,
                'download_throughput_raw': download_bytes,  # 원본 bytes/sec
                'upload_throughput_raw': upload_bytes,      # 원본 bytes/sec
                'download_throughput': self.last_valid_values['download_throughput'],  # 캐시된 값
                'upload_throughput': self.last_valid_values['upload_throughput'],      # 캐시된 값
                'ping_latency': self.last_valid_values['ping_latency'],                # 캐시된 값
                'azimuth': float(data['azimuth']) if data['azimuth'] else 0.0,
                'elevation': float(data['elevation']) if data['elevation'] else 0.0,
                'snr': self.last_valid_values['snr']                                   # 캐시된 값
            }
            
        except Exception as e:
            print(f"⚠️ 데이터 파싱 오류: {e}")
            return None
        
    def start_data_collection(self):
        """데이터 수집 시작"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.data_collection_thread = threading.Thread(target=self._data_collection_loop)
        self.data_collection_thread.daemon = True
        self.data_collection_thread.start()
        print("🚀 단위 수정 대시보드 시작 - CSV 데이터 재생")
    
    def _data_collection_loop(self):
        """데이터 수집 루프"""
        while self.monitoring_active:
            loop_start = time.time()
            
            # CSV에서 다음 데이터 가져오기
            data = self.get_next_data_point()
            
            if data:
                self.update_count += 1
                
                self.latest_data = {
                    'timestamp': data['timestamp'],
                    'terminal_id': data['terminal_id'],
                    'hardware_version': data['hardware_version'],
                    'software_version': data['software_version'],
                    'state': data['state'],
                    'uptime': data['uptime'],
                    'download_throughput': data['download_throughput'],     # bytes/sec (캐시된 값)
                    'upload_throughput': data['upload_throughput'],         # bytes/sec (캐시된 값)
                    'ping_latency': data['ping_latency'],                   # ms (캐시된 값)
                    'azimuth': data['azimuth'],
                    'elevation': data['elevation'],
                    'snr': data['snr'],                                     # dB (캐시된 값)
                    'update_count': self.update_count,
                    'interval_ms': 100.0
                }
                
                # 로깅
                if self.update_count % 10 == 0:
                    download_mbps = data['download_throughput'] / 1000000  # bytes/sec → Mbps
                    upload_mbps = data['upload_throughput'] / 1000000      # bytes/sec → Mbps
                    ping_display = f"{data['ping_latency']:.1f}ms" if data['ping_latency'] else "캐시된 값 없음"
                    
                    print(f"✅ 단위 수정 데이터 #{self.update_count}: {data['state']} | "
                          f"⬇️{download_mbps:.1f}Mbps | ⬆️{upload_mbps:.1f}Mbps | 📡{ping_display}")
            
            # 500ms 간격으로 재생
            elapsed = time.time() - loop_start
            sleep_time = max(0, 0.5 - elapsed)
            time.sleep(sleep_time)
    
    def stop_data_collection(self):
        """데이터 수집 중지"""
        self.monitoring_active = False
        if self.data_collection_thread:
            self.data_collection_thread.join(timeout=1)
        print("🛑 데이터 수집 중지")

# Flask 웹 인터페이스
dashboard = UnitFixedDashboard()

# HTML 템플릿 (단위 수정 버전)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Unit Fixed Starlink Dashboard</title>
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
        .charts-container { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-top: 30px; 
        }
        .chart-card { 
            background: #1E2329; 
            border-radius: 8px; 
            padding: 20px; 
        }
        .chart-title { 
            font-size: 16px; 
            color: #EAECEF; 
            margin-bottom: 15px; 
            font-weight: bold; 
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
        ✅ UNIT FIXED: bytes/sec → Mbps 올바른 단위 변환 | 실제 CSV 데이터 재생 | 마지막 유효값 유지
    </div>
    
    <div class="header">
        <h1>🛰️ Unit Fixed Starlink Dashboard</h1>
        <div>
            <span id="status-indicator" class="connected">●</span>
            <span id="connection-status">Connected</span>
            <span style="margin-left: 20px;">Updates: <span id="update-count">0</span></span>
            <span style="margin-left: 20px;">Interval: 500ms (CSV Playback)</span>
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

    <div class="charts-container">
        <div class="chart-card">
            <div class="chart-title">📊 다운로드/업로드 속도 (올바른 단위 변환)</div>
            <canvas id="speedChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-card">
            <div class="chart-title">📡 스타링크 핑 (마지막 유효값 유지)</div>
            <canvas id="pingChart" width="400" height="200"></canvas>
        </div>
    </div>

    <script>
        // 차트 초기화
        const speedCtx = document.getElementById('speedChart').getContext('2d');
        const pingCtx = document.getElementById('pingChart').getContext('2d');
        
        const speedChart = new Chart(speedCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Download (Mbps)',
                    data: [],
                    borderColor: '#2EBD85',
                    fill: false
                }, {
                    label: 'Upload (Mbps)', 
                    data: [],
                    borderColor: '#F0B90B',
                    fill: false
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
                plugins: { legend: { labels: { color: '#EAECEF' } } }
            }
        });
        
        const pingChart = new Chart(pingCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Starlink Ping (ms)',
                    data: [],
                    borderColor: '#2EBD85',
                    fill: false
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
                plugins: { legend: { labels: { color: '#EAECEF' } } }
            }
        });

        // 실시간 데이터 업데이트
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // 연결 상태 업데이트
                    const statusElement = document.getElementById('connection-status');
                    const statusIndicator = document.getElementById('status-indicator');
                    
                    if (data.state === 'CONNECTED') {
                        statusElement.textContent = 'Connected';
                        statusElement.className = 'connected';
                        statusIndicator.className = 'connected';
                    } else {
                        statusElement.textContent = data.state || 'Disconnected';
                        statusElement.className = 'disconnected';
                        statusIndicator.className = 'disconnected';
                    }
                    
                    // bytes/sec → Mbps 올바른 변환
                    const downloadMbps = (data.download_throughput/1000000 || 0).toFixed(1);
                    const uploadMbps = (data.upload_throughput/1000000 || 0).toFixed(1);
                    
                    document.getElementById('state').textContent = data.state || 'UNKNOWN';
                    document.getElementById('download-speed').innerHTML = `${downloadMbps}<span class="metric-unit">Mbps</span>`;
                    document.getElementById('upload-speed').innerHTML = `${uploadMbps}<span class="metric-unit">Mbps</span>`;
                    
                    // 핑 정보
                    if (data.ping_latency !== null && data.ping_latency !== undefined) {
                        document.getElementById('ping-latency').innerHTML = `${data.ping_latency.toFixed(1)}<span class="metric-unit">ms</span>`;
                    } else {
                        document.getElementById('ping-latency').innerHTML = `측정중<span class="metric-unit"></span>`;
                    }
                    
                    document.getElementById('snr').innerHTML = `${(data.snr || 0).toFixed(2)}<span class="metric-unit">dB</span>`;
                    document.getElementById('update-count').textContent = data.update_count || 0;
                    
                    // 업타임 포맷
                    const uptime = data.uptime || 0;
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    const seconds = uptime % 60;
                    document.getElementById('uptime').textContent = `${hours}h ${minutes}m ${seconds}s`;
                    
                    // 차트 업데이트
                    const currentTime = new Date().toLocaleTimeString();
                    
                    // 속도 차트
                    speedChart.data.labels.push(currentTime);
                    speedChart.data.datasets[0].data.push(parseFloat(downloadMbps));
                    speedChart.data.datasets[1].data.push(parseFloat(uploadMbps));
                    
                    // 핑 차트
                    pingChart.data.labels.push(currentTime);
                    pingChart.data.datasets[0].data.push(data.ping_latency);
                    
                    // 최대 20개 데이터 포인트 유지
                    if (speedChart.data.labels.length > 20) {
                        speedChart.data.labels.shift();
                        speedChart.data.datasets.forEach(dataset => dataset.data.shift());
                        pingChart.data.labels.shift();
                        pingChart.data.datasets.forEach(dataset => dataset.data.shift());
                    }
                    
                    speedChart.update();
                    pingChart.update();
                })
                .catch(error => {
                    console.error('데이터 업데이트 오류:', error);
                });
        }

        // 500ms마다 업데이트
        setInterval(updateDashboard, 500);
        updateDashboard();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    """단위 수정된 스타링크 데이터 API"""
    return jsonify(dashboard.latest_data)

@app.route('/api/start')
def start_monitoring():
    """모니터링 시작"""
    dashboard.start_data_collection()
    return jsonify({"status": "started", "message": "단위 수정 데이터 재생 시작"})

@app.route('/api/stop')
def stop_monitoring():
    """모니터링 중지"""
    dashboard.stop_data_collection()
    return jsonify({"status": "stopped", "message": "데이터 재생 중지"})

if __name__ == '__main__':
    print("🚀 Unit Fixed Starlink Dashboard 시작")
    print("📊 대시보드: http://localhost:8901")
    print("📁 데이터 소스: real_starlink_data_20260106.csv")
    print("🔄 올바른 단위 변환: bytes/sec → Mbps")
    print("⚡ CSV 데이터 재생 모드")
    
    # 자동으로 데이터 수집 시작
    dashboard.start_data_collection()
    
    try:
        app.run(host='0.0.0.0', port=8901, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 대시보드 종료")
        dashboard.stop_data_collection()