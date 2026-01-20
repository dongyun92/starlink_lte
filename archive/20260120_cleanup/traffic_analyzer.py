#!/usr/bin/env python3
"""
스타링크 네트워크 트래픽 분석기
브라우저의 실제 요청과 우리 구현을 비교하여 0-byte 응답 문제 해결
"""

import requests
import struct
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

class TrafficAnalyzer:
    def __init__(self, dish_ip: str = "192.168.100.1"):
        self.dish_ip = dish_ip
        self.grpc_url = f"http://{dish_ip}:9201/SpaceX.API.Device.Device/Handle"
        self.web_url = f"http://{dish_ip}/"
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def analyze_web_page(self):
        """웹페이지 분석하여 실제 API 호출 패턴 찾기"""
        print("🔍 스타링크 웹페이지 분석 중...")
        
        try:
            response = requests.get(self.web_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                print(f"✅ 웹페이지 로드 성공: {len(content)} 바이트")
                
                # JavaScript 파일 링크 찾기
                import re
                js_files = re.findall(r'<script[^>]*src="([^"]*\.js[^"]*)"', content)
                for js_file in js_files:
                    print(f"  📄 JavaScript 파일 발견: {js_file}")
                    
                    if not js_file.startswith('http'):
                        js_url = f"http://{self.dish_ip}{js_file}"
                    else:
                        js_url = js_file
                    
                    self.analyze_js_file(js_url)
                    
        except Exception as e:
            print(f"❌ 웹페이지 분석 실패: {e}")
    
    def analyze_js_file(self, js_url: str):
        """JavaScript 파일에서 API 호출 패턴 분석"""
        try:
            response = requests.get(js_url, timeout=5)
            if response.status_code == 200:
                js_content = response.text
                print(f"  📥 JS 파일 로드: {len(js_content)} 바이트")
                
                # gRPC-Web 관련 패턴 찾기
                import re
                
                # API 호출 패턴
                api_patterns = re.findall(r'fetch\([\'"]([^\'"]*)[\'"]', js_content)
                grpc_patterns = re.findall(r'grpc[^;]*;', js_content)
                
                if api_patterns:
                    print(f"  🎯 API 호출 패턴: {api_patterns[:3]}")
                if grpc_patterns:
                    print(f"  🔗 gRPC 패턴: {grpc_patterns[:2]}")
                    
                # protobuf 필드 번호 찾기
                field_patterns = re.findall(r'(\d+)\s*:\s*[\'"]([^\'"]*)[\'"]', js_content)
                if field_patterns:
                    print(f"  📊 필드 매핑: {field_patterns[:5]}")
                
        except Exception as e:
            print(f"  ❌ JS 분석 실패: {e}")
    
    def test_different_requests(self):
        """다양한 요청 패턴 테스트"""
        print("\n🧪 다양한 gRPC-Web 요청 패턴 테스트")
        
        # 테스트할 요청들
        test_requests = [
            # 1. 완전히 빈 GetDiagnostics
            {
                'name': '빈 GetDiagnostics',
                'data': self.create_empty_diagnostics()
            },
            
            # 2. GetStatus 요청 (다른 RPC 메소드)
            {
                'name': 'GetStatus 요청',
                'data': self.create_status_request()
            },
            
            # 3. Reboot 요청 (테스트용)
            {
                'name': 'Reboot 요청 (테스트)',
                'data': self.create_reboot_request()
            },
            
            # 4. DishStow 요청
            {
                'name': 'DishStow 요청',
                'data': self.create_dish_stow_request()
            },
            
            # 5. 다른 헤더로 요청
            {
                'name': 'Chrome 헤더',
                'data': self.create_empty_diagnostics(),
                'headers': self.get_chrome_headers()
            }
        ]
        
        for test in test_requests:
            print(f"\n  🔬 테스트: {test['name']}")
            self.send_grpc_request(
                test['data'], 
                headers=test.get('headers', self.get_default_headers())
            )
            time.sleep(1)  # 요청 간 간격
    
    def create_empty_diagnostics(self) -> bytes:
        """완전히 빈 GetDiagnostics 요청"""
        # GetDiagnosticsRequest는 완전히 빈 메시지
        get_diagnostics = b''
        
        # Request 메시지: field 6000 (GET_DIAGNOSTICS)
        tag_6000 = (6000 << 3) | 2  # 48002
        request_msg = self.encode_varint(tag_6000) + self.encode_varint(0) + get_diagnostics
        
        # ToDevice 메시지: field 1 (request)
        to_device = b'\x0A' + self.encode_varint(len(request_msg)) + request_msg
        
        # gRPC-Web frame
        frame = b'\x00' + struct.pack('>I', len(to_device)) + to_device
        
        return frame
    
    def create_status_request(self) -> bytes:
        """GetStatus 요청 생성"""
        # Request에서 다른 필드 시도 (추정)
        status_request = b''
        
        # 가능한 GetStatus 필드 번호 (JavaScript에서 찾은 패턴)
        tag_status = (1004 << 3) | 2  # 추정된 GetStatus 필드
        request_msg = self.encode_varint(tag_status) + self.encode_varint(0) + status_request
        
        to_device = b'\x0A' + self.encode_varint(len(request_msg)) + request_msg
        frame = b'\x00' + struct.pack('>I', len(to_device)) + to_device
        
        return frame
    
    def create_reboot_request(self) -> bytes:
        """Reboot 요청 (JavaScript에서 확인된 1001 필드)"""
        reboot_request = b''
        
        tag_1001 = (1001 << 3) | 2  # REBOOT
        request_msg = self.encode_varint(tag_1001) + self.encode_varint(0) + reboot_request
        
        to_device = b'\x0A' + self.encode_varint(len(request_msg)) + request_msg
        frame = b'\x00' + struct.pack('>I', len(to_device)) + to_device
        
        return frame
        
    def create_dish_stow_request(self) -> bytes:
        """DishStow 요청 (JavaScript에서 확인된 2002 필드)"""
        stow_request = b''
        
        tag_2002 = (2002 << 3) | 2  # DISH_STOW
        request_msg = self.encode_varint(tag_2002) + self.encode_varint(0) + stow_request
        
        to_device = b'\x0A' + self.encode_varint(len(request_msg)) + request_msg
        frame = b'\x00' + struct.pack('>I', len(to_device)) + to_device
        
        return frame
    
    def get_default_headers(self) -> Dict[str, str]:
        """기본 헤더"""
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/grpc-web+proto',
            'Origin': f'http://{self.dish_ip}',
            'Referer': f'http://{self.dish_ip}/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'X-Grpc-Web': '1',
            'X-User-Agent': 'grpc-web-javascript/0.1'
        }
    
    def get_chrome_headers(self) -> Dict[str, str]:
        """최신 Chrome 헤더"""
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/grpc-web+proto',
            'Origin': f'http://{self.dish_ip}',
            'Pragma': 'no-cache',
            'Referer': f'http://{self.dish_ip}/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Grpc-Web': '1',
            'X-User-Agent': 'grpc-web-javascript/0.1'
        }
    
    def encode_varint(self, value: int) -> bytes:
        """Protobuf varint 인코딩"""
        if value == 0:
            return b'\x00'
        
        result = b''
        while value > 0:
            byte = value & 0x7F
            value >>= 7
            if value > 0:
                byte |= 0x80
            result += bytes([byte])
        return result
    
    def send_grpc_request(self, data: bytes, headers: Dict[str, str]):
        """gRPC 요청 전송 및 분석"""
        try:
            print(f"    📤 요청: {len(data)} 바이트")
            print(f"    🔢 Hex: {data.hex()}")
            
            response = requests.post(
                self.grpc_url,
                headers=headers,
                data=data,
                timeout=10
            )
            
            print(f"    📥 응답: {response.status_code}")
            print(f"    📊 길이: {len(response.content)} 바이트")
            
            if len(response.content) > 0:
                print(f"    ✅ 데이터 받음! Hex: {response.content.hex()}")
                
                # 응답 헤더 분석
                for key, value in response.headers.items():
                    if 'grpc' in key.lower() or 'content' in key.lower():
                        print(f"    📋 {key}: {value}")
                
                return True
            else:
                print(f"    ❌ 빈 응답")
                return False
                
        except Exception as e:
            print(f"    💥 오류: {e}")
            return False
    
    def check_connectivity(self):
        """연결성 종합 확인"""
        print("🔌 스타링크 연결성 종합 확인\n")
        
        tests = [
            ("웹 인터페이스", self.web_url),
            ("gRPC OPTIONS", self.grpc_url),
        ]
        
        for name, url in tests:
            try:
                if "OPTIONS" in name:
                    response = requests.options(url, timeout=5, headers={
                        'Origin': f'http://{self.dish_ip}',
                        'Access-Control-Request-Method': 'POST',
                        'Access-Control-Request-Headers': 'content-type,x-grpc-web'
                    })
                else:
                    response = requests.get(url, timeout=5)
                
                print(f"✅ {name}: {response.status_code}")
                
                # CORS 헤더 확인
                cors_headers = {k: v for k, v in response.headers.items() 
                              if 'access-control' in k.lower() or 'cors' in k.lower()}
                if cors_headers:
                    print(f"   🌐 CORS: {cors_headers}")
                    
            except Exception as e:
                print(f"❌ {name}: {e}")

def main():
    print("🛰️ 스타링크 트래픽 분석기 시작")
    print("=" * 60)
    
    analyzer = TrafficAnalyzer()
    
    # 1. 기본 연결성 확인
    analyzer.check_connectivity()
    
    # 2. 웹페이지 분석
    analyzer.analyze_web_page()
    
    # 3. 다양한 요청 패턴 테스트
    analyzer.test_different_requests()
    
    print("\n" + "=" * 60)
    print("🎯 분석 완료!")
    print("   다음 단계:")
    print("   1. 위 결과에서 성공한 요청 패턴 확인")
    print("   2. JavaScript 파일에서 실제 API 호출 패턴 분석")
    print("   3. 성공적인 패턴을 메인 API에 적용")

if __name__ == "__main__":
    main()