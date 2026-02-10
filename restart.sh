#!/bin/bash

###############################################################################
# Starlink Flight Analysis 3D Visualization - Complete Restart Script
#
# This script handles ALL server restarts for the Starlink project.
# ALWAYS use this script. NEVER start servers manually.
#
# Usage: ./restart.sh
###############################################################################

set -e  # Exit on error

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starlink Flight Analysis - Complete System Restart"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Kill all existing processes
echo "🔪 Step 1/6: Killing existing processes..."

# Kill all Vite processes (any port)
echo "  ├─ Killing all Vite processes..."
pkill -f "vite" 2>/dev/null || true
sleep 1

# Kill all node processes related to this project
pgrep -lf "node.*frontend" | awk '{print $1}' | xargs kill -9 2>/dev/null || true

# Kill specific ports that might be in use
for port in 5173 5020 5021 5022 5023; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "  ├─ Killing process on port $port..."
        kill -9 $(lsof -ti:$port) 2>/dev/null || true
    fi
done

# Kill Flask server (port 5002)
if lsof -ti:5002 > /dev/null 2>&1; then
    echo "  ├─ Killing Flask server (port 5002)..."
    kill -9 $(lsof -ti:5002) 2>/dev/null || true
    sleep 1
fi

# Kill any Python processes in analysis directory
pkill -f "python.*app.py" 2>/dev/null || true

sleep 2  # Wait for all processes to terminate

echo "  └─ ✅ All processes killed"
echo ""

# Step 2: Clear Redis cache
echo "🗑️  Step 2/6: Clearing Redis cache..."
redis-cli FLUSHALL > /dev/null 2>&1 && echo "  └─ ✅ Redis cache cleared" || echo "  └─ ⚠️  Redis not available"
echo ""

# Step 3: Clear Python cache
echo "🗑️  Step 3/6: Clearing Python cache..."
cd /Users/dykim/dev/starlink/analysis
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo "  └─ ✅ Python cache cleared"
echo ""

# Step 4: Start Flask server
echo "🚀 Step 4/6: Starting Flask server (port 5002)..."
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

# Step 5: Start Vite dev server
echo "🚀 Step 5/6: Starting Vite dev server (port 5173)..."
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

# Step 6: Display status
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
