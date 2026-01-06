#!/usr/bin/env python3
"""
스타링크 실제 API 테스트 - 다양한 방법 시도
"""

import requests
import json
import struct
from datetime import datetime

def test_http_api():
    """HTTP API 시도"""
    print("🔍 HTTP API 테스트...")
    
    base_url = "http://192.168.100.1"
    endpoints = [
        "/",
        "/status",
        "/api/status", 
        "/starlink/status",
        "/dish/status",
        "/stats",
        "/info"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"  테스트: {base_url}{endpoint}")
            response = requests.get(f"{base_url}{endpoint}", timeout=3)
            print(f"    응답: {response.status_code}, 길이: {len(response.content)}")
            
            if response.status_code == 200 and len(response.content) > 0:
                print(f"    ✅ 성공! 내용: {response.content[:100]}")
                
                # JSON인지 확인
                try:
                    data = response.json()
                    print(f"    📊 JSON 데이터: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                except:
                    print(f"    📝 텍스트 데이터")
                    
        except Exception as e:
            print(f"    ❌ 실패: {e}")

def test_grpc_variations():
    """다양한 gRPC-Web 요청 시도"""
    print("\n🔍 gRPC-Web 변형 테스트...")
    
    url = "http://192.168.100.1:9201/SpaceX.API.Device.Device/Handle"
    
    # 다양한 요청 패턴 시도
    requests_to_try = [
        # 완전한 빈 요청
        b'',
        
        # 기본 gRPC-Web 헤더만
        b'\x00\x00\x00\x00\x00',
        
        # GetStatus 빈 메시지
        b'\x00\x00\x00\x00\x02\x0A\x00',
        
        # 단순 Request 
        b'\x00\x00\x00\x00\x01\x0A',
        
        # 실제 protobuf 스타일
        struct.pack('>BI', 0, 2) + b'\x0A\x00',
        
        # 브라우저 스타일 요청 (추정)
        b'\x00\x00\x00\x00\x04\x08\x01\x12\x00',
    ]
    
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/grpc-web+proto',
        'Origin': 'http://192.168.100.1',
        'Referer': 'http://192.168.100.1/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'X-Grpc-Web': '1',
        'X-User-Agent': 'grpc-web-javascript/0.1'
    }
    
    for i, request_data in enumerate(requests_to_try):
        try:
            print(f"  시도 {i+1}: {len(request_data)} 바이트")
            print(f"    hex: {request_data.hex()}")
            
            response = requests.post(url, headers=headers, data=request_data, timeout=5)
            
            print(f"    응답: {response.status_code}, 길이: {len(response.content)}")
            
            if response.status_code == 200 and len(response.content) > 0:
                print(f"    ✅ 데이터 받음!")
                print(f"    응답 hex: {response.content.hex()}")
                
                # gRPC-Web 응답 파싱 시도
                if len(response.content) >= 5:
                    compressed = response.content[0]
                    msg_len = struct.unpack('>I', response.content[1:5])[0]
                    print(f"    파싱: 압축={compressed}, 길이={msg_len}")
                    
                    if msg_len > 0 and len(response.content) >= 5 + msg_len:
                        msg_data = response.content[5:5+msg_len]
                        print(f"    메시지: {msg_data.hex()}")
                        
                        # 간단한 필드 파싱
                        analyze_protobuf(msg_data)
            else:
                print(f"    ❌ 빈 응답")
                
        except Exception as e:
            print(f"    ❌ 오류: {e}")

def analyze_protobuf(data):
    """간단한 protobuf 분석"""
    print(f"    🔍 protobuf 분석:")
    
    if not data:
        print("      빈 데이터")
        return
        
    # 첫 몇 바이트 분석
    for i in range(min(10, len(data))):
        byte = data[i]
        field_num = byte >> 3
        wire_type = byte & 0x7
        print(f"      [{i}] {byte:02x} -> 필드:{field_num}, 타입:{wire_type}")

def test_web_interface():
    """웹 인터페이스 확인"""
    print("\n🔍 웹 인터페이스 테스트...")
    
    try:
        response = requests.get("http://192.168.100.1", timeout=5)
        print(f"메인 페이지: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            print(f"페이지 길이: {len(content)}")
            
            # JavaScript API 호출 찾기
            if "grpc" in content.lower():
                print("✅ gRPC 관련 코드 발견")
            if "api" in content.lower():
                print("✅ API 관련 코드 발견")
            if "status" in content.lower():
                print("✅ status 관련 코드 발견")
                
            # script 태그에서 API 호출 패턴 찾기
            import re
            api_calls = re.findall(r'fetch\(["\']([^"\']*)["\']', content)
            for call in api_calls[:5]:
                print(f"  발견된 API 호출: {call}")
                
    except Exception as e:
        print(f"웹 인터페이스 테스트 실패: {e}")

if __name__ == "__main__":
    print("🛰️ 스타링크 실제 API 테스트")
    print("=" * 50)
    
    # 1. HTTP API 테스트
    test_http_api()
    
    # 2. 웹 인터페이스 분석
    test_web_interface()
    
    # 3. gRPC-Web 변형 테스트
    test_grpc_variations()
    
    print("\n" + "=" * 50)
    print("테스트 완료")