#!/usr/bin/env python3
"""
실제 스타링크 192.168.100.1 gRPC 연결 대시보드
- 시뮬레이션 없음, 실제 데이터만 사용
- starlink-grpc-tools 통합
- 100ms 고속 데이터 수집
- 포트 8899 고정
"""
import os
import sys
import time
import csv
import subprocess
import threading
import json
import re
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

class RealStarlinkDashboard:
    def __init__(self):
        self.monitoring_active = False
        self.data_collection_thread = None
        self.update_count = 0
        self.csv_file = 'real_starlink_data_20260106.csv'
        self.latest_data = {}
        self.grpc_tools_path = 'starlink-grpc-tools'
        
        # CSV 헤더 초기화
        self.init_csv_file()
        
    def init_csv_file(self):
        """CSV 파일 헤더 생성"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'terminal_id', 'hardware_version', 'software_version',
                    'state', 'uptime', 'download_throughput', 'upload_throughput', 'ping_latency',
                    'update_count', 'interval_ms', 'azimuth', 'elevation', 'snr'
                ])
        
    def collect_real_starlink_data(self):
        """실제 192.168.100.1에서 gRPC로 데이터 수집"""
        try:
            # starlink-grpc-tools의 dish_grpc_text.py 실행
            cmd = [
                'python', 'dish_grpc_text.py',
                '-t', '0.1',  # 100ms 간격
                'status'
            ]
            
            # grpc_env 환경에서 실행
            env = os.environ.copy()
            env['PATH'] = f"{os.path.join(self.grpc_tools_path, 'grpc_env/bin')}:{env['PATH']}"
            
            # 프로세스 실행 - 한 줄만 읽기
            process = subprocess.Popen(
                cmd,
                cwd=self.grpc_tools_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # 타임아웃과 함께 한 줄 읽기
            try:
                output_line = process.stdout.readline().strip()
                process.terminate()
                
                if output_line and not output_line.startswith('usage:'):
                    return self.parse_grpc_output(output_line)
                    
            except Exception as e:
                print(f"⚠️ gRPC 데이터 읽기 오류: {e}")
                process.terminate()
                
        except Exception as e:
            print(f"❌ 실제 gRPC 연결 오류: {e}")
            
        return None
        
    def parse_grpc_output(self, line):
        """gRPC 출력 파싱"""
        try:
            # CSV 형태의 출력 파싱
            parts = line.split(',')
            if len(parts) >= 20:
                return {
                    'timestamp': parts[0],
                    'terminal_id': parts[1],
                    'hardware_version': parts[2],
                    'software_version': parts[3],
                    'state': parts[4],
                    'uptime': int(parts[5]) if parts[5] else 0,
                    'download_throughput': float(parts[8]) if parts[8] else 0.0,
                    'upload_throughput': float(parts[9]) if parts[9] else 0.0,
                    'ping_latency': float(parts[10]) if parts[10] else 0.0,
                    'snr': float(parts[11]) if parts[11] else 0.0,
                    'azimuth': float(parts[16]) if parts[16] else 0.0,
                    'elevation': float(parts[17]) if parts[17] else 0.0,
                }
        except Exception as e:
            print(f"⚠️ 데이터 파싱 오류: {e}")
            
        return None
        
    def start_data_collection(self):
        """실제 데이터 수집 시작"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.data_collection_thread = threading.Thread(target=self._real_data_collection_loop)
        self.data_collection_thread.daemon = True
        self.data_collection_thread.start()
        print("🚀 실제 스타링크 데이터 수집 시작")
    
    def _real_data_collection_loop(self):
        """실제 스타링크 데이터 수집 루프"""
        while self.monitoring_active:
            loop_start = time.time()
            
            # 실제 gRPC 데이터 수집
            real_data = self.collect_real_starlink_data()
            
            if real_data:
                self.update_count += 1
                current_time = datetime.now().isoformat() + '+00:00'
                
                # 실제 데이터로 최신 데이터 업데이트
                self.latest_data = {
                    'timestamp': current_time,
                    'terminal_id': real_data['terminal_id'],
                    'hardware_version': real_data['hardware_version'],
                    'software_version': real_data['software_version'],
                    'state': real_data['state'],
                    'uptime': real_data['uptime'],
                    'download_throughput': real_data['download_throughput'],
                    'upload_throughput': real_data['upload_throughput'],
                    'ping_latency': real_data['ping_latency'],
                    'update_count': self.update_count,
                    'interval_ms': 100.0,
                    'azimuth': real_data['azimuth'],
                    'elevation': real_data['elevation'],
                    'snr': real_data['snr']
                }
                
                # CSV에 실제 데이터 저장
                self.save_data_to_csv(self.latest_data)
                
                # 로깅 (1초마다)
                if self.update_count % 10 == 0:
                    print(f"✅ 실제 데이터 #{self.update_count}: {real_data['state']} | "
                          f"⬇️{real_data['download_throughput']/1000:.1f}Kbps | "
                          f"⬆️{real_data['upload_throughput']/1000:.1f}Kbps | "
                          f"📡{real_data['ping_latency']:.1f}ms")
            else:
                print(f"⚠️ 데이터 수집 실패 #{self.update_count}")
                
            # 100ms 간격 유지
            elapsed = time.time() - loop_start
            sleep_time = max(0, 0.1 - elapsed)
            time.sleep(sleep_time)
    
    def save_data_to_csv(self, data):
        """CSV에 데이터 저장"""
        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data['timestamp'],
                    data['terminal_id'],
                    data['hardware_version'], 
                    data['software_version'],
                    data['state'],
                    data['uptime'],
                    data['download_throughput'],
                    data['upload_throughput'],
                    data['ping_latency'],
                    data['update_count'],
                    data['interval_ms'],
                    data['azimuth'],
                    data['elevation'],
                    data['snr']
                ])
        except Exception as e:
            print(f"CSV 저장 오류: {e}")
    
    def stop_data_collection(self):
        """데이터 수집 중지"""
        self.monitoring_active = False
        if self.data_collection_thread:
            self.data_collection_thread.join(timeout=2)
        print("🛑 데이터 수집 중지됨")

