#!/bin/bash

# MyTutor Production Daemon Wrapper
# This script properly daemonizes the production script to survive SSH disconnects

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Starting MyTutor in daemon mode...${NC}"

# Check if already running
if [ -f "pids/monitor.pid" ]; then
    monitor_pid=$(cat pids/monitor.pid 2>/dev/null)
    if [ -n "$monitor_pid" ] && ps -p $monitor_pid > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  MyTutor is already running (Monitor PID: $monitor_pid)${NC}"
        echo -e "${CYAN}Use './stop.sh' to stop it first${NC}"
        exit 1
    fi
fi

# Create pids directory
mkdir -p pids

# Start production script as a proper daemon
# - Redirect stdout/stderr to production.log
# - Run in background with nohup
# - Detach from current session
nohup ./production.sh </dev/null >>logs/production.log 2>&1 &
MONITOR_PID=$!

# Save monitor PID
echo $MONITOR_PID > pids/monitor.pid

# Wait a moment to check if it started
sleep 2

if ps -p $MONITOR_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MyTutor started successfully in daemon mode${NC}"
    echo -e "${CYAN}   Monitor PID: $MONITOR_PID${NC}"
    echo ""
    echo -e "${CYAN}📝 View logs:${NC}"
    echo -e "   tail -f logs/monitor.log       # Monitoring and restarts"
    echo -e "   tail -f logs/production.log    # Startup and main logs"
    echo -e "   tail -f logs/frontend.log      # Frontend logs"
    echo -e "   tail -f logs/backend.log       # Backend logs"
    echo -e "   tail -f logs/agent.log         # Agent logs"
    echo ""
    echo -e "${CYAN}🛑 Stop services:${NC}"
    echo -e "   ./stop.sh"
    echo ""
    echo -e "${GREEN}You can now safely disconnect from SSH${NC}"
else
    echo -e "${RED}❌ Failed to start MyTutor${NC}"
    echo -e "${YELLOW}Check logs/production.log for details${NC}"
    exit 1
fi
