#!/bin/bash
# 통신품질 분석 서버 재시작 (Flask + Vite)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/stop.sh"
sleep 1
"$SCRIPT_DIR/start.sh"
