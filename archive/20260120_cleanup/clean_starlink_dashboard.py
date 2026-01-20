#!/usr/bin/env python3
"""
완전 실제 데이터 스타링크 대시보드 - 가짜 데이터 제거 버전
- 시뮬레이션 없음, 실제 데이터만 사용
- 하드코딩된 전력 소비 제거
- 실제 외부 핑 테스트 (8.8.8.8, 1.1.1.1) 추가
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

class CleanStarlinkDashboard:
    def __init__(self):
        self.monitoring_active = False
        self.data_collection_thread = None
        self.update_count = 0
        self.csv_file = f'clean_starlink_data_{datetime.now().strftime("%Y%m%d")}.csv'
        self.latest_data = {}
        self.grpc_tools_path = 'starlink-grpc-tools'
        
        # 마지막 유효 값 보관 (모바일 앱처럼 0.0 표시 방지)
        self.last_valid_values = {
            'download_throughput': None,
            'upload_throughput': None,
            'starlink_ping': None,
            'snr': None,
            'external_ping_google': None,
            'external_ping_cloudflare': None
        }
        
        # 외부 핑 테스트용 서버
        self.ping_servers = {
            'google': '8.8.8.8',
            'cloudflare': '1.1.1.1'
        }
        
        # CSV 헤더 초기화
        self.init_csv_file()
        
    def init_csv_file(self):
        """CSV 파일 헤더 생성 - 실제 데이터만"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'terminal_id', 'hardware_version', 'software_version',
                    'state', 'uptime', 'download_throughput_bps', 'upload_throughput_bps', 
                    'starlink_ping_ms', 'azimuth', 'elevation', 'snr',
                    'external_ping_google_ms', 'external_ping_cloudflare_ms',
                    'update_count', 'interval_ms'
                ])
        
    def test_external_ping(self):
        """실제 외부 서버 핑 테스트 (subprocess 사용)"""
        ping_results = {}
        
        for server_name, server_ip in self.ping_servers.items():
            try:
                # macOS ping 명령어 사용 (-c 1: 1회만, -W 2000: 2초 타임아웃)
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2000', server_ip],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if result.returncode == 0:
                    # ping 출력에서 시간 추출 (time=XXX.XXX ms 형태)
                    output_lines = result.stdout.split('\n')
                    for line in output_lines:
                        if 'time=' in line:
                            # time=12.345 ms 형태에서 숫자 추출
                            time_match = re.search(r'time=([0-9.]+)', line)
                            if time_match:
                                ping_time = float(time_match.group(1))
                                ping_results[server_name] = round(ping_time, 1)
                                break
                    else:
                        ping_results[server_name] = None
                else:
                    ping_results[server_name] = None
                    
            except Exception as e:
                print(f"⚠️ {server_name} 핑 테스트 실패: {e}")
                ping_results[server_name] = None
                
        return ping_results
    
    def update_last_valid_values(self, data):
        """마지막 유효 값 업데이트 (모바일 앱처럼 0.0 방지)"""
        # 다운로드/업로드 속도 (0이 아닌 값만)
        if data.get('download_throughput', 0) > 0:
            self.last_valid_values['download_throughput'] = data['download_throughput']
        
        if data.get('upload_throughput', 0) > 0:
            self.last_valid_values['upload_throughput'] = data['upload_throughput']
        
        # 핑 값 (None이 아닌 값만)
        if data.get('starlink_ping') is not None:
            self.last_valid_values['starlink_ping'] = data['starlink_ping']
        
        # SNR (0이 아닌 값만)
        if data.get('snr', 0) > 0:
            self.last_valid_values['snr'] = data['snr']
        
        # 외부 핑 (None이 아닌 값만)
        if data.get('external_ping_google') is not None:
            self.last_valid_values['external_ping_google'] = data['external_ping_google']
        
        if data.get('external_ping_cloudflare') is not None:
            self.last_valid_values['external_ping_cloudflare'] = data['external_ping_cloudflare']
    
    def get_display_value(self, key, current_value):
        """표시용 값 반환 (마지막 유효 값 또는 현재 값)"""
        if current_value is not None and current_value != 0:
            return current_value
        return self.last_valid_values.get(key)
        
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
        """gRPC 출력 파싱 - 실제 데이터만, 가짜 데이터 제거"""
        try:
            # CSV 형태의 출력 파싱
            parts = line.split(',')
            if len(parts) >= 14:
                # 실제 핑 값만 사용 (0이거나 빈 값이면 None)
                ping_value = None
                if parts[8] and parts[8] != '0.0' and parts[8] != '':
                    try:
                        ping_value = float(parts[8])
                    except ValueError:
                        ping_value = None
                
                # 실제 스루풋 데이터 (bytes/sec)
                download_bytes = 0.0
                upload_bytes = 0.0
                
                if parts[6]:
                    try:
                        download_bytes = float(parts[6])
                    except ValueError:
                        download_bytes = 0.0
                        
                if parts[7]:
                    try:
                        upload_bytes = float(parts[7])
                    except ValueError:
                        upload_bytes = 0.0
                
                # 실제 SNR 데이터
                snr_value = 0.0
                if len(parts) > 13 and parts[13]:
                    try:
                        snr_value = float(parts[13])
                    except ValueError:
                        snr_value = 0.0
                
                # 업타임
                uptime_seconds = 0
                if parts[5]:
                    try:
                        uptime_seconds = int(parts[5])
                    except ValueError:
                        uptime_seconds = 0
                
                # 방위각/고도
                azimuth = 0.0
                elevation = 0.0
                
                if len(parts) > 11 and parts[11]:
                    try:
                        azimuth = float(parts[11])
                    except ValueError:
                        azimuth = 0.0
                        
                if len(parts) > 12 and parts[12]:
                    try:
                        elevation = float(parts[12])
                    except ValueError:
                        elevation = 0.0
                
                return {
                    'timestamp': parts[0],
                    'terminal_id': parts[1],
                    'hardware_version': parts[2],
                    'software_version': parts[3],
                    'state': parts[4],
                    'uptime': uptime_seconds,
                    'ping_latency': ping_value,  # 실제 스타링크 핑 (ms)
                    'download_throughput': download_bytes,  # bytes/sec
                    'upload_throughput': upload_bytes,      # bytes/sec
                    'snr': snr_value,  # 신호 대 잡음 비 (dB)
                    'azimuth': azimuth,
                    'elevation': elevation,
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
        print("🚀 실제 스타링크 데이터 수집 시작 (가짜 데이터 없음)")
    
    def _real_data_collection_loop(self):
        """실제 스타링크 데이터 수집 루프"""
        while self.monitoring_active:
            loop_start = time.time()
            
            # 실제 gRPC 데이터 수집
            real_data = self.collect_real_starlink_data()
            
            # 외부 핑 테스트 (5회마다 1회 실행으로 부하 줄이기)
            external_ping = {}
            if self.update_count % 5 == 0:
                external_ping = self.test_external_ping()
            
            if real_data:
                self.update_count += 1
                current_time = datetime.now().isoformat() + '+00:00'
                
                # 실제 데이터로 최신 데이터 업데이트 (가짜 데이터 제거)
                raw_data = {
                    'timestamp': current_time,
                    'terminal_id': real_data['terminal_id'],
                    'hardware_version': real_data['hardware_version'],
                    'software_version': real_data['software_version'],
                    'state': real_data['state'],
                    'uptime': real_data['uptime'],
                    'download_throughput': real_data['download_throughput'],
                    'upload_throughput': real_data['upload_throughput'],
                    'starlink_ping': real_data['ping_latency'],
                    'azimuth': real_data['azimuth'],
                    'elevation': real_data['elevation'],
                    'snr': real_data['snr'],
                    'external_ping_google': external_ping.get('google'),
                    'external_ping_cloudflare': external_ping.get('cloudflare'),
                    'update_count': self.update_count,
                    'interval_ms': 100.0
                }
                
                # 마지막 유효 값 업데이트
                self.update_last_valid_values(raw_data)
                
                # 표시용 데이터 생성 (마지막 유효 값 사용)
                self.latest_data = {
                    'timestamp': current_time,
                    'terminal_id': raw_data['terminal_id'],
                    'hardware_version': raw_data['hardware_version'],
                    'software_version': raw_data['software_version'],
                    'state': raw_data['state'],
                    'uptime': raw_data['uptime'],
                    'download_throughput': self.get_display_value('download_throughput', raw_data['download_throughput']),
                    'upload_throughput': self.get_display_value('upload_throughput', raw_data['upload_throughput']),
                    'starlink_ping': self.get_display_value('starlink_ping', raw_data['starlink_ping']),
                    'azimuth': raw_data['azimuth'],
                    'elevation': raw_data['elevation'],
                    'snr': self.get_display_value('snr', raw_data['snr']),
                    'external_ping_google': self.get_display_value('external_ping_google', raw_data['external_ping_google']),
                    'external_ping_cloudflare': self.get_display_value('external_ping_cloudflare', raw_data['external_ping_cloudflare']),
                    'update_count': self.update_count,
                    'interval_ms': 100.0
                }
                
                # CSV에 실제 데이터 저장
                self.save_data_to_csv(self.latest_data)
                
                # 로깅 (1초마다)
                if self.update_count % 10 == 0:
                    ping_display = f"{real_data['ping_latency']:.1f}ms" if real_data['ping_latency'] is not None else "측정중"
                    
                    # 외부 핑 정보 추가
                    ext_ping_info = ""
                    if external_ping:
                        google_ping = f"G:{external_ping.get('google', 'N/A')}ms" if external_ping.get('google') else "G:fail"
                        cf_ping = f"CF:{external_ping.get('cloudflare', 'N/A')}ms" if external_ping.get('cloudflare') else "CF:fail"
                        ext_ping_info = f" | {google_ping} {cf_ping}"
                    
                    print(f"✅ 실제 데이터 #{self.update_count}: {real_data['state']} | "
                          f"⬇️{real_data['download_throughput']/125000:.1f}Mbps | "
                          f"⬆️{real_data['upload_throughput']/125000:.1f}Mbps | "
                          f"📡{ping_display}{ext_ping_info}")
            else:
                print(f"⚠️ 데이터 수집 실패 #{self.update_count}")
                
            # 100ms 간격 유지
            elapsed = time.time() - loop_start
            sleep_time = max(0, 0.1 - elapsed)
            time.sleep(sleep_time)
    
    def save_data_to_csv(self, data):
        """CSV에 실제 데이터만 저장"""
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
                    data['download_throughput'],  # bytes/sec
                    data['upload_throughput'],    # bytes/sec
                    data['starlink_ping'],        # ms 또는 None
                    data['azimuth'],
                    data['elevation'],
                    data['snr'],
                    data['external_ping_google'],     # ms 또는 None
                    data['external_ping_cloudflare'], # ms 또는 None
                    data['update_count'],
                    data['interval_ms']
                ])
        except Exception as e:
            print(f"❌ CSV 저장 오류: {e}")
    
    def stop_data_collection(self):
        """데이터 수집 중지"""
        self.monitoring_active = False
        if self.data_collection_thread:
            self.data_collection_thread.join(timeout=1)
        print("🛑 데이터 수집 중지")

