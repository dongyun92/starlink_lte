#!/bin/bash

echo "========================================="
echo "LTE 모니터링 시스템 테스트"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test collector status
echo -e "\n${YELLOW}1. LTE 컬렉터 상태 확인...${NC}"
STATUS=$(curl -s http://localhost:8897/status | jq -r '.state')
if [ "$STATUS" == "collecting" ]; then
    echo -e "${GREEN}✓ 컬렉터 수집 중${NC}"
    POINTS=$(curl -s http://localhost:8897/status | jq -r '.total_points')
    echo "  - 수집된 데이터 포인트: $POINTS"
else
    echo -e "${RED}✗ 컬렉터 상태: $STATUS${NC}"
fi

# Test ground station
echo -e "\n${YELLOW}2. 지상국 대시보드 상태 확인...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8079/)
if [ "$HTTP_STATUS" == "200" ]; then
    echo -e "${GREEN}✓ 지상국 대시보드 정상 작동 (http://localhost:8079)${NC}"
else
    echo -e "${RED}✗ 지상국 응답 코드: $HTTP_STATUS${NC}"
fi

# Test drone control
echo -e "\n${YELLOW}3. 드론 제어 테스트...${NC}"
# Stop collection
STOP_RESULT=$(curl -s -X POST http://localhost:8079/api/drone_control/stop \
    -H "Content-Type: application/json" \
    -d '{"drone_address":"localhost"}' | jq -r '.success')
    
if [ "$STOP_RESULT" == "true" ]; then
    echo -e "${GREEN}✓ Stop 명령 성공${NC}"
else
    echo -e "${RED}✗ Stop 명령 실패${NC}"
fi

sleep 2

# Start collection
START_RESULT=$(curl -s -X POST http://localhost:8079/api/drone_control/start \
    -H "Content-Type: application/json" \
    -d '{"drone_address":"localhost"}' | jq -r '.success')
    
if [ "$START_RESULT" == "true" ]; then
    echo -e "${GREEN}✓ Start 명령 성공${NC}"
else
    echo -e "${RED}✗ Start 명령 실패${NC}"
fi

# Check recent data
echo -e "\n${YELLOW}4. 최근 수집 데이터 확인...${NC}"
RECENT_DATA=$(curl -s "http://localhost:8897/data/recent?count=1" | jq -r '.[0]')
if [ "$RECENT_DATA" != "null" ]; then
    echo -e "${GREEN}✓ 데이터 수집 정상${NC}"
    RSSI=$(echo $RECENT_DATA | jq -r '.rssi')
    NETWORK=$(echo $RECENT_DATA | jq -r '.network_type')
    echo "  - RSSI: $RSSI dBm"
    echo "  - Network: $NETWORK"
else
    echo -e "${RED}✗ 데이터 수집 실패${NC}"
fi

# Check CSV files
echo -e "\n${YELLOW}5. CSV 파일 생성 확인...${NC}"
CSV_COUNT=$(ls -1 lte-collector-data/*.csv 2>/dev/null | wc -l)
if [ "$CSV_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ CSV 파일 $CSV_COUNT 개 생성됨${NC}"
    LATEST_CSV=$(ls -t lte-collector-data/*.csv | head -1)
    echo "  - 최신 파일: $(basename $LATEST_CSV)"
    LINE_COUNT=$(wc -l < "$LATEST_CSV")
    echo "  - 데이터 라인: $LINE_COUNT"
else
    echo -e "${RED}✗ CSV 파일 없음${NC}"
fi

echo -e "\n========================================="
echo -e "${GREEN}테스트 완료!${NC}"
echo -e "지상국 대시보드: ${YELLOW}http://localhost:8079${NC}"
echo -e "========================================="