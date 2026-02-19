#!/bin/bash

###############################################################################
# Starlink Flight Analysis 3D Visualization - Complete Restart Script
#
# This script handles ALL server restarts for the Starlink project.
# ALWAYS use this script. NEVER start servers manually.
#
# Usage: ./restart.sh
###############################################################################

# PID 파일 - 우리 프로세스만 식별
FLASK_PID_FILE="/tmp/starlink_flask.pid"
VITE_PID_FILE="/tmp/starlink_vite.pid"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starlink Flight Analysis - Complete System Restart"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Starlink 프로세스만 종료 (다른 프로젝트 영향 없음)
echo "🔪 Step 1/6: Killing existing processes..."

# PID 파일로 정확히 우리 프로세스만 종료
kill_our_process() {
    local pid_file="$1"
    local name="$2"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            # 자식 프로세스도 함께 종료 (npm → node/vite 등)
            pkill -P "$pid" 2>/dev/null || true
            kill -9 "$pid" 2>/dev/null || true
            echo "  ├─ Killed $name (PID: $pid)"
        fi
        rm -f "$pid_file"
    fi
}

kill_our_process "$FLASK_PID_FILE" "Flask"
kill_our_process "$VITE_PID_FILE" "Vite"

# 경로 기반 fallback (PID 파일 없을 때, 우리 경로만 타겟)
pkill -f "starlink/analysis/app.py" 2>/dev/null || true
pkill -f "starlink/frontend.*vite" 2>/dev/null || true

sleep 1
echo "  └─ ✅ Starlink processes killed (other projects unaffected)"
echo ""

# Step 2: Redis cache 초기화
echo "🗑️  Step 2/6: Clearing Redis cache..."
redis-cli FLUSHALL > /dev/null 2>&1 && echo "  └─ ✅ Redis cache cleared" || echo "  └─ ⚠️  Redis not available"
echo ""

# Step 3: Python cache 초기화
echo "🗑️  Step 3/6: Clearing Python cache..."
find /Users/dykim/dev/starlink/analysis -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo "  └─ ✅ Python cache cleared"
echo ""

# Step 4: Flask 서버 시작 + PID 저장
echo "🚀 Step 4/6: Starting Flask server (port 5002)..."
cd /Users/dykim/dev/starlink/analysis
nohup python3 app.py > flask.log 2>&1 &
echo $! > "$FLASK_PID_FILE"

echo "  ├─ Waiting for Flask to start..."
for i in {1..10}; do
    if lsof -ti:5002 > /dev/null 2>&1; then
        echo "  └─ ✅ Flask server started successfully (${i}s)"
        break
    fi
    sleep 1
done

if ! lsof -ti:5002 > /dev/null 2>&1; then
    echo "  └─ ❌ Flask server failed to start after 10 seconds"
    echo ""
    echo "Flask logs (last 30 lines):"
    tail -30 /Users/dykim/dev/starlink/analysis/flask.log
    exit 1
fi
echo ""

# Step 5: Vite 서버 시작 + PID 저장
echo "🚀 Step 5/6: Starting Vite dev server (port 5173)..."
cd /Users/dykim/dev/starlink/frontend
nohup npm run dev -- --port 5173 --strictPort > /tmp/vite.log 2>&1 &
echo $! > "$VITE_PID_FILE"

echo "  ├─ Waiting for Vite to start..."
for i in {1..10}; do
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo "  └─ ✅ Vite dev server started successfully (${i}s)"
        break
    fi
    sleep 1
done

if ! lsof -ti:5173 > /dev/null 2>&1; then
    echo "  └─ ❌ Vite dev server failed to start after 10 seconds"
    echo ""
    echo "Vite logs (last 30 lines):"
    tail -30 /tmp/vite.log
    exit 1
fi
echo ""

# Step 6: 상태 출력
echo "✅ Step 6/6: System Status"
echo ""
echo "  Frontend (Vite):  http://localhost:5173"
echo "  Backend (Flask):  http://localhost:5002"
echo ""
echo "Logs:"
echo "  Flask:  tail -f /Users/dykim/dev/starlink/analysis/flask.log"
echo "  Vite:   tail -f /tmp/vite.log"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  🎉 All services started successfully!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
