#!/usr/bin/env python3
"""
간단한 실시간 테스트 대시보드
"""
import time
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 간단한 카운터
counter = 0
running = False

def background_task():
    """백그라운드에서 실시간 데이터 전송"""
    global counter, running
    running = True
    
    while running:
        counter += 1
        
        # 간단한 테스트 데이터
        data = {
            'counter': counter,
            'timestamp': time.strftime('%H:%M:%S'),
            'interval': 1000,  # 1초
            'status': 'ACTIVE'
        }
        
        # WebSocket으로 전송
        socketio.emit('test_update', data)
        print(f"📡 전송: {counter} ({time.strftime('%H:%M:%S')})")
        
        time.sleep(1)  # 1초마다

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>실시간 테스트</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <style>
        body { font-family: monospace; background: #000; color: #0f0; padding: 20px; }
        .counter { font-size: 3em; color: #0ff; text-align: center; }
        .status { font-size: 2em; color: #ff0; text-align: center; }
        .log { border: 1px solid #0f0; padding: 10px; height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <h1>🚀 실시간 연결 테스트</h1>
    
    <div class="counter" id="counter">0</div>
    <div class="status" id="status">연결중...</div>
    
    <h3>실시간 로그:</h3>
    <div class="log" id="log"></div>
    
    <script>
        const socket = io();
        const counterEl = document.getElementById('counter');
        const statusEl = document.getElementById('status');
        const logEl = document.getElementById('log');
        
        function addLog(msg) {
            const time = new Date().toLocaleTimeString();
            logEl.innerHTML += `<div>[${time}] ${msg}</div>`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        socket.on('connect', function() {
            statusEl.textContent = '🟢 연결됨';
            statusEl.style.color = '#0f0';
            addLog('✅ WebSocket 연결 성공');
        });
        
        socket.on('disconnect', function() {
            statusEl.textContent = '🔴 연결끊김';
            statusEl.style.color = '#f00';
            addLog('❌ WebSocket 연결 해제');
        });
        
        socket.on('test_update', function(data) {
            counterEl.textContent = data.counter;
            addLog(`📡 업데이트: ${data.counter} (${data.timestamp})`);
        });
        
        addLog('🚀 페이지 로드 완료');
    </script>
</body>
</html>
    ''')

@socketio.on('connect')
def handle_connect():
    print('🔗 클라이언트 연결됨')
    
@socketio.on('disconnect')
def handle_disconnect():
    print('❌ 클라이언트 연결 해제')

if __name__ == '__main__':
    # 백그라운드 작업 시작
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    print("🚀 실시간 테스트 서버 시작: http://localhost:8889")
    socketio.run(app, host='0.0.0.0', port=8889, debug=False)