#!/bin/bash
# Starlink 웹 대시보드 실행 스크립트

echo "Starlink 웹 대시보드를 시작합니다..."

# 가상환경 활성화
if [ -d "starlink_env" ]; then
    source starlink_env/bin/activate
    echo "가상환경이 활성화되었습니다."
else
    echo "가상환경이 없습니다. 먼저 ./install.sh를 실행하세요."
    exit 1
fi

# Python 경로 확인
which python

echo ""
echo "웹 대시보드가 http://localhost:5000 에서 실행됩니다."
echo "브라우저에서 해당 주소로 접속하세요."
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# 웹 대시보드 실행 (gRPC-Web 버전)
python final_web_dashboard.py