#!/bin/bash

###############################################################################
# Starlink Flight Analysis - Server Start Script
#
# 모든 서버를 시작합니다. (기존 프로세스는 중지하지 않음)
#
# Usage: ./start.sh
###############################################################################

set -e  # Exit on error

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starlink Flight Analysis - Server Start"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if servers are already running
if lsof -ti:5002 > /dev/null 2>&1; then
    echo "⚠️  Flask server already running on port 5002"
    echo "   Use ./restart.sh to restart or ./stop.sh first"
    exit 1
fi

if lsof -ti:5173 > /dev/null 2>&1; then
    echo "⚠️  Vite server already running on port 5173"
    echo "   Use ./restart.sh to restart or ./stop.sh first"
    exit 1
fi

# Step 1: Clear Redis cache
echo "🗑️  Step 1/3: Clearing Redis cache..."
redis-cli FLUSHALL > /dev/null 2>&1 && echo "  └─ ✅ Redis cache cleared" || echo "  └─ ⚠️  Redis not available"
echo ""

# Step 2: Start Flask server
echo "🚀 Step 2/3: Starting Flask server (port 5002)..."
cd /Users/dykim/dev/starlink/analysis
nohup python3 app.py > flask.log 2>&1 &

# Wait for Flask to start (max 10 seconds)
echo "  ├─ Waiting for Flask to start..."
for i in {1..10}; do
    if lsof -ti:5002 > /dev/null 2>&1; then
        echo "  └─ ✅ Flask server started successfully (${i}s)"
        break
    fi
    sleep 1
done

# Final verification
if ! lsof -ti:5002 > /dev/null 2>&1; then
    echo "  └─ ❌ Flask server failed to start after 10 seconds"
    echo ""
    echo "Flask logs (last 30 lines):"
    tail -30 flask.log
    exit 1
fi
echo ""

# Step 3: Start Vite dev server
echo "🚀 Step 3/3: Starting Vite dev server (port 5173)..."
cd /Users/dykim/dev/starlink/frontend
nohup npm run dev -- --port 5173 --strictPort > /tmp/vite.log 2>&1 &

# Wait for Vite to start (max 10 seconds)
echo "  ├─ Waiting for Vite to start..."
for i in {1..10}; do
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo "  └─ ✅ Vite dev server started successfully (${i}s)"
        break
    fi
    sleep 1
done

# Final verification
if ! lsof -ti:5173 > /dev/null 2>&1; then
    echo "  └─ ❌ Vite dev server failed to start after 10 seconds"
    echo ""
    echo "Vite logs (last 30 lines):"
    tail -30 /tmp/vite.log
    exit 1
fi
echo ""

# Display status
echo "✅ System Status"
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
