#!/usr/bin/env python3
"""
JavaScript Protobuf 구조 세밀 분석기
실제 작동하는 protobuf 패턴을 찾기 위한 정밀 분석
"""

import requests
import re
import json
import gzip
import struct
import binascii
from typing import Dict, List, Any

class JSProtobufAnalyzer:
    def __init__(self, dish_ip: str = "192.168.100.1"):
        self.dish_ip = dish_ip
        
    def analyze_compressed_js(self):
        """압축된 JavaScript 파일 상세 분석"""
        print("🔍 압축된 JavaScript 파일 상세 분석")
        
        js_url = f"http://{self.dish_ip}/static/js/script.js.gz"
        
        try:
            response = requests.get(js_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ 압축 파일 다운로드: {len(response.content)} 바이트")
                
                # gzip 압축 해제
                try:
                    decompressed = gzip.decompress(response.content)
                    js_content = decompressed.decode('utf-8')
                    print(f"📦 압축 해제: {len(js_content)} 바이트")
                    
                    # JavaScript 파일을 분석 가능한 파일로 저장
                    with open('/Users/dykim/dev/starlink/starlink_script_full.js', 'w', encoding='utf-8') as f:
                        f.write(js_content)
                    print("💾 전체 스크립트 저장: starlink_script_full.js")
                    
                    return self.deep_protobuf_analysis(js_content)
                    
                except Exception as e:
                    print(f"❌ 압축 해제 실패: {e}")
                    
        except Exception as e:
            print(f"❌ JS 파일 다운로드 실패: {e}")
            
    def deep_protobuf_analysis(self, js_content: str):
        """JavaScript에서 protobuf 패턴 정밀 분석"""
        print("\n🔬 Protobuf 패턴 정밀 분석")
        
        # 1. Request 관련 패턴 찾기
        self.find_request_patterns(js_content)
        
        # 2. gRPC 호출 패턴 찾기  
        self.find_grpc_patterns(js_content)
        
        # 3. Protobuf 메시지 정의 찾기
        self.find_message_definitions(js_content)
        
        # 4. 실제 API 호출 함수 찾기
        self.find_api_functions(js_content)
        
        # 5. 인코딩/디코딩 함수 찾기
        self.find_encoding_functions(js_content)
        
    def find_request_patterns(self, js_content: str):
        """Request 구조 패턴 분석"""
        print("\n📋 Request 패턴 분석:")
        
        patterns = [
            # Request 타입 정의
            r'Request[^{]*\{[^}]*\}',
            # oneofGroups 정의
            r'oneofGroups_[^;]*;',
            # RequestCase 정의
            r'RequestCase[^}]*\}',
            # 필드 번호 매핑
            r'(\d+)\s*:\s*[\'"](\w+)[\'"]',
            # protobuf 바이트 배열
            r'\[(\d+(?:,\s*\d+)*)\]',
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, js_content, re.IGNORECASE | re.DOTALL)
            if matches:
                print(f"  🎯 패턴 {i+1}: {len(matches)}개 발견")
                for match in matches[:3]:  # 처음 3개만 출력
                    if isinstance(match, tuple):
                        print(f"    → {match}")
                    else:
                        print(f"    → {match[:100]}...")
                        
    def find_grpc_patterns(self, js_content: str):
        """gRPC 호출 패턴 찾기"""
        print("\n🌐 gRPC 호출 패턴:")
        
        patterns = [
            # gRPC 서비스 호출
            r'grpc[^;]*handle[^;]*;',
            # fetch나 XMLHttpRequest 호출
            r'fetch\([^)]*\)',
            r'XMLHttpRequest[^;]*;',
            # protobuf 관련 함수
            r'encode[A-Z]\w*\([^)]*\)',
            r'decode[A-Z]\w*\([^)]*\)',
            # 메시지 생성
            r'new\s+\w*Request\([^)]*\)',
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            if matches:
                print(f"  📡 gRPC 패턴 {i+1}: {len(matches)}개")
                for match in matches[:2]:
                    print(f"    → {match[:80]}...")
                    
    def find_message_definitions(self, js_content: str):
        """Protobuf 메시지 정의 찾기"""
        print("\n📝 Protobuf 메시지 정의:")
        
        # SpaceX 관련 메시지 찾기
        spacex_patterns = [
            r'SpaceX\.API\.Device\.\w+',
            r'GetDiagnosticsRequest',
            r'GetDiagnosticsResponse', 
            r'DishGetDiagnosticsResponse',
            r'WifiGetDiagnosticsResponse',
            r'ToDevice',
            r'FromDevice',
        ]
        
        for pattern in spacex_patterns:
            matches = re.findall(pattern, js_content)
            if matches:
                print(f"  📄 {pattern}: {len(set(matches))}개 발견")
                
    def find_api_functions(self, js_content: str):
        """실제 API 호출 함수 찾기"""
        print("\n🎯 API 호출 함수:")
        
        # 함수 정의 패턴 찾기
        function_patterns = [
            r'function\s+(\w*[Dd]iagnostic\w*)\s*\([^{]*\{[^}]{50,200}\}',
            r'(\w+)\s*:\s*function[^{]*\{[^}]*grpc[^}]*\}',
            r'async\s+function\s+(\w*[Gg]et\w*)\s*\(',
        ]
        
        for pattern in function_patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE | re.DOTALL)
            if matches:
                print(f"  🔧 함수 발견: {matches}")
                
    def find_encoding_functions(self, js_content: str):
        """인코딩/디코딩 함수 찾기"""
        print("\n⚙️ 인코딩/디코딩 함수:")
        
        # 인코딩 관련 패턴
        encoding_patterns = [
            r'writeMessage\([^)]*\)',
            r'writeVarint\([^)]*\)', 
            r'writeBytes\([^)]*\)',
            r'serializeBinary\([^)]*\)',
            r'toUint8Array\([^)]*\)',
        ]
        
        for pattern in encoding_patterns:
            matches = re.findall(pattern, js_content)
            if matches:
                print(f"  📊 {pattern}: {len(matches)}개")
                
    def extract_actual_requests(self, js_content: str):
        """실제 요청 생성 패턴 추출"""
        print("\n🎯 실제 요청 생성 패턴 추출")
        
        # Request 생성 코드 찾기
        request_creation_patterns = [
            r'new\s+\w*Request[^;]*;',
            r'request\.[^=]*=\s*[^;]*;',
            r'\w*Request\.prototype\.[^=]*=\s*function[^}]*\}',
        ]
        
        for pattern in request_creation_patterns:
            matches = re.findall(pattern, js_content, re.DOTALL)
            if matches:
                print(f"  📦 요청 생성 패턴: {len(matches)}개")
                for match in matches[:2]:
                    print(f"    → {match[:100]}...")
                    
    def create_corrected_request(self):
        """분석 결과를 바탕으로 수정된 요청 생성"""
        print("\n🛠️ 분석 결과 기반 수정된 요청 생성")
        
        # 다양한 접근 방식 시도
        approaches = [
            self.create_minimal_request(),
            self.create_standard_grpc_request(), 
            self.create_full_message_request(),
            self.create_alternative_encoding()
        ]
        
        for i, (name, data) in enumerate(approaches):
            print(f"  📝 접근법 {i+1}: {name}")
            print(f"     길이: {len(data)} 바이트")
            print(f"     Hex: {data.hex()}")
            
            # 실제 테스트
            success = self.test_request(data)
            if success:
                print(f"     ✅ 성공!")
                return data
            else:
                print(f"     ❌ 실패")
                
        return None
    
    def create_minimal_request(self):
        """최소한의 요청"""
        # 단순히 empty message
        return ("최소 요청", b'\x00\x00\x00\x00\x00')
    
    def create_standard_grpc_request(self):
        """표준 gRPC 요청"""
        # GetDiagnostics (6000) with proper encoding
        message = b''  # empty GetDiagnosticsRequest
        
        # field 6000 in Request
        field_tag = (6000 << 3) | 2  # wire type 2
        field_data = self.encode_varint(field_tag) + self.encode_varint(0) + message
        
        # field 1 in ToDevice (request)
        request_data = b'\x0A' + self.encode_varint(len(field_data)) + field_data
        
        # gRPC-Web frame
        frame = b'\x00' + struct.pack('>I', len(request_data)) + request_data
        
        return ("표준 gRPC", frame)
    
    def create_full_message_request(self):
        """완전한 메시지 구조"""
        # ToDevice with all proper fields
        request_msg = b''  # Empty GetDiagnosticsRequest
        
        # Request message with field 6000
        request_field = self.encode_varint(48002) + self.encode_varint(0) + request_msg
        
        # ToDevice message with field 1 (request) 
        todevice_msg = b'\x0A' + self.encode_varint(len(request_field)) + request_field
        
        # gRPC frame with compression flag
        frame = b'\x00' + struct.pack('>I', len(todevice_msg)) + todevice_msg
        
        return ("완전한 메시지", frame)
        
    def create_alternative_encoding(self):
        """대안적 인코딩"""
        # 다른 field 번호나 구조 시도
        # Maybe the browser uses different field numbers
        alt_data = b'\x00\x00\x00\x00\x02\x08\x01'  # Alternative encoding
        return ("대안적 인코딩", alt_data)
    
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
    
    def test_request(self, data: bytes) -> bool:
        """요청 테스트"""
        try:
            response = requests.post(
                f"http://{self.dish_ip}:9201/SpaceX.API.Device.Device/Handle",
                headers={
                    'Content-Type': 'application/grpc-web+proto',
                    'X-Grpc-Web': '1',
                    'Origin': f'http://{self.dish_ip}',
                },
                data=data,
                timeout=5
            )
            return len(response.content) > 0
        except:
            return False

def main():
    print("🔍 JavaScript Protobuf 구조 세밀 분석기")
    print("=" * 60)
    
    analyzer = JSProtobufAnalyzer()
    
    # 압축된 JS 파일 분석
    analyzer.analyze_compressed_js()
    
    print("\n" + "=" * 60)
    print("🎯 분석 완료!")

if __name__ == "__main__":
    main()