#!/bin/bash

# MyTutor Production Deployment Script
# Runs all services as background daemons with proper process management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${PURPLE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                            ║${NC}"
echo -e "${PURPLE}║            🚀 MyTutor Production Deployment 🚀             ║${NC}"
echo -e "${PURPLE}║                                                            ║${NC}"
echo -e "${PURPLE}║         AI-Powered Course Learning Platform                ║${NC}"
echo -e "${PURPLE}║                                                            ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running from project root
if [ ! -d "agent" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Error: Must run from project root directory${NC}"
    exit 1
fi

# Function to kill process on port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  Port $port is in use. Stopping existing process...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Create necessary directories
echo -e "${CYAN}📁 Creating directories...${NC}"
mkdir -p logs
mkdir -p pids
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Kill any existing processes on required ports
echo -e "${CYAN}🔍 Checking and cleaning up ports...${NC}"
kill_port 8080  # AgentCore
kill_port 8000  # Backend
kill_port 5173  # Frontend (same port for dev and production)
echo -e "${GREEN}✅ All ports ready${NC}"
echo ""

# Clear Python bytecode cache to ensure fresh code loads
echo -e "${CYAN}🧹 Clearing Python bytecode cache...${NC}"
find agent -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find agent -name "*.pyc" -delete 2>/dev/null || true
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Python cache cleared${NC}"
echo ""

# Setup AgentCore
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🤖 Deploying AgentCore Runtime...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd agent
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}   Creating virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${YELLOW}   Installing dependencies...${NC}"
    pip install -r requirements.txt
    playwright install
else
    source .venv/bin/activate
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}   Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}   ⚠️  Please update agent/.env with your AWS credentials!${NC}"
fi

# Start agent as daemon with unbuffered output
nohup python -u full_course_processor.py > ../logs/agent.log 2>&1 &
AGENT_PID=$!
echo $AGENT_PID > ../pids/agent.pid
echo -e "${GREEN}✅ AgentCore started (PID: $AGENT_PID)${NC}"
echo -e "${CYAN}   📝 Log: tail -f logs/agent.log${NC}"
cd ..
sleep 3

# Setup Backend
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}⚙️  Deploying Backend API...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd backend
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}   Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${YELLOW}   Installing dependencies...${NC}"
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}   Creating .env from .env.example...${NC}"
    cp .env.example .env
fi

# Start backend as daemon (no --reload in production)
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../pids/backend.pid
echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
echo -e "${CYAN}   📝 Log: tail -f logs/backend.log${NC}"
cd ..
sleep 3

# Setup Frontend
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🎨 Deploying Frontend...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd frontend
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}   Installing dependencies...${NC}"
    npm install
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}   Creating .env from .env.example...${NC}"
    cp .env.example .env
fi

# Install serve if not already installed
if ! command -v serve &> /dev/null; then
    echo -e "${YELLOW}   Installing serve (production static file server)...${NC}"
    npm install -g serve
fi

# Build for production
echo -e "${YELLOW}   Building production bundle...${NC}"
npm run build

# Start production server using 'serve' (much more stable than vite preview)
echo -e "${YELLOW}   Starting production server...${NC}"
nohup serve -s dist -l 5173 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../pids/frontend.pid
echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "${CYAN}   📝 Log: tail -f logs/frontend.log${NC}"
cd ..

# Wait for services to be ready
echo ""
echo -e "${CYAN}⏳ Waiting for services to initialize...${NC}"
sleep 5

# Health check
echo ""
echo -e "${CYAN}🏥 Performing health checks...${NC}"

# Check if processes are running
check_process() {
    local pid=$1
    local name=$2
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ $name is running (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}   ❌ $name failed to start${NC}"
        return 1
    fi
}

HEALTH_OK=true
check_process $AGENT_PID "AgentCore" || HEALTH_OK=false
check_process $BACKEND_PID "Backend" || HEALTH_OK=false
check_process $FRONTEND_PID "Frontend" || HEALTH_OK=false

