#!/bin/bash
# VoiceVibe Monitoring Script
# Checks status, logs, and resources

echo "🔍 VoiceVibe Status Monitor"
echo "=========================================="
echo ""

# Check if running (multiple patterns to catch all cases)
INSTANCES=$(ps aux | grep -E "(python.*main\.py|Python.*main\.py|main\.py)" | grep -v grep)
if [ -z "$INSTANCES" ]; then
    echo "❌ No instances running"
    echo ""
    echo "💡 To start: ./start.sh"
    exit 0
fi

COUNT=$(echo "$INSTANCES" | wc -l | tr -d ' ')
echo "✅ $COUNT instance(s) running:"
echo "$INSTANCES" | awk '{print "   PID:", $2, "| CPU:", $3"%", "| MEM:", $4"%", "| Time:", $10}'
echo ""

# Check PID file
if [ -f /tmp/voicevibe.pid ]; then
    SAVED_PID=$(cat /tmp/voicevibe.pid)
    if ps -p $SAVED_PID > /dev/null 2>&1; then
        echo "✅ Main instance (from PID file): $SAVED_PID"
    else
        echo "⚠️  PID file exists but process not running: $SAVED_PID"
    fi
fi
echo ""

# Check logs
if [ -f /tmp/voicevibe.log ]; then
    LOG_SIZE=$(wc -l < /tmp/voicevibe.log | tr -d ' ')
    echo "📋 Log file: /tmp/voicevibe.log ($LOG_SIZE lines)"
    echo ""
    echo "📊 Recent activity (last 10 lines):"
    tail -10 /tmp/voicevibe.log 2>/dev/null | sed 's/^/   /'
else
    echo "⚠️  No log file found"
fi
echo ""

# Check GPU memory if available
if command -v python3 &> /dev/null; then
    echo "🧠 GPU Memory (MPS):"
    python3 -c "
import torch
try:
    if torch.backends.mps.is_available():
        allocated = torch.mps.current_allocated_memory() / (1024**3)
        print(f'   Allocated: {allocated:.2f} GB')
    else:
        print('   MPS not available')
except:
    print('   Unable to check')
" 2>/dev/null || echo "   Unable to check"
fi
echo ""

echo "=========================================="
echo "💡 Commands:"
echo "   ./start.sh  - Start application"
echo "   ./stop.sh   - Stop all instances"
echo "   tail -f /tmp/voicevibe.log - Watch logs"
echo "=========================================="
