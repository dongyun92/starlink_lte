#!/usr/bin/env python3
"""
Simple Starlink 실시간 웹 대시보드 (gRPC 의존성 없음)
"""

import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from collections import deque
import logging

from simple_starlink_monitor import SimpleStarlinkMonitor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple_starlink_dashboard_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# 전역 데이터 저장소
data_history = deque(maxlen=100)  # 최근 100개 데이터 포인트
current_data = {}
monitor = None
monitoring_thread = None
is_monitoring = False

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def data_collector():
    """백그라운드에서 데이터 수집"""
    global current_data, is_monitoring
    
    while is_monitoring:
        try:
            if monitor:
                data = monitor.collect_data()
                if data:
                    current_data = data
                    data_history.append(data)
                    
                    # 웹소켓으로 실시간 데이터 전송
                    socketio.emit('data_update', data)
                    logging.info(f"데이터 업데이트: SNR={data.get('snr', 0):.1f}dB, 핑={data.get('pop_ping_latency_ms', 0):.1f}ms")
                    
        except Exception as e:
            logging.error(f"데이터 수집 오류: {e}")
        
        time.sleep(30)  # 30초마다 수집

@app.route('/')
def dashboard():
    """메인 대시보드 페이지"""
    return render_template('dashboard.html')

@app.route('/api/current')
def get_current_data():
    """현재 데이터 반환"""
    return jsonify(current_data)

@app.route('/api/history')
def get_history():
    """데이터 히스토리 반환"""
    return jsonify(list(data_history))

@app.route('/api/stats')
def get_stats():
    """통계 정보 반환"""
    if not data_history:
        return jsonify({'error': '데이터가 없습니다'})
    
    # 최근 1시간 데이터로 통계 계산
    recent_data = list(data_history)[-20:]  # 최근 20개
    
    stats = {}
    
    # 평균 계산할 필드들
    numeric_fields = [
        'pop_ping_latency_ms', 'pop_ping_drop_rate', 'downlink_throughput_bps',
        'uplink_throughput_bps', 'snr', 'obstruction_fraction'
    ]
    
    for field in numeric_fields:
        values = [data.get(field, 0) for data in recent_data if data.get(field) is not None]
        if values:
            stats[f'{field}_avg'] = sum(values) / len(values)
            stats[f'{field}_min'] = min(values)
            stats[f'{field}_max'] = max(values)
    
    return jsonify(stats)

@socketio.on('connect')
def handle_connect():
    """클라이언트 연결시"""
    logging.info('클라이언트가 연결되었습니다')
    emit('status', {'message': '연결되었습니다'})
    
    # 현재 데이터 전송
    if current_data:
        emit('data_update', current_data)

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제시"""
    logging.info('클라이언트 연결이 해제되었습니다')

def start_monitoring():
    """모니터링 시작"""
    global monitor, monitoring_thread, is_monitoring
    
    try:
        monitor = SimpleStarlinkMonitor()
        is_monitoring = True
        monitoring_thread = threading.Thread(target=data_collector, daemon=True)
        monitoring_thread.start()
        logging.info("Simple 모니터링이 시작되었습니다")
        return True
    except Exception as e:
        logging.error(f"모니터링 시작 실패: {e}")
    
    return False

def stop_monitoring():
    """모니터링 중지"""
    global is_monitoring
    is_monitoring = False

if __name__ == '__main__':
    setup_logging()
    
    print("=" * 60)
    print("🛰️  Simple Starlink 웹 대시보드")
    print("=" * 60)
    print("📊 실시간 데이터: 30초마다 업데이트")
    print("🌐 웹 주소: http://localhost:5000")
    print("📝 로그: simple_starlink_monitor.log")
    print("=" * 60)
    
    # 모니터링 시작
    if start_monitoring():
        try:
            # 웹 서버 시작
            socketio.run(app, host='0.0.0.0', port=5000, debug=False)
        finally:
            stop_monitoring()
    else:
        print("❌ 모니터링 시작에 실패했습니다")