echo ""

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Production deployment successful!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}📍 Service URLs:${NC}"
    echo -e "   ${YELLOW}Frontend:${NC}     http://localhost:5173"
    echo -e "   ${YELLOW}Backend API:${NC}  http://localhost:8000"
    echo -e "   ${YELLOW}API Docs:${NC}     http://localhost:8000/docs"
    echo -e "   ${YELLOW}AgentCore:${NC}    http://localhost:8080"
    echo ""
    echo -e "${CYAN}📝 Login Credentials:${NC}"
    echo -e "   ${YELLOW}Username:${NC}     admin"
    echo -e "   ${YELLOW}Password:${NC}     admin123"
    echo ""
    echo -e "${CYAN}📋 Process Management:${NC}"
    echo -e "   ${YELLOW}View logs:${NC}    tail -f logs/agent.log"
    echo -e "   ${YELLOW}              ${NC}    tail -f logs/backend.log"
    echo -e "   ${YELLOW}              ${NC}    tail -f logs/frontend.log"
    echo -e "   ${YELLOW}Stop all:${NC}     ./stop.sh"
    echo -e "   ${YELLOW}Restart:${NC}      ./stop.sh && ./production.sh"
    echo ""
    echo -e "${CYAN}💾 PID Files:${NC}"
    echo -e "   ${YELLOW}AgentCore:${NC}    pids/agent.pid"
    echo -e "   ${YELLOW}Backend:${NC}      pids/backend.pid"
    echo -e "   ${YELLOW}Frontend:${NC}     pids/frontend.pid"
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Check if user wants to disable monitoring (monitoring is ON by default)
    if [ "$1" == "--no-monitor" ] || [ "$1" == "-n" ]; then
        echo -e "${YELLOW}⚠️  Monitoring disabled - services will NOT auto-restart${NC}"
        echo -e "${PURPLE}   Use './stop.sh' to stop services${NC}"
        echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${CYAN}💡 Services are running in background${NC}"
        echo ""
    else
        # MONITORING ENABLED BY DEFAULT
        echo -e "${CYAN}👁️  Monitoring enabled - services will auto-restart if they crash${NC}"

        # Check if running under nohup (for EC2/server deployments)
        if [ -t 1 ]; then
            echo -e "${YELLOW}⌨️  Press Ctrl+C to stop all services${NC}"
        else
            echo -e "${CYAN}🖥️  Running in background mode (EC2/server)${NC}"
            echo -e "${YELLOW}💡 Monitor logs: tail -f logs/monitor.log${NC}"
            echo -e "${YELLOW}💡 Stop services: ./stop.sh${NC}"
        fi
        echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        # Monitoring configuration
        declare -A RESTART_COUNT
        RESTART_COUNT[agent]=0
        RESTART_COUNT[backend]=0
        RESTART_COUNT[frontend]=0
        MAX_RESTARTS=5
        CHECK_INTERVAL=10
        MONITOR_LOG="logs/monitor.log"

        # Initialize monitor log
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitoring started" >> $MONITOR_LOG

        # Cleanup handler
        cleanup_monitor() {
            echo "" | tee -a $MONITOR_LOG
            echo -e "${YELLOW}🛑 Shutting down all services...${NC}" | tee -a $MONITOR_LOG
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitoring stopped - shutting down services" >> $MONITOR_LOG
            ./stop.sh
            exit 0
        }

        trap cleanup_monitor SIGINT SIGTERM

        # Service restart function
        restart_service() {
            local service=$1
            local name=$2

            RESTART_COUNT[$service]=$((RESTART_COUNT[$service] + 1))

            if [ ${RESTART_COUNT[$service]} -gt $MAX_RESTARTS ]; then
                echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $name crashed $MAX_RESTARTS times. Stopping.${NC}" | tee -a $MONITOR_LOG
                cleanup_monitor
            fi

            echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $name crashed! Restarting (${RESTART_COUNT[$service]}/$MAX_RESTARTS)...${NC}" | tee -a $MONITOR_LOG

            case $service in
                "agent")
                    cd agent && source .venv/bin/activate && \
                    nohup python -u full_course_processor.py > ../logs/agent.log 2>&1 & \
                    echo $! > ../pids/agent.pid && cd ..
                    ;;
                "backend")
                    cd backend && source venv/bin/activate && \
                    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 & \
                    echo $! > ../pids/backend.pid && cd ..
                    ;;
                "frontend")
                    kill_port 5173 &>/dev/null
                    cd frontend && \
                    nohup serve -s dist -l 5173 > ../logs/frontend.log 2>&1 & \
                    echo $! > ../pids/frontend.pid && cd ..
                    ;;
            esac

            sleep 2
            new_pid=$(cat "pids/${service}.pid" 2>/dev/null)
            echo -e "${GREEN}[$(date '+%H:%M:%S')] ✅ $name restarted (PID: $new_pid)${NC}" | tee -a $MONITOR_LOG
        }

        # Health check function
        check_service() {
            local service=$1
            local name=$2
            local pid_file="pids/${service}.pid"

            if [ ! -f "$pid_file" ]; then
                echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $name: PID file missing${NC}" | tee -a $MONITOR_LOG
                restart_service "$service" "$name"
                return
            fi

            local pid=$(cat "$pid_file" 2>/dev/null)
            if ! ps -p $pid > /dev/null 2>&1; then
                echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $name: Process died (PID: $pid)${NC}" | tee -a $MONITOR_LOG
                restart_service "$service" "$name"
            fi
        }

        # Start monitoring
        echo -e "${GREEN}✅ Monitoring started. Checking every ${CHECK_INTERVAL}s...${NC}" | tee -a $MONITOR_LOG
        echo ""

        while true; do
            check_service "agent" "AgentCore"
            check_service "backend" "Backend"
            check_service "frontend" "Frontend"
            sleep $CHECK_INTERVAL
        done
    fi
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Some services failed to start. Check logs for details.${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
