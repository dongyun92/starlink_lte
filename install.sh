#!/bin/bash
# Starlink 모니터링 도구 설치 스크립트

echo "Starlink 모니터링 도구 설치를 시작합니다..."

# Python 가상환경 생성
python3 -m venv starlink_env
source starlink_env/bin/activate

# 필요 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "설치가 완료되었습니다!"
echo ""
echo "사용 방법:"
echo "1. 가상환경 활성화: source starlink_env/bin/activate"
echo "2. 한 번 수집: python starlink_monitor.py --once"
echo "3. 지속적 수집 (5분 간격): python starlink_monitor.py"
echo "4. 사용자 정의 간격: python starlink_monitor.py --interval 10"
echo ""