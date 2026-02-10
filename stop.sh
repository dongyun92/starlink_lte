#!/bin/bash

###############################################################################
# Starlink Flight Analysis - Server Stop Script
#
# 모든 서버를 안전하게 중지합니다.
#
# Usage: ./stop.sh
###############################################################################

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starlink Flight Analysis - Server Stop"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Kill all Vite processes
echo "🔪 Stopping Vite dev server..."
pkill -f "vite" 2>/dev/null || true
pgrep -lf "node.*frontend" | awk '{print $1}' | xargs kill -9 2>/dev/null || true

# Kill specific ports
for port in 5173 5020 5021 5022 5023; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "  ├─ Killing process on port $port..."
        kill -9 $(lsof -ti:$port) 2>/dev/null || true
    fi
done

# Kill Flask server (port 5002)
if lsof -ti:5002 > /dev/null 2>&1; then
    echo "🔪 Stopping Flask server (port 5002)..."
    kill -9 $(lsof -ti:5002) 2>/dev/null || true
fi

# Kill any Python processes in analysis directory
pkill -f "python.*app.py" 2>/dev/null || true

sleep 2

echo "  └─ ✅ All servers stopped"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  🛑 Shutdown complete"
echo "═══════════════════════════════════════════════════════════════"
echo ""