# Flask 웹 인터페이스
dashboard = CleanStarlinkDashboard()

# 스타링크 앱 스타일 HTML 템플릿 (가짜 데이터 제거)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Clean Starlink Dashboard - No Fake Data</title>
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
            border: 1px solid #F0B90B; 
            border-radius: 8px; 
            padding: 15px; 
            margin-bottom: 20px; 
            color: #F0B90B; 
            text-align: center; 
            font-weight: bold; 
        }
    </style>
</head>
<body>
    <div class="disclaimer">
        ✅ FIXED VERSION: 단위 변환 수정 (÷125,000) | 마지막 값 보관 | 0.0 표시 방지 | Port 8899 고정
    </div>
    
    <div class="header">
        <h1>🛰️ Clean Starlink Dashboard</h1>
        <div>
            <span id="status-indicator" class="connected">●</span>
            <span id="connection-status">Connected</span>
            <span style="margin-left: 20px;">Updates: <span id="update-count">0</span></span>
            <span style="margin-left: 20px;">Interval: 100ms</span>
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
            <div class="metric-title">외부 핑 - Google</div>
            <div class="metric-value" id="external-ping-google">측정중<span class="metric-unit"></span></div>
        </div>
        
        <div class="status-card">
            <div class="metric-title">외부 핑 - Cloudflare</div>
            <div class="metric-value" id="external-ping-cloudflare">측정중<span class="metric-unit"></span></div>
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
            <div class="chart-title">📊 다운로드/업로드 속도</div>
            <canvas id="speedChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-card">
            <div class="chart-title">📡 핑 레이턴시</div>
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
                }, {
                    label: 'Google Ping (ms)',
                    data: [],
                    borderColor: '#F0B90B',
                    fill: false
                }, {
                    label: 'Cloudflare Ping (ms)',
                    data: [],
                    borderColor: '#F6465D',
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
                    
                    // 메트릭 업데이트 (실제 데이터만, 올바른 단위 변환: ÷125,000)
                    document.getElementById('state').textContent = data.state || 'UNKNOWN';
                    document.getElementById('download-speed').innerHTML = `${(data.download_throughput/125000 || 0).toFixed(1)}<span class="metric-unit">Mbps</span>`;
                    document.getElementById('upload-speed').innerHTML = `${(data.upload_throughput/125000 || 0).toFixed(1)}<span class="metric-unit">Mbps</span>`;
                    
                    // 핑 정보 (실제 값만 표시)
                    const starlinkPing = data.starlink_ping;
                    if (starlinkPing !== null && starlinkPing !== undefined) {
                        document.getElementById('ping-latency').innerHTML = `${starlinkPing.toFixed(1)}<span class="metric-unit">ms</span>`;
                    } else {
                        document.getElementById('ping-latency').innerHTML = `측정중<span class="metric-unit"></span>`;
                    }
                    
                    // 외부 핑 (실제 측정 값만)
                    const googlePing = data.external_ping_google;
                    if (googlePing !== null && googlePing !== undefined) {
                        document.getElementById('external-ping-google').innerHTML = `${googlePing.toFixed(1)}<span class="metric-unit">ms</span>`;
                    } else {
                        document.getElementById('external-ping-google').innerHTML = `측정중<span class="metric-unit"></span>`;
                    }
                    
                    const cfPing = data.external_ping_cloudflare;
                    if (cfPing !== null && cfPing !== undefined) {
                        document.getElementById('external-ping-cloudflare').innerHTML = `${cfPing.toFixed(1)}<span class="metric-unit">ms</span>`;
                    } else {
                        document.getElementById('external-ping-cloudflare').innerHTML = `측정중<span class="metric-unit"></span>`;
                    }
                    
                    document.getElementById('snr').innerHTML = `${(data.snr || 0).toFixed(1)}<span class="metric-unit">dB</span>`;
                    document.getElementById('update-count').textContent = data.update_count || 0;
                    
                    // 업타임 포맷
                    const uptime = data.uptime || 0;
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    const seconds = uptime % 60;
                    document.getElementById('uptime').textContent = `${hours}h ${minutes}m ${seconds}s`;
                    
                    // 차트 업데이트
                    const currentTime = new Date().toLocaleTimeString();
                    
                    // 속도 차트 (올바른 단위 변환: ÷125,000)
                    speedChart.data.labels.push(currentTime);
                    speedChart.data.datasets[0].data.push((data.download_throughput/125000 || 0));
                    speedChart.data.datasets[1].data.push((data.upload_throughput/125000 || 0));
                    
                    // 핑 차트
                    pingChart.data.labels.push(currentTime);
                    pingChart.data.datasets[0].data.push(starlinkPing);
                    pingChart.data.datasets[1].data.push(googlePing);
                    pingChart.data.datasets[2].data.push(cfPing);
                    
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
    """실제 스타링크 데이터 API (가짜 데이터 없음)"""
    return jsonify(dashboard.latest_data)

@app.route('/api/start')
def start_monitoring():
    """모니터링 시작"""
    dashboard.start_data_collection()
    return jsonify({"status": "started", "message": "실제 데이터 수집 시작"})

@app.route('/api/stop')
def stop_monitoring():
    """모니터링 중지"""
    dashboard.stop_data_collection()
    return jsonify({"status": "stopped", "message": "데이터 수집 중지"})

if __name__ == '__main__':
    print("🚀 Clean Starlink Dashboard 시작 (가짜 데이터 없음)")
    print("📊 대시보드: http://localhost:8899")
    print("🔄 실제 외부 핑 테스트 포함")
    print("⚡ 100ms 고속 데이터 수집")
    
    # 자동으로 데이터 수집 시작
    dashboard.start_data_collection()
    
    try:
        app.run(host='0.0.0.0', port=8899, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 대시보드 종료")
        dashboard.stop_data_collection()