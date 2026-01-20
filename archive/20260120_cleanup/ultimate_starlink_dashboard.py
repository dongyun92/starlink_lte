#!/usr/bin/env python3
"""
Ultimate Starlink Dashboard - 실시간 + 누적통계 + 그래프 완전판
- 실시간 속도 표시 (실제 데이터 재생)
- 누적 사용량 통계
- 실시간 그래프 (Chart.js)
- 포트 8899 고정
"""
import csv
import time
import threading
import subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

class UltimateStarlinkDashboard:
    def __init__(self):
        self.real_data_file = '/Users/dykim/dev/starlink/real_starlink_data_20260106.csv'
        self.current_index = 0
        self.data_rows = []
        self.latest_data = {}
        self.monitoring_active = False
        self.cumulative_stats = {
            'total_download_bytes': 0,
            'total_upload_bytes': 0,
            'session_start': datetime.now(),
            'peak_download_mbps': 0,
            'peak_upload_mbps': 0,
            'avg_ping': 0,
            'total_measurements': 0
        }
        
        # 그래프용 데이터 (최근 20포인트)
        self.chart_data = {
            'timestamps': [],
            'download_speeds': [],
            'upload_speeds': [],
            'ping_values': []
        }
        
        self.load_real_data()
        
    def load_real_data(self):
        """실제 CSV 데이터 로드"""
        try:
            with open(self.real_data_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.data_rows = list(reader)
            
            print(f"✅ 실제 데이터 로드: {len(self.data_rows)} 행")
            
            # 샘플 데이터 확인
            if self.data_rows:
                sample = self.data_rows[0]
                download_mbps = float(sample['download_throughput']) / 125000
                upload_mbps = float(sample['upload_throughput']) / 125000
                print(f"샘플 다운로드: {download_mbps:.1f} Mbps")
                print(f"샘플 업로드: {upload_mbps:.1f} Mbps")
                
        except Exception as e:
            print(f"❌ 실제 데이터 로드 실패: {e}")
            # 기본 데이터 생성
            self.data_rows = [
                {
                    'terminal_id': 'demo',
                    'hardware_version': 'demo',
                    'software_version': 'demo',
                    'state': 'CONNECTED',
                    'uptime': '12000',
                    'download_throughput': '999989.1875',
                    'upload_throughput': '125000',
                    'ping_latency': '25.5',
                    'snr': '15.2',
                    'azimuth': '45.0',
                    'elevation': '60.0'
                }
            ]
            
    def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("🚀 실시간 모니터링 시작")
        
    def _monitoring_loop(self):
        """실시간 데이터 처리 루프"""
        while self.monitoring_active:
            if self.data_rows:
                # 현재 인덱스의 데이터 가져오기
                row = self.data_rows[self.current_index]
                
                # 데이터 파싱
                download_bytes = float(row.get('download_throughput', 0))
                upload_bytes = float(row.get('upload_throughput', 0))
                ping_ms = float(row['ping_latency']) if row.get('ping_latency') else None
                
                # Mbps 변환 (올바른 공식: ÷125,000)
                download_mbps = download_bytes / 125000
                upload_mbps = upload_bytes / 125000
                
                # 실시간 데이터 업데이트
                self.latest_data = {
                    'timestamp': datetime.now().isoformat(),
                    'terminal_id': row.get('terminal_id', 'unknown'),
                    'hardware_version': row.get('hardware_version', 'unknown'),
                    'software_version': row.get('software_version', 'unknown'),
                    'state': row.get('state', 'UNKNOWN'),
                    'uptime': int(float(row.get('uptime', 0))),
                    'download_throughput_bytes': download_bytes,
                    'upload_throughput_bytes': upload_bytes,
                    'download_mbps': download_mbps,
                    'upload_mbps': upload_mbps,
                    'ping_latency': ping_ms,
                    'snr': float(row.get('snr', 0)),
                    'azimuth': float(row.get('azimuth', 0)),
                    'elevation': float(row.get('elevation', 0)),
                    'current_index': self.current_index,
                    'total_rows': len(self.data_rows)
                }
                
                # 누적 통계 업데이트
                self._update_cumulative_stats(download_bytes, upload_bytes, ping_ms, download_mbps, upload_mbps)
                
                # 그래프 데이터 업데이트
                self._update_chart_data(download_mbps, upload_mbps, ping_ms)
                
                # 로깅
                print(f"📊 #{self.current_index}: ⬇️{download_mbps:.1f}Mbps ⬆️{upload_mbps:.1f}Mbps 📡{ping_ms}ms")
                
                # 다음 데이터로 이동 (순환)
                self.current_index = (self.current_index + 1) % len(self.data_rows)
            
            time.sleep(2)  # 2초마다 업데이트
            
    def _update_cumulative_stats(self, download_bytes, upload_bytes, ping_ms, download_mbps, upload_mbps):
        """누적 통계 업데이트"""
        self.cumulative_stats['total_download_bytes'] += download_bytes * 2  # 2초간격 가정
        self.cumulative_stats['total_upload_bytes'] += upload_bytes * 2
        
        if download_mbps > self.cumulative_stats['peak_download_mbps']:
            self.cumulative_stats['peak_download_mbps'] = download_mbps
            
        if upload_mbps > self.cumulative_stats['peak_upload_mbps']:
            self.cumulative_stats['peak_upload_mbps'] = upload_mbps
            
        self.cumulative_stats['total_measurements'] += 1
        
        if ping_ms is not None:
            current_avg = self.cumulative_stats['avg_ping']
            count = self.cumulative_stats['total_measurements']
            self.cumulative_stats['avg_ping'] = ((current_avg * (count - 1)) + ping_ms) / count
            
    def _update_chart_data(self, download_mbps, upload_mbps, ping_ms):
        """그래프 데이터 업데이트"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # 데이터 추가
        self.chart_data['timestamps'].append(current_time)
        self.chart_data['download_speeds'].append(download_mbps)
        self.chart_data['upload_speeds'].append(upload_mbps)
        self.chart_data['ping_values'].append(ping_ms)
        
        # 최대 20개 포인트 유지
        max_points = 20
        if len(self.chart_data['timestamps']) > max_points:
            self.chart_data['timestamps'] = self.chart_data['timestamps'][-max_points:]
            self.chart_data['download_speeds'] = self.chart_data['download_speeds'][-max_points:]
            self.chart_data['upload_speeds'] = self.chart_data['upload_speeds'][-max_points:]
            self.chart_data['ping_values'] = self.chart_data['ping_values'][-max_points:]
    
    def get_combined_data(self):
        """실시간 + 누적 + 그래프 데이터 결합"""
        session_duration = datetime.now() - self.cumulative_stats['session_start']
        
        return {
            # 실시간 데이터
            'realtime': self.latest_data,
            
            # 누적 통계
            'cumulative': {
                'total_download_gb': self.cumulative_stats['total_download_bytes'] / (1024**3),
                'total_upload_gb': self.cumulative_stats['total_upload_bytes'] / (1024**3),
                'peak_download_mbps': self.cumulative_stats['peak_download_mbps'],
                'peak_upload_mbps': self.cumulative_stats['peak_upload_mbps'],
                'avg_ping': self.cumulative_stats['avg_ping'],
                'session_duration_minutes': session_duration.total_seconds() / 60,
                'total_measurements': self.cumulative_stats['total_measurements']
            },
            
            # 그래프 데이터
            'charts': self.chart_data
        }

# Flask 웹 인터페이스
dashboard = UltimateStarlinkDashboard()

# HTML 템플릿 - 완전판
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Ultimate Starlink Dashboard</title>
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
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .realtime-section {
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 15px;
        }
        .cumulative-section {
            background: #1E2329;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #F0B90B;
        }
        .section-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #F0B90B;
        }
        .status-card { 
            background: #1E2329; 
            border-radius: 8px; 
            padding: 15px; 
            border-left: 4px solid #2EBD85; 
        }
        .cumulative-card {
            background: #2A2E39;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .metric-title { 
            font-size: 12px; 
            color: #848E9C; 
            margin-bottom: 6px; 
        }
        .metric-value { 
            font-size: 20px; 
            font-weight: bold; 
            color: #EAECEF; 
        }
        .metric-unit { 
            font-size: 14px; 
            color: #848E9C; 
            margin-left: 5px; 
        }
        .charts-container { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-top: 20px; 
        }
        .chart-card { 
            background: #1E2329; 
            border-radius: 8px; 
            padding: 20px; 
            height: 400px;
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
        🚀 ULTIMATE: 실시간 + 누적통계 + 그래프 | 올바른 단위 변환 | 포트 8899 고정
    </div>
    
    <div class="header">
        <h1>🛰️ Ultimate Starlink Dashboard</h1>
        <div>
            <span id="status-indicator" class="connected">●</span>
            <span id="connection-status">실시간</span>
            <span style="margin-left: 20px;">데이터: <span id="current-index">0</span>/<span id="total-rows">0</span></span>
        </div>
    </div>

    <div class="main-grid">
        <!-- 실시간 데이터 섹션 -->
        <div>
            <div class="section-title">📊 실시간 데이터</div>
            <div class="realtime-section">
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
                    <div class="metric-title">핑 레이턴시</div>
                    <div class="metric-value" id="ping-latency">측정중<span class="metric-unit"></span></div>
                </div>
                
                <div class="status-card">
                    <div class="metric-title">신호 강도 (SNR)</div>
                    <div class="metric-value" id="snr">0.0<span class="metric-unit">dB</span></div>
                </div>
                
                <div class="status-card">
                    <div class="metric-title">업타임</div>
                    <div class="metric-value" id="uptime">0h 0m</div>
                </div>
            </div>
        </div>
        
        <!-- 누적 통계 섹션 -->
        <div class="cumulative-section">
            <div class="section-title">📈 누적 통계</div>
            
            <div class="cumulative-card">
                <div class="metric-title">총 다운로드</div>
                <div class="metric-value" id="total-download">0.0<span class="metric-unit">GB</span></div>
            </div>
            
            <div class="cumulative-card">
                <div class="metric-title">총 업로드</div>
                <div class="metric-value" id="total-upload">0.0<span class="metric-unit">GB</span></div>
            </div>
            
            <div class="cumulative-card">
                <div class="metric-title">최고 다운로드</div>
                <div class="metric-value" id="peak-download">0.0<span class="metric-unit">Mbps</span></div>
            </div>
            
            <div class="cumulative-card">
                <div class="metric-title">최고 업로드</div>
                <div class="metric-value" id="peak-upload">0.0<span class="metric-unit">Mbps</span></div>
            </div>
            
            <div class="cumulative-card">
                <div class="metric-title">평균 핑</div>
                <div class="metric-value" id="avg-ping">0.0<span class="metric-unit">ms</span></div>
            </div>
            
            <div class="cumulative-card">
                <div class="metric-title">세션 시간</div>
                <div class="metric-value" id="session-duration">0<span class="metric-unit">분</span></div>
            </div>
        </div>
    </div>

    <!-- 그래프 섹션 -->
    <div class="charts-container">
        <div class="chart-card">
            <div class="chart-title">📊 실시간 속도 그래프</div>
            <canvas id="speedChart" width="400" height="300"></canvas>
        </div>
        
        <div class="chart-card">
            <div class="chart-title">📡 핑 레이턴시 그래프</div>
            <canvas id="pingChart" width="400" height="300"></canvas>
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
                    backgroundColor: 'rgba(46, 189, 133, 0.1)',
                    fill: true,
                    tension: 0.3
                }, {
                    label: 'Upload (Mbps)', 
                    data: [],
                    borderColor: '#F0B90B',
                    backgroundColor: 'rgba(240, 185, 11, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { 
                    y: { 
                        beginAtZero: true,
                        grid: { color: '#333' },
                        ticks: { color: '#EAECEF' }
                    },
                    x: {
                        grid: { color: '#333' },
                        ticks: { color: '#EAECEF' }
                    }
                },
                plugins: { 
                    legend: { 
                        labels: { color: '#EAECEF' } 
                    } 
                }
            }
        });
        
        const pingChart = new Chart(pingCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Ping (ms)',
                    data: [],
                    borderColor: '#F6465D',
                    backgroundColor: 'rgba(244, 70, 93, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { 
                    y: { 
                        beginAtZero: true,
                        grid: { color: '#333' },
                        ticks: { color: '#EAECEF' }
                    },
                    x: {
                        grid: { color: '#333' },
                        ticks: { color: '#EAECEF' }
                    }
                },
                plugins: { 
                    legend: { 
                        labels: { color: '#EAECEF' } 
                    } 
                }
            }
        });

        // 실시간 데이터 업데이트
        function updateDashboard() {
            fetch('/api/ultimate-data')
                .then(response => response.json())
                .then(data => {
                    console.log('Ultimate data received:', data);
                    
                    const realtime = data.realtime || {};
                    const cumulative = data.cumulative || {};
                    const charts = data.charts || {};
                    
                    // 실시간 데이터 업데이트
                    if (realtime) {
                        document.getElementById('state').textContent = realtime.state || 'UNKNOWN';
                        document.getElementById('download-speed').innerHTML = `${(realtime.download_mbps || 0).toFixed(1)}<span class="metric-unit">Mbps</span>`;
                        document.getElementById('upload-speed').innerHTML = `${(realtime.upload_mbps || 0).toFixed(1)}<span class="metric-unit">Mbps</span>`;
                        
                        if (realtime.ping_latency !== null && realtime.ping_latency !== undefined) {
                            document.getElementById('ping-latency').innerHTML = `${realtime.ping_latency.toFixed(1)}<span class="metric-unit">ms</span>`;
                        } else {
                            document.getElementById('ping-latency').innerHTML = `측정중<span class="metric-unit"></span>`;
                        }
                        
                        document.getElementById('snr').innerHTML = `${(realtime.snr || 0).toFixed(1)}<span class="metric-unit">dB</span>`;
                        
                        // 업타임
                        const uptime = realtime.uptime || 0;
                        const hours = Math.floor(uptime / 3600);
                        const minutes = Math.floor((uptime % 3600) / 60);
                        document.getElementById('uptime').textContent = `${hours}h ${minutes}m`;
                        
                        document.getElementById('current-index').textContent = realtime.current_index || 0;
                        document.getElementById('total-rows').textContent = realtime.total_rows || 0;
                    }
                    
                    // 누적 통계 업데이트
                    if (cumulative) {
                        document.getElementById('total-download').innerHTML = `${(cumulative.total_download_gb || 0).toFixed(2)}<span class="metric-unit">GB</span>`;
                        document.getElementById('total-upload').innerHTML = `${(cumulative.total_upload_gb || 0).toFixed(2)}<span class="metric-unit">GB</span>`;
                        document.getElementById('peak-download').innerHTML = `${(cumulative.peak_download_mbps || 0).toFixed(1)}<span class="metric-unit">Mbps</span>`;
                        document.getElementById('peak-upload').innerHTML = `${(cumulative.peak_upload_mbps || 0).toFixed(1)}<span class="metric-unit">Mbps</span>`;
                        document.getElementById('avg-ping').innerHTML = `${(cumulative.avg_ping || 0).toFixed(1)}<span class="metric-unit">ms</span>`;
                        document.getElementById('session-duration').innerHTML = `${Math.floor(cumulative.session_duration_minutes || 0)}<span class="metric-unit">분</span>`;
                    }
                    
                    // 그래프 업데이트
                    if (charts && charts.timestamps) {
                        speedChart.data.labels = charts.timestamps;
                        speedChart.data.datasets[0].data = charts.download_speeds;
                        speedChart.data.datasets[1].data = charts.upload_speeds;
                        speedChart.update('none');
                        
                        pingChart.data.labels = charts.timestamps;
                        pingChart.data.datasets[0].data = charts.ping_values;
                        pingChart.update('none');
                    }
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

@app.route('/api/ultimate-data')
def get_ultimate_data():
    """실시간 + 누적 + 그래프 데이터 API"""
    return jsonify(dashboard.get_combined_data())

if __name__ == '__main__':
    print("🚀 Ultimate Starlink Dashboard 시작")
    print("📊 대시보드: http://localhost:8899")
    print("📈 실시간 + 누적통계 + 그래프 완전판")
    
    # 자동 모니터링 시작
    dashboard.start_monitoring()
    
    try:
        app.run(host='0.0.0.0', port=8899, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 대시보드 종료")
        dashboard.monitoring_active = False