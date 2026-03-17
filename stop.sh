#!/bin/bash
# 통신품질 분석 서버 중지 (Flask + Vite)

FLASK_PID_FILE="/tmp/starlink_flask.pid"
VITE_PID_FILE="/tmp/starlink_vite.pid"
BACKEND_PORT=5002
FRONTEND_PORT=5173

kill_by_pid_file() {
    local pid_file="$1" name="$2"
    if [ -f "$pid_file" ]; then
        local pid; pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            pkill -P "$pid" 2>/dev/null || true
            kill -9 "$pid" 2>/dev/null && echo "[STOP] $name (PID $pid)"
        fi
        rm -f "$pid_file"
    fi
}

kill_by_pid_file "$FLASK_PID_FILE" "Backend"
kill_by_pid_file "$VITE_PID_FILE"  "Frontend"

# fallback: 포트로 잔존 프로세스 정리
lsof -ti:$BACKEND_PORT  | xargs kill -9 2>/dev/null || true
lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true

echo "[DONE] All services stopped"
