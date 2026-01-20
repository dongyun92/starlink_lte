#!/usr/bin/env python3
"""
Quectel EC25/EC21 LTE 모듈 AT 명령어 테스트 스크립트
실제 하드웨어 연결 시 AT 명령어가 제대로 작동하는지 테스트
"""

import serial
import time
import sys
import argparse

def test_at_command(ser, command, wait_time=1, description=""):
    """AT 명령어 테스트 및 응답 출력"""
    print(f"\n{'='*60}")
    if description:
        print(f"테스트: {description}")
    print(f"명령어: {command}")
    print("-" * 40)
    
    try:
        # 명령어 전송
        ser.write(f"{command}\r\n".encode())
        time.sleep(wait_time)
        
        # 응답 읽기
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        
        if response:
            print(f"응답:\n{response}")
            return True
        else:
            print("응답 없음")
            return False
            
    except Exception as e:
        print(f"에러: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='LTE 모듈 AT 명령어 테스터')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='시리얼 포트')
    parser.add_argument('--baudrate', type=int, default=115200, help='보드레이트')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Quectel EC25/EC21 LTE 모듈 테스트")
    print("=" * 60)
    print(f"포트: {args.port}")
    print(f"보드레이트: {args.baudrate}")
    
    try:
        # 시리얼 포트 연결
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            timeout=1,
            rtscts=True,
            dsrdtr=True
        )
        
        print(f"\n✅ 시리얼 포트 연결 성공: {args.port}")
        
        # 기본 AT 명령어 테스트
        tests = [
            ("AT", 1, "기본 통신 테스트"),
            ("ATI", 1, "모듈 정보 조회"),
            ("AT+CGMI", 1, "제조사 정보"),
            ("AT+CGMM", 1, "모델명"),
            ("AT+CGSN", 1, "IMEI 번호"),
            ("AT+CSQ", 1, "신호 강도 (RSSI, BER)"),
            ("AT+CREG?", 1, "2G/3G 네트워크 등록 상태"),
            ("AT+CEREG?", 1, "LTE 네트워크 등록 상태"),
            ("AT+COPS?", 1, "현재 네트워크 운영자"),
            ("AT+QNWINFO", 1, "네트워크 정보 (타입, 밴드, 채널)"),
            ("AT+CIMI", 1, "IMSI (SIM 카드 정보)"),
            ("AT+CCID", 1, "SIM 카드 ID"),
            ("AT+QGDCNT?", 1, "데이터 사용량 (RX/TX)"),
            ("AT+CGPADDR", 1, "IP 주소"),
            ("AT+QENG=\"servingcell\"", 2, "서빙 셀 상세 정보"),
            ("AT+QCSQ", 1, "확장 신호 품질 정보"),
            ("AT+QRSRP", 1, "RSRP (Reference Signal Received Power)"),
            ("AT+QRSRQ", 1, "RSRQ (Reference Signal Received Quality)"),
            ("AT+QSINR", 1, "SINR (Signal to Interference plus Noise Ratio)"),
        ]
        
        success_count = 0
        fail_count = 0
        
        for cmd, wait, desc in tests:
            if test_at_command(ser, cmd, wait, desc):
                success_count += 1
            else:
                fail_count += 1
            time.sleep(0.5)
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("테스트 결과 요약")
        print("=" * 60)
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {fail_count}개")
        
        if success_count > 0:
            print("\n🎉 LTE 모듈이 정상적으로 작동합니다!")
            print("실제 데이터 수집이 가능합니다.")
        else:
            print("\n⚠️ LTE 모듈 응답 없음")
            print("다음 사항을 확인하세요:")
            print("1. 모듈 전원 연결 상태")
            print("2. 시리얼 포트 설정 (포트명, 보드레이트)")
            print("3. USB 케이블 연결 상태")
            print("4. 모듈 드라이버 설치 여부")
        
        # 시리얼 포트 닫기
        ser.close()
        
    except serial.SerialException as e:
        print(f"\n❌ 시리얼 포트 연결 실패: {e}")
        print("\n해결 방법:")
        print("1. 올바른 포트명 확인:")
        print("   - Linux: /dev/ttyUSB0, /dev/ttyUSB1, ...")
        print("   - Mac: /dev/cu.usbserial-*, /dev/tty.usbserial-*")
        print("   - Windows: COM3, COM4, ...")
        print("2. 포트 권한 확인 (Linux/Mac):")
        print("   sudo chmod 666 /dev/ttyUSB0")
        print("3. 다른 프로그램이 포트를 사용 중인지 확인")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()