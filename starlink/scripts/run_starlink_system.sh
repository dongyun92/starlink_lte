#!/bin/bash

# 스타링크 모니터링 시스템 실행 스크립트
# 실행: ./run_starlink_system.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
COLLECTOR="${ROOT_DIR}/collector/remote_collector.py"
RECEIVER="${ROOT_DIR}/ground_station/receiver.py"
UI_DIR="${ROOT_DIR}/ground_station/ui/ground-station-ultra-compact"

echo "🚀 스타링크 모니터링 시스템 시작 중..."

# 기존 프로세스 정리
echo "📝 기존 프로세스 정리..."
pkill -f "remote_collector.py" > /dev/null 2>&1
pkill -f "receiver.py" > /dev/null 2>&1
sleep 2

# 가상환경 활성화 확인
if [ ! -d "${VENV_DIR}" ]; then
    echo "⚠️ Python 가상환경이 없습니다. 생성 중..."
    python3 -m venv "${VENV_DIR}"
    source "${VENV_DIR}/bin/activate"
    pip install flask requests
else
    source "${VENV_DIR}/bin/activate"
fi

echo "✅ Python 가상환경 활성화됨"

# 1. 테스트 데이터 수집기 시작 (드론 역할)
echo "🛸 테스트 드론 수집기 시작 (포트: 8899)..."
python "${COLLECTOR}" --control-port 8899 --mode mock > /dev/null 2>&1 &
DRONE_PID=$!

# 잠시 대기
sleep 3

# 2. 지상국 수신기 시작 (울트라 컴팩트 UI)
echo "📡 지상국 모니터 시작 (포트: 8080)..."
python "${RECEIVER}" --port 8080 --data-dir "${UI_DIR}" > /dev/null 2>&1 &
GROUND_PID=$!

# 시스템 준비 완료 대기
sleep 5

echo ""
echo "🎉 스타링크 모니터링 시스템 준비 완료!"
echo ""
echo "📊 대시보드 접속: http://localhost:8080"
echo ""
echo "💡 사용방법:"
echo "   1. 브라우저에서 http://localhost:8080 접속"
echo "   2. 드론 주소는 기본값 (localhost:8899) 사용"
echo "   3. 'Start Collection' 버튼으로 데이터 수집 시작"
echo "   4. 실시간 데이터 모니터링 가능"
echo ""
echo "📋 특징:"
echo "   • 10분 간격 파일 로테이션 (30MB 제한)"
echo "   • 실시간 모의 스타링크 데이터"
echo "   • 울트라 컴팩트 UI (스크롤 불필요)"
echo "   • 프리미엄 네이비/화이트 테마"
echo ""
echo "🛑 종료: Ctrl+C 또는 pkill -f 'starlink'"
echo ""
echo "프로세스 ID:"
echo "   드론 수집기: $DRONE_PID"
echo "   지상국 모니터: $GROUND_PID"

# 종료 시 프로세스 정리
cleanup() {
    echo ""
    echo "🛑 시스템 종료 중..."
    kill $DRONE_PID $GROUND_PID 2>/dev/null
    echo "✅ 정리 완료"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 백그라운드 프로세스 유지
wait
