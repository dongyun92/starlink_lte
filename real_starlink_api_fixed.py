#!/usr/bin/env python3
"""
수정된 실제 스타링크 API - 정확한 protobuf 구조 사용
JavaScript 분석 결과를 바탕으로 한 올바른 구현
"""

import json
import time
import logging
import requests
import struct
import csv
import os
from datetime import datetime, timezone
from typing import Dict, Any
import threading

class RealStarlinkAPI:
    def __init__(self, dish_ip: str = "192.168.100.1"):
        self.dish_ip = dish_ip
        self.grpc_url = f"http://{dish_ip}:9201/SpaceX.API.Device.Device/Handle"
        self.setup_logging()
        
        # 정확한 시간 동기화
        self.start_time = time.time()
        
        # 실제 브라우저 헤더 (완전 복제)
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/grpc-web+proto',
            'Host': f'{dish_ip}:9201',
            'Origin': f'http://{dish_ip}',
            'Pragma': 'no-cache',
            'Referer': f'http://{dish_ip}/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'X-Grpc-Web': '1',
            'X-User-Agent': 'grpc-web-javascript/0.1'
        }
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
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
    
    def create_diagnostics_request(self) -> bytes:
        """JavaScript 분석 결과 기반 GetDiagnosticsRequest 생성"""
        try:
            # JavaScript 분석 결과:
            # Request.oneofGroups_=[[1001,2002,6e3]]
            # Request.RequestCase={REQUEST_NOT_SET:0,REBOOT:1001,DISH_STOW:2002,GET_DIAGNOSTICS:6e3}
            # 6e3 = 6000 (GET_DIAGNOSTICS)
            
            # GetDiagnosticsRequest는 빈 메시지
            get_diagnostics_request = b''
            
            # Request 메시지 구성
            # field 6000 (GET_DIAGNOSTICS): tag = (6000 << 3) | 2 = 48002
            tag_6000 = (6000 << 3) | 2  # wire_type 2 (length-delimited)
            request_message = self.encode_varint(tag_6000) + self.encode_varint(len(get_diagnostics_request)) + get_diagnostics_request
            
            # ToDevice 메시지 구성
            # field 1 (request): tag = (1 << 3) | 2 = 10 = 0x0A
            to_device_message = b'\x0A' + self.encode_varint(len(request_message)) + request_message
            
            # gRPC-Web frame: [compressed_flag][message_length(4bytes)][message_data]
            compressed_flag = b'\x00'  # 압축 안함
            message_length = struct.pack('>I', len(to_device_message))
            
            frame = compressed_flag + message_length + to_device_message
            
            self.logger.info(f"GetDiagnostics 요청 생성: {len(frame)} 바이트")
            self.logger.info(f"요청 hex: {frame.hex()}")
            
            return frame
            
        except Exception as e:
            self.logger.error(f"GetDiagnostics 요청 생성 실패: {e}")
            return b''
    
    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            options_response = requests.options(
                self.grpc_url,
                headers={
                    'Origin': f'http://{self.dish_ip}',
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'content-type,x-grpc-web,x-user-agent'
                },
                timeout=5
            )
            
            return options_response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"연결 테스트 실패: {e}")
            return False
    
    def decode_varint(self, data: bytes, offset: int) -> tuple:
        """varint 디코딩"""
        result = 0
        shift = 0
        
        while offset < len(data):
            byte = data[offset]
            offset += 1
            
            result |= (byte & 0x7F) << shift
            
            if (byte & 0x80) == 0:
                break
                
            shift += 7
            
        return result, offset
    
    def parse_protobuf_fields(self, data: bytes) -> dict:
        """protobuf 필드 파싱"""
        fields = {}
        offset = 0
        
        try:
            while offset < len(data):
                if offset >= len(data):
                    break
                    
                # varint 태그 읽기
                tag, offset = self.decode_varint(data, offset)
                field_num = tag >> 3
                wire_type = tag & 0x7
                
                if wire_type == 0:  # varint
                    value, offset = self.decode_varint(data, offset)
                    fields[field_num] = value
                elif wire_type == 1:  # fixed64
                    if offset + 8 > len(data):
                        break
                    value = struct.unpack('<Q', data[offset:offset+8])[0]
                    fields[field_num] = value
                    offset += 8
                elif wire_type == 2:  # length-delimited
                    length, offset = self.decode_varint(data, offset)
                    if offset + length > len(data):
                        break
                    fields[field_num] = data[offset:offset+length]
                    offset += length
                elif wire_type == 5:  # fixed32
                    if offset + 4 > len(data):
                        break
                    value = struct.unpack('<I', data[offset:offset+4])[0]
                    fields[field_num] = value
                    offset += 4
                else:
                    self.logger.warning(f"알 수 없는 wire type: {wire_type}")
                    break
                    
        except Exception as e:
            self.logger.error(f"필드 파싱 오류: {e}")
        
        return fields
    
    def get_real_diagnostics(self) -> Dict[str, Any]:
        """실제 진단 데이터 요청"""
        try:
            request_data = self.create_diagnostics_request()
            if not request_data:
                return {}
            
            # API 요청
            response = requests.post(
                self.grpc_url,
                headers=self.headers,
                data=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"gRPC-Web 응답: {len(response.content)} 바이트")
                
                if len(response.content) > 0:
                    self.logger.info(f"응답 hex: {response.content.hex()}")
                    
                    # gRPC-Web 헤더 파싱
                    if len(response.content) >= 5:
                        compressed = response.content[0]
                        msg_len = struct.unpack('>I', response.content[1:5])[0]
                        self.logger.info(f"응답 분석: 압축={compressed}, 메시지길이={msg_len}")
                        
                        if msg_len > 0 and len(response.content) >= 5 + msg_len:
                            message_data = response.content[5:5+msg_len]
                            self.logger.info(f"메시지 데이터: {message_data.hex()}")
                            
                            # protobuf 파싱
                            return self.parse_response(message_data)
                
                self.logger.warning("빈 응답 또는 파싱 불가")
                return {}
            else:
                self.logger.error(f"API 요청 실패: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.error(f"진단 데이터 요청 실패: {e}")
            return {}
    
    def parse_response(self, data: bytes) -> Dict[str, Any]:
        """FromDevice 응답 파싱"""
        try:
            # FromDevice 파싱
            from_device_fields = self.parse_protobuf_fields(data)
            self.logger.info(f"FromDevice 필드: {list(from_device_fields.keys())}")
            
            if 1 in from_device_fields:  # response field
                response_data = from_device_fields[1]
                response_fields = self.parse_protobuf_fields(response_data)
                self.logger.info(f"Response 필드: {list(response_fields.keys())}")
                
                # dishGetDiagnostics (6001) 또는 wifiGetDiagnostics (6000) 확인
                if 6001 in response_fields:  # dishGetDiagnostics
                    return self.parse_dish_diagnostics(response_fields[6001])
                elif 6000 in response_fields:  # wifiGetDiagnostics  
                    return self.parse_wifi_diagnostics(response_fields[6000])
                
            self.logger.warning("알려진 진단 응답 필드를 찾을 수 없음")
            return {}
            
        except Exception as e:
            self.logger.error(f"응답 파싱 실패: {e}")
            return {}
    
    def parse_dish_diagnostics(self, data: bytes) -> Dict[str, Any]:
        """DishGetDiagnosticsResponse 파싱"""
        try:
            fields = self.parse_protobuf_fields(data)
            self.logger.info(f"Dish 진단 필드: {list(fields.keys())}")
            
            result = {
                'data_source': 'real_dish_diagnostics',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            
            # 필드 매핑 (JavaScript 분석 결과 기반)
            if 1 in fields:  # id
                result['device_id'] = fields[1].decode('utf-8', errors='ignore')
            if 2 in fields:  # hardwareVersion
                result['hardware_version'] = fields[2].decode('utf-8', errors='ignore')
            if 3 in fields:  # softwareVersion
                result['software_version'] = fields[3].decode('utf-8', errors='ignore')
            
            self.logger.info("✅ 실제 Dish 진단 데이터 파싱 성공!")
            return result
            
        except Exception as e:
            self.logger.error(f"Dish 진단 파싱 실패: {e}")
            return {}
    
    def parse_wifi_diagnostics(self, data: bytes) -> Dict[str, Any]:
        """WifiGetDiagnosticsResponse 파싱"""
        try:
            fields = self.parse_protobuf_fields(data)
            self.logger.info(f"WiFi 진단 필드: {list(fields.keys())}")
            
            result = {
                'data_source': 'real_wifi_diagnostics',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            
            if 1 in fields:  # id
                result['device_id'] = fields[1].decode('utf-8', errors='ignore')
            if 2 in fields:  # hardwareVersion
                result['hardware_version'] = fields[2].decode('utf-8', errors='ignore')
            if 3 in fields:  # softwareVersion
                result['software_version'] = fields[3].decode('utf-8', errors='ignore')
            
            self.logger.info("✅ 실제 WiFi 진단 데이터 파싱 성공!")
            return result
            
        except Exception as e:
            self.logger.error(f"WiFi 진단 파싱 실패: {e}")
            return {}

# 테스트 함수
def test_real_diagnostics():
    api = RealStarlinkAPI()
    print("🛰️ 실제 스타링크 진단 API 테스트")
    print("=" * 50)
    
    # 연결 테스트
    if api.test_connection():
        print("✅ API 연결 성공")
        
        # 진단 데이터 요청
        data = api.get_real_diagnostics()
        if data:
            print("✅ 실제 진단 데이터 받음!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("❌ 진단 데이터 없음")
    else:
        print("❌ API 연결 실패")

if __name__ == "__main__":
    test_real_diagnostics()