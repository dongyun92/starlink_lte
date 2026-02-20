#!/bin/bash

# 3D Visualization Server Management Script
# Usage: ./server.sh {start|stop|restart|status}

BACKEND_DIR="/Users/dykim/dev/starlink/analysis"
FRONTEND_DIR="/Users/dykim/dev/starlink/frontend"
BACKEND_PORT=5002
FRONTEND_PORT=5020

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if process is running
check_backend() {
    lsof -ti:$BACKEND_PORT > /dev/null 2>&1
    return $?
}

check_frontend() {
    lsof -ti:$FRONTEND_PORT > /dev/null 2>&1
    return $?
}

# Start backend server
start_backend() {
    if check_backend; then
        echo -e "${YELLOW}⚠️  Backend already running on port $BACKEND_PORT${NC}"
        return 1
    fi

    echo -e "${GREEN}🚀 Starting Backend (Flask) on port $BACKEND_PORT...${NC}"
    cd "$BACKEND_DIR"
    nohup /Users/dykim/dev/starlink/analysis_env/bin/python3 -m flask run --host=0.0.0.0 --port=$BACKEND_PORT > /tmp/flask_3d.log 2>&1 &
    sleep 2

    if check_backend; then
        echo -e "${GREEN}✅ Backend started successfully${NC}"
        echo -e "   Log: /tmp/flask_3d.log"
        return 0
    else
        echo -e "${RED}❌ Backend failed to start${NC}"
        tail -20 /tmp/flask_3d.log
        return 1
    fi
}

# Start frontend server
start_frontend() {
    if check_frontend; then
        echo -e "${YELLOW}⚠️  Frontend already running on port $FRONTEND_PORT${NC}"
        return 1
    fi

    echo -e "${GREEN}🚀 Starting Frontend (Vite) on port $FRONTEND_PORT...${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --port $FRONTEND_PORT > /tmp/vite_3d.log 2>&1 &
    sleep 3

    if check_frontend; then
        echo -e "${GREEN}✅ Frontend started successfully${NC}"
        echo -e "   URL: http://localhost:$FRONTEND_PORT"
        echo -e "   Log: /tmp/vite_3d.log"
        return 0
    else
        echo -e "${RED}❌ Frontend failed to start${NC}"
        tail -20 /tmp/vite_3d.log
        return 1
    fi
}

# Stop backend server
stop_backend() {
    if ! check_backend; then
        echo -e "${YELLOW}⚠️  Backend not running${NC}"
        return 1
    fi

    echo -e "${YELLOW}🛑 Stopping Backend...${NC}"
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null
    sleep 1

    if ! check_backend; then
        echo -e "${GREEN}✅ Backend stopped${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to stop backend${NC}"
        return 1
    fi
}

# Stop frontend server
stop_frontend() {
    if ! check_frontend; then
        echo -e "${YELLOW}⚠️  Frontend not running${NC}"
        return 1
    fi

    echo -e "${YELLOW}🛑 Stopping Frontend...${NC}"
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null
    sleep 1

    if ! check_frontend; then
        echo -e "${GREEN}✅ Frontend stopped${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to stop frontend${NC}"
        return 1
    fi
}

# Show server status
status() {
    echo ""
    echo "=== 3D Visualization Server Status ==="
    echo ""

    # Backend status
    if check_backend; then
        PID=$(lsof -ti:$BACKEND_PORT)
        echo -e "${GREEN}✅ Backend (Flask):${NC}"
        echo "   Port: $BACKEND_PORT"
        echo "   PID:  $PID"
        echo "   URL:  http://localhost:$BACKEND_PORT"
    else
        echo -e "${RED}❌ Backend (Flask): Not Running${NC}"
    fi

    echo ""

    # Frontend status
    if check_frontend; then
        PID=$(lsof -ti:$FRONTEND_PORT)
        echo -e "${GREEN}✅ Frontend (Vite):${NC}"
        echo "   Port: $FRONTEND_PORT"
        echo "   PID:  $PID"
        echo "   URL:  http://localhost:$FRONTEND_PORT"
    else
        echo -e "${RED}❌ Frontend (Vite): Not Running${NC}"
    fi

    echo ""
}

# Main command handler
case "$1" in
    start)
        echo ""
        echo "=== Starting 3D Visualization Servers ==="
        echo ""
        start_backend
        start_frontend
        echo ""
        status
        ;;

    stop)
        echo ""
        echo "=== Stopping 3D Visualization Servers ==="
        echo ""
        stop_backend
        stop_frontend
        echo ""
        ;;

    restart)
        echo ""
        echo "=== Restarting 3D Visualization Servers ==="
        echo ""
        stop_backend
        stop_frontend
        sleep 1
        start_backend
        start_frontend
        echo ""
        status
        ;;

    status)
        status
        ;;

    backend-start)
        start_backend
        ;;

    backend-stop)
        stop_backend
        ;;

    backend-restart)
        stop_backend
        sleep 1
        start_backend
        ;;

    frontend-start)
        start_frontend
        ;;

    frontend-stop)
        stop_frontend
        ;;

    frontend-restart)
        stop_frontend
        sleep 1
        start_frontend
        ;;

    logs)
        echo ""
        echo "=== Backend Logs (Last 20 lines) ==="
        tail -20 /tmp/flask_3d.log 2>/dev/null || echo "No backend logs found"
        echo ""
        echo "=== Frontend Logs (Last 20 lines) ==="
        tail -20 /tmp/vite_3d.log 2>/dev/null || echo "No frontend logs found"
        echo ""
        ;;

    logs-follow)
        echo ""
        echo "=== Following Backend Logs (Press Ctrl+C to stop) ==="
        echo ""
        tail -f /tmp/flask_3d.log
        ;;

    logs-backend)
        tail -f /tmp/flask_3d.log
        ;;

    logs-frontend)
        tail -f /tmp/vite_3d.log
        ;;

    *)
        echo ""
        echo "3D Visualization Server Management"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  start              Start both backend and frontend"
        echo "  stop               Stop both servers"
        echo "  restart            Restart both servers"
        echo "  status             Show server status"
        echo ""
        echo "  backend-start      Start backend only"
        echo "  backend-stop       Stop backend only"
        echo "  backend-restart    Restart backend only"
        echo ""
        echo "  frontend-start     Start frontend only"
        echo "  frontend-stop      Stop frontend only"
        echo "  frontend-restart   Restart frontend only"
        echo ""
        echo "  logs               Show recent logs"
        echo ""
        exit 1
        ;;
esac