# 글로벌 대시보드 인스턴스
dashboard = RealStarlinkDashboard()

@app.route('/')
def dashboard_page():
    """메인 대시보드 페이지"""
    return render_template_string("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🛰️ Real Starlink Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f1419; color: #fff; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 20px; border-radius: 15px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header .subtitle { opacity: 0.8; font-size: 1.1em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #1f2937; padding: 20px; border-radius: 15px; border-left: 4px solid #3b82f6; }
        .card h3 { color: #60a5fa; margin-bottom: 15px; font-size: 1.3em; }
        .metric { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; padding: 10px; background: #374151; border-radius: 8px; }
        .metric-label { font-weight: 500; }
        .metric-value { font-weight: bold; font-size: 1.1em; }
        .status-connected { color: #10b981; }
        .status-error { color: #ef4444; }
        .chart-container { background: #1f2937; padding: 20px; border-radius: 15px; border-left: 4px solid #10b981; }
        .chart-wrapper { height: 400px; }
        .real-badge { background: linear-gradient(45deg, #10b981, #059669); color: white; padding: 4px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold; }
        .ping { color: #fbbf24; }
        .download { color: #10b981; }
        .upload { color: #3b82f6; }
        footer { text-align: center; margin-top: 30px; padding: 20px; opacity: 0.7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛰️ Real Starlink Monitor</h1>
            <div class="subtitle">실제 192.168.100.1 gRPC 연결 • 100ms 초고속 수집 <span class="real-badge">REAL DATA</span></div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📡 연결 상태</h3>
                <div class="metric">
                    <span class="metric-label">상태:</span>
                    <span class="metric-value" id="status">연결 중...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">업타임:</span>
                    <span class="metric-value" id="uptime">0s</span>
                </div>
                <div class="metric">
                    <span class="metric-label">터미널 ID:</span>
                    <span class="metric-value" id="terminal-id">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">업데이트:</span>
                    <span class="metric-value" id="update-count">0</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🌐 네트워크 성능</h3>
                <div class="metric">
                    <span class="metric-label">다운로드:</span>
                    <span class="metric-value download" id="download">0 Mbps</span>
                </div>
                <div class="metric">
                    <span class="metric-label">업로드:</span>
                    <span class="metric-value upload" id="upload">0 Mbps</span>
                </div>
                <div class="metric">
                    <span class="metric-label">핑:</span>
                    <span class="metric-value ping" id="ping">0 ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">신호 강도:</span>
                    <span class="metric-value" id="snr">0 dB</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 위치 정보</h3>
                <div class="metric">
                    <span class="metric-label">방위각:</span>
                    <span class="metric-value" id="azimuth">0°</span>
                </div>
                <div class="metric">
                    <span class="metric-label">고도각:</span>
                    <span class="metric-value" id="elevation">0°</span>
                </div>
                <div class="metric">
                    <span class="metric-label">하드웨어:</span>
                    <span class="metric-value" id="hardware">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">소프트웨어:</span>
                    <span class="metric-value" id="software">-</span>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>📈 실시간 성능 차트</h3>
            <div class="chart-wrapper">
                <canvas id="performanceChart"></canvas>
            </div>
        </div>
        
        <footer>
            <p>Real Starlink Monitor v2.0 • 실제 gRPC 데이터 • 시뮬레이션 없음</p>
        </footer>
    </div>

    <script>
        // Chart.js 설정
        const ctx = document.getElementById('performanceChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '다운로드 (Mbps)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                }, {
                    label: '업로드 (Mbps)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }, {
                    label: '핑 (ms)',
                    data: [],
                    borderColor: '#fbbf24',
                    backgroundColor: 'rgba(251, 191, 36, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '실시간 네트워크 성능 (100ms 간격)',
                        color: '#fff'
                    },
                    legend: {
                        labels: { color: '#fff' }
                    }
                },
                scales: {
                    x: {
                        grid: { color: '#374151' },
                        ticks: { color: '#9ca3af', maxTicksLimit: 10 }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: '#374151' },
                        ticks: { color: '#9ca3af' },
                        title: { display: true, text: 'Mbps', color: '#fff' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#9ca3af' },
                        title: { display: true, text: 'ms', color: '#fff' }
                    }
                },
                animation: { duration: 0 }
            }
        });

        // 데이터 업데이트 함수
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // 상태 업데이트
                    document.getElementById('status').textContent = data.state || 'ERROR';
                    document.getElementById('status').className = data.state === 'CONNECTED' ? 
                        'metric-value status-connected' : 'metric-value status-error';
                    
                    // 네트워크 정보
                    document.getElementById('uptime').textContent = formatUptime(data.uptime || 0);
                    document.getElementById('terminal-id').textContent = data.terminal_id || '-';
                    document.getElementById('update-count').textContent = data.update_count || 0;
                    
                    // 성능 지표
                    document.getElementById('download').textContent = 
                        ((data.download_throughput || 0) / 1000000).toFixed(2) + ' Mbps';
                    document.getElementById('upload').textContent = 
                        ((data.upload_throughput || 0) / 1000000).toFixed(2) + ' Mbps';
                    document.getElementById('ping').textContent = 
                        (data.ping_latency || 0).toFixed(1) + ' ms';
                    document.getElementById('snr').textContent = 
                        (data.snr || 0).toFixed(1) + ' dB';
                    
                    // 위치 정보
                    document.getElementById('azimuth').textContent = (data.azimuth || 0).toFixed(1) + '°';
                    document.getElementById('elevation').textContent = (data.elevation || 0).toFixed(1) + '°';
                    document.getElementById('hardware').textContent = data.hardware_version || '-';
                    document.getElementById('software').textContent = data.software_version || '-';
                    
                    // 차트 업데이트
                    updateChart(data);
                })
                .catch(error => {
                    console.error('데이터 업데이트 오류:', error);
                });
        }

        function updateChart(data) {
            const now = new Date().toLocaleTimeString();
            chart.data.labels.push(now);
            
            // 데이터 추가
            chart.data.datasets[0].data.push((data.download_throughput || 0) / 1000000);
            chart.data.datasets[1].data.push((data.upload_throughput || 0) / 1000000);
            chart.data.datasets[2].data.push(data.ping_latency || 0);
            
            // 최대 50개 데이터 포인트만 유지
            if (chart.data.labels.length > 50) {
                chart.data.labels.shift();
                chart.data.datasets.forEach(dataset => dataset.data.shift());
            }
            
            chart.update('none');
        }

        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            return `${hours}h ${minutes}m ${secs}s`;
        }

        // 100ms마다 업데이트
        updateDashboard();
        setInterval(updateDashboard, 100);
    </script>
</body>
</html>
    """)

@app.route('/api/data')
def get_data():
    """API 엔드포인트 - 최신 실제 데이터 반환"""
    return jsonify(dashboard.latest_data)

if __name__ == '__main__':
    # 데이터 수집 시작
    dashboard.start_data_collection()
    
    print("🚀 실제 스타링크 대시보드 시작")
    print("📡 포트: 8899")
    print("🌐 URL: http://localhost:8899")
    print("🔗 실제 192.168.100.1 gRPC 연결")
    print("⚡ 100ms 간격 실시간 업데이트")
    print("🚫 시뮬레이션 없음 - 실제 데이터만")
    
    try:
        app.run(host='0.0.0.0', port=8899, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 서버 종료 중...")
        dashboard.stop_data_collection()
        print("✅ 정상 종료됨")