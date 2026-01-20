#!/bin/bash

echo "========================================="
echo "LTE 실제 데이터 수집 시작 스크립트"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 기존 프로세스 종료
echo -e "\n${YELLOW}기존 프로세스 종료 중...${NC}"
pkill -f "lte_remote_collector"
sleep 2

# 시리얼 포트 검색
echo -e "\n${YELLOW}LTE 모듈 검색 중...${NC}"

# Linux 시리얼 포트 확인
SERIAL_PORT=""
for port in /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB2 /dev/ttyACM0 /dev/ttyACM1; do
    if [ -e "$port" ]; then
        echo -e "${GREEN}✓ 포트 발견: $port${NC}"
        SERIAL_PORT=$port
        break
    fi
done

# Mac 시리얼 포트 확인
if [ -z "$SERIAL_PORT" ]; then
    for port in /dev/cu.usbserial* /dev/tty.usbserial* /dev/cu.usbmodem* /dev/tty.usbmodem*; do
        if [ -e "$port" ]; then
            echo -e "${GREEN}✓ 포트 발견: $port${NC}"
            SERIAL_PORT=$port
            break
        fi
    done
fi

# 포트를 찾지 못한 경우
if [ -z "$SERIAL_PORT" ]; then
    echo -e "${RED}✗ LTE 모듈을 찾을 수 없습니다${NC}"
    echo -e "${YELLOW}Mock 모드로 실행합니다...${NC}"
    SERIAL_PORT="/dev/ttyUSB0"  # 기본값 사용 (Mock 모드 자동 활성화)
else
    # 포트 권한 설정 (Linux/Mac)
    echo -e "\n${YELLOW}포트 권한 설정 중...${NC}"
    sudo chmod 666 $SERIAL_PORT 2>/dev/null || true
fi

# AT 명령어 테스트
echo -e "\n${YELLOW}AT 명령어 테스트 실행...${NC}"
python3 test_at_commands.py --port $SERIAL_PORT --baudrate 115200

# 사용자 확인
echo -e "\n${YELLOW}LTE 데이터 수집을 시작하시겠습니까? (y/n)${NC}"
read -r response

if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    # 데이터 디렉토리 생성
    mkdir -p lte-collector-data
    
    # LTE 컬렉터 시작
    echo -e "\n${GREEN}LTE 데이터 수집 시작...${NC}"
    echo "포트: $SERIAL_PORT"
    echo "제어 포트: 8897"
    echo "데이터 저장: ./lte-collector-data/"
    echo ""
    
    python3 lte_remote_collector_en.py \
        --data-dir ./lte-collector-data \
        --control-port 8897 \
        --serial-port $SERIAL_PORT \
        --interval 5
        
else
    echo -e "${YELLOW}취소되었습니다${NC}"
fi