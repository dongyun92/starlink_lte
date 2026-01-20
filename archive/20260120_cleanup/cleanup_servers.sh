#!/bin/bash
# 🧹 스타링크 서버 정리 스크립트
# 모든 기존 서버를 종료하고 최종 대시보드만 실행

echo "🧹 스타링크 서버 정리 시작..."

# 모든 Python 스타링크 관련 프로세스 종료
echo "⏹️ 기존 Python 프로세스 종료 중..."
pkill -f "python.*starlink" 2>/dev/null || true
pkill -f "python.*dashboard" 2>/dev/null || true
pkill -f "python.*realtime" 2>/dev/null || true
pkill -f "python.*monitoring" 2>/dev/null || true

# 잠시 대기
sleep 2

# 포트 확인 및 정리
echo "🔌 포트 사용 상황 확인..."
lsof -ti:8000,8080,8888,8889,8890,8899 | xargs kill -9 2>/dev/null || true

echo "✅ 서버 정리 완료!"
echo ""
echo "🚀 실제 스타링크 대시보드 실행 중..."
echo "📡 포트: 8899"
echo "🌐 URL: http://localhost:8899"
echo "🔗 실제 192.168.100.1 gRPC 연결"
echo "🚫 시뮬레이션 없음 - 실제 데이터만"
echo ""
echo "✨ 실제 데이터 대시보드 실행으로 완료!"

# 실제 스타링크 대시보드 실행
source starlink_env/bin/activate && python real_starlink_dashboard.py &