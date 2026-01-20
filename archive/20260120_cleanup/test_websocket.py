#!/usr/bin/env python3
"""
WebSocket 연결 테스트 스크립트
"""
import socketio
import time
import json

def test_websocket():
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ WebSocket 연결 성공!")
    
    @sio.event
    def disconnect():
        print("❌ WebSocket 연결 해제")
    
    @sio.event
    def update(data):
        print(f"📡 실시간 데이터 수신: {data.get('timestamp', 'N/A')}")
        print(f"   신호강도: {data.get('signal_strength', 0)}%")
        print(f"   다운로드: {data.get('download_speed_mbps', 0)} Mbps")
        print(f"   업데이트 수: {getattr(test_websocket, 'update_count', 0) + 1}")
        test_websocket.update_count = getattr(test_websocket, 'update_count', 0) + 1
        
    @sio.event
    def status(data):
        print(f"📊 상태 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    try:
        print("🔗 WebSocket 연결 시도... (localhost:8888)")
        sio.connect('http://localhost:8888')
        
        print("⏳ 10초간 실시간 업데이트 확인...")
        time.sleep(10)
        
        sio.disconnect()
        print(f"✅ 테스트 완료. 총 {getattr(test_websocket, 'update_count', 0)}개 업데이트 수신")
        
    except Exception as e:
        print(f"❌ WebSocket 연결 실패: {e}")

if __name__ == "__main__":
    test_websocket()