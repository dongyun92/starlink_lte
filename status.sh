#!/bin/bash

###############################################################################
# Starlink Flight Analysis - Server Status Script
#
# 모든 서버의 현재 상태를 확인합니다.
#
# Usage: ./status.sh
###############################################################################

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starlink Flight Analysis - Server Status"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check Flask server (port 5002)
echo "📊 Backend (Flask - Port 5002):"
if lsof -ti:5002 > /dev/null 2>&1; then
    FLASK_PID=$(lsof -ti:5002)
    echo "  ✅ Running (PID: $FLASK_PID)"
    echo "  📍 URL: http://localhost:5002"
    echo "  📝 Logs: tail -f /Users/dykim/dev/starlink/analysis/flask.log"
else
    echo "  ❌ Not running"
fi
echo ""

# Check Vite server (port 5173)
echo "🎨 Frontend (Vite - Port 5173):"
if lsof -ti:5173 > /dev/null 2>&1; then
    VITE_PID=$(lsof -ti:5173)
    echo "  ✅ Running (PID: $VITE_PID)"
    echo "  📍 URL: http://localhost:5173"
    echo "  📝 Logs: tail -f /tmp/vite.log"
else
    echo "  ❌ Not running"
fi
echo ""

# Check Redis
echo "💾 Redis (Port 6379):"
if lsof -ti:6379 > /dev/null 2>&1; then
    REDIS_PID=$(lsof -ti:6379)
    echo "  ✅ Running (PID: $REDIS_PID)"
    # Check Redis memory usage
    REDIS_KEYS=$(redis-cli DBSIZE 2>/dev/null | grep -o '[0-9]*' || echo "0")
    echo "  🔑 Cached keys: $REDIS_KEYS"
else
    echo "  ❌ Not running"
fi
echo ""

# Overall status
FLASK_OK=$(lsof -ti:5002 > /dev/null 2>&1 && echo "1" || echo "0")
VITE_OK=$(lsof -ti:5173 > /dev/null 2>&1 && echo "1" || echo "0")

echo "═══════════════════════════════════════════════════════════════"
if [ "$FLASK_OK" = "1" ] && [ "$VITE_OK" = "1" ]; then
    echo "  🎉 All services running normally"
elif [ "$FLASK_OK" = "1" ] || [ "$VITE_OK" = "1" ]; then
    echo "  ⚠️  Some services are running"
    echo ""
    echo "  To start missing services: ./start.sh"
    echo "  To restart all services:   ./restart.sh"
else
    echo "  ❌ All services are stopped"
    echo ""
    echo "  To start all services: ./start.sh"
fi
echo "═══════════════════════════════════════════════════════════════"
echo ""
