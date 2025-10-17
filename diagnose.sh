#!/bin/bash

# MyTutor Diagnostic Script for Lightsail
# Run this on your Lightsail instance to diagnose frontend issues

echo "======================================"
echo "MyTutor Frontend Diagnostic Report"
echo "======================================"
echo ""

# Check memory
echo "1. MEMORY STATUS:"
free -h 2>/dev/null || vm_stat 2>/dev/null || echo "Memory check not available"
echo ""

# Check disk space
echo "2. DISK SPACE:"
df -h .
echo ""

# Check if dist directory exists
echo "3. FRONTEND BUILD STATUS:"
if [ -d "frontend/dist" ]; then
    echo "✓ dist directory exists"
    echo "  Size: $(du -sh frontend/dist | cut -f1)"
    echo "  Files: $(find frontend/dist -type f | wc -l)"
else
    echo "✗ dist directory NOT FOUND - build may have failed"
fi
echo ""

# Check if serve is installed
echo "4. SERVE INSTALLATION:"
if command -v serve &> /dev/null; then
    echo "✓ serve is installed"
    echo "  Version: $(serve --version 2>&1 | head -1)"
else
    echo "✗ serve is NOT installed"
fi
echo ""

# Check port 5173
echo "5. PORT 5173 STATUS:"
if lsof -ti:5173 > /dev/null 2>&1; then
    echo "⚠ Port 5173 is IN USE:"
    lsof -ti:5173 | while read pid; do
        echo "  PID: $pid"
        ps -p $pid -o command= 2>/dev/null || echo "  Process info not available"
    done
else
    echo "✓ Port 5173 is FREE"
fi
echo ""

# Check logs
echo "6. RECENT FRONTEND LOGS:"
if [ -f "logs/frontend.log" ]; then
    echo "Last 15 lines:"
    tail -15 logs/frontend.log
else
    echo "No frontend log file found"
fi
echo ""

# Check system logs for OOM killer
echo "7. CHECKING FOR OOM (Out of Memory) KILLS:"
if [ -f "/var/log/syslog" ]; then
    grep -i "killed process\|out of memory" /var/log/syslog | tail -5 || echo "No OOM kills found"
elif [ -f "/var/log/messages" ]; then
    grep -i "killed process\|out of memory" /var/log/messages | tail -5 || echo "No OOM kills found"
else
    dmesg 2>/dev/null | grep -i "killed process\|out of memory" | tail -5 || echo "Cannot check OOM logs (may need sudo)"
fi
echo ""

# Check running processes
echo "8. CURRENT MYTUTOR PROCESSES:"
ps aux | grep -E "(python.*full_course|uvicorn|serve|vite)" | grep -v grep || echo "No MyTutor processes running"
echo ""

# Check PID files
echo "9. PID FILES STATUS:"
for service in agent backend frontend; do
    pidfile="pids/${service}.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile" 2>/dev/null)
        if [ -n "$pid" ]; then
            if ps -p $pid > /dev/null 2>&1; then
                echo "✓ $service (PID: $pid) - RUNNING"
            else
                echo "✗ $service (PID: $pid) - NOT RUNNING (stale PID)"
            fi
        else
            echo "✗ $service - EMPTY PID FILE"
        fi
    else
        echo "- $service - NO PID FILE"
    fi
done
echo ""

echo "======================================"
echo "Diagnostic Complete"
echo "======================================"
