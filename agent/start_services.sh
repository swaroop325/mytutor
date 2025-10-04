#!/bin/bash

# Start all agent services
# - Course Processor Agent (port 8080)
# - Browser Viewer Service (port 8081)

set -e

echo "🚀 Starting MyTutor Agent Services..."

# Activate virtual environment
source .venv/bin/activate

# Start Browser Viewer Service in background
echo "📺 Starting Browser Viewer Service on port 8081..."
python browser_viewer.py &
VIEWER_PID=$!

# Wait a bit
sleep 2

# Start Course Processor Agent
echo "🤖 Starting Course Processor Agent on port 8080..."
python course_processor.py &
PROCESSOR_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $VIEWER_PID 2>/dev/null || true
    kill $PROCESSOR_PID 2>/dev/null || true
    echo "✅ Services stopped"
    exit 0
}

# Register cleanup function
trap cleanup SIGINT SIGTERM

echo ""
echo "✅ All services started!"
echo "   - Course Processor: http://localhost:8080"
echo "   - Browser Viewer: http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait
