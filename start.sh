#!/bin/bash
# 통신품질 분석 서버 시작 (Flask + Vite)

BACKEND_DIR="/Users/dykim/dev/starlink/analysis"
FRONTEND_DIR="/Users/dykim/dev/starlink/frontend"
FLASK_PID_FILE="/tmp/starlink_flask.pid"
VITE_PID_FILE="/tmp/starlink_vite.pid"
BACKEND_PORT=5002
FRONTEND_PORT=5173

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

is_running() { lsof -ti:"$1" > /dev/null 2>&1; }

# Backend
if is_running $BACKEND_PORT; then
    echo -e "${YELLOW}[SKIP] Backend already running on :$BACKEND_PORT${NC}"
else
    echo "[START] Backend (Flask :$BACKEND_PORT)..."
    cd "$BACKEND_DIR"
    nohup /Users/dykim/dev/starlink/analysis_env/bin/python3 app.py > flask.log 2>&1 &
    echo $! > "$FLASK_PID_FILE"
    for i in {1..10}; do
        is_running $BACKEND_PORT && break
        sleep 1
    done
    if is_running $BACKEND_PORT; then
        echo -e "${GREEN}[OK] Backend started${NC}"
    else
        echo -e "${RED}[FAIL] Backend failed — check analysis/flask.log${NC}"; exit 1
    fi
fi

# Frontend
if is_running $FRONTEND_PORT; then
    echo -e "${YELLOW}[SKIP] Frontend already running on :$FRONTEND_PORT${NC}"
else
    echo "[START] Frontend (Vite :$FRONTEND_PORT)..."
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --port $FRONTEND_PORT --strictPort > /tmp/vite.log 2>&1 &
    echo $! > "$VITE_PID_FILE"
    for i in {1..10}; do
        is_running $FRONTEND_PORT && break
        sleep 1
    done
    if is_running $FRONTEND_PORT; then
        echo -e "${GREEN}[OK] Frontend started${NC}"
    else
        echo -e "${RED}[FAIL] Frontend failed — check /tmp/vite.log${NC}"; exit 1
    fi
fi

echo ""
echo "  Dashboard : http://localhost:$FRONTEND_PORT"
echo "  API       : http://localhost:$BACKEND_PORT"
echo "  Logs      : tail -f analysis/flask.log  /  tail -f /tmp/vite.log"
