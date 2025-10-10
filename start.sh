#!/bin/bash

# MyTutor Complete Application Starter
# Starts all three services: AgentCore, Backend, Frontend

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
echo -e "${PURPLE}║                   🎓 MyTutor Starter 🎓                    ║${NC}"
echo -e "${PURPLE}║                                                            ║${NC}"
echo -e "${PURPLE}║      AI-Powered Course Learning Platform with AgentCore    ║${NC}"
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
        sleep 1
    fi
}

# Kill any existing processes on required ports
echo -e "${CYAN}🔍 Checking and cleaning up ports...${NC}"
kill_port 8080  # AgentCore
kill_port 8000  # Backend
kill_port 5173  # Frontend
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

# Create logs directory
mkdir -p logs

# Setup AgentCore
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🤖 Setting up AgentCore Runtime...${NC}"
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

python -u full_course_processor.py > ../logs/agent.log 2>&1 &
AGENT_PID=$!
echo -e "${GREEN}✅ AgentCore started (PID: $AGENT_PID)${NC}"
cd ..
sleep 2

# Setup Backend
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}⚙️  Setting up Backend API...${NC}"
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

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
cd ..
sleep 2

# Setup Frontend
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🎨 Setting up Frontend...${NC}"
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

npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
cd ..

# Wait for services to be ready
echo ""
echo -e "${CYAN}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Display status
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All services started successfully!${NC}"
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
echo -e "${CYAN}📋 Process IDs:${NC}"
echo -e "   ${YELLOW}AgentCore:${NC}    $AGENT_PID"
echo -e "   ${YELLOW}Backend:${NC}      $BACKEND_PID"
echo -e "   ${YELLOW}Frontend:${NC}     $FRONTEND_PID"
echo ""
echo -e "${CYAN}📁 Logs:${NC}"
echo -e "   ${YELLOW}AgentCore:${NC}    tail -f logs/agent.log"
echo -e "   ${YELLOW}Backend:${NC}      tail -f logs/backend.log"
echo -e "   ${YELLOW}Frontend:${NC}     tail -f logs/frontend.log"
echo ""
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}Press Ctrl+C to stop all services${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down all services...${NC}"

    echo -e "${CYAN}   Stopping AgentCore (PID: $AGENT_PID)...${NC}"
    kill $AGENT_PID 2>/dev/null || true

    echo -e "${CYAN}   Stopping Backend (PID: $BACKEND_PID)...${NC}"
    kill $BACKEND_PID 2>/dev/null || true

    echo -e "${CYAN}   Stopping Frontend (PID: $FRONTEND_PID)...${NC}"
    kill $FRONTEND_PID 2>/dev/null || true

    sleep 2
    kill -9 $AGENT_PID 2>/dev/null || true
    kill -9 $BACKEND_PID 2>/dev/null || true
    kill -9 $FRONTEND_PID 2>/dev/null || true

    echo -e "${GREEN}✅ All services stopped${NC}"
    echo ""
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
