#!/bin/bash

# MyTutor Stop Script
# Gracefully stops all running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${YELLOW}🛑 Stopping MyTutor Services...${NC}"
echo ""

# Function to stop service by PID file
stop_service() {
    local pid_file=$1
    local service_name=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${CYAN}   Stopping $service_name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null || true

            # Wait up to 10 seconds for graceful shutdown
            for i in {1..10}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo -e "${GREEN}   ✅ $service_name stopped gracefully${NC}"
                    rm -f "$pid_file"
                    return 0
                fi
                sleep 1
            done

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${YELLOW}   ⚠️  Force stopping $service_name...${NC}"
                kill -9 $pid 2>/dev/null || true
                rm -f "$pid_file"
                echo -e "${GREEN}   ✅ $service_name force stopped${NC}"
            fi
        else
            echo -e "${YELLOW}   ℹ️  $service_name not running (stale PID file)${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}   ℹ️  No PID file for $service_name${NC}"
    fi
}

# Stop monitor first (if running via production-daemon.sh)
stop_service "pids/monitor.pid" "Monitor"

# Stop all services
stop_service "pids/agent.pid" "AgentCore"
stop_service "pids/backend.pid" "Backend"
stop_service "pids/frontend.pid" "Frontend"

# Additional cleanup - kill any processes on the ports
echo ""
echo -e "${CYAN}🔍 Cleaning up any remaining processes on ports...${NC}"

cleanup_port() {
    local port=$1
    local name=$2
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}   Found process on port $port ($name), terminating...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
}

cleanup_port 8080 "AgentCore"
cleanup_port 8000 "Backend"
cleanup_port 5173 "Frontend Dev"
cleanup_port 4173 "Frontend Prod"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All services stopped${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
