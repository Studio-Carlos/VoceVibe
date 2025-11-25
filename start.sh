#!/bin/bash
# VoiceVibe4 Startup Script
# Kills all previous instances before launching

echo "=========================================="
echo "🚀 VoiceVibe4 Startup Script"
echo "=========================================="
echo ""

# Kill all previous instances
echo "🛑 Killing all previous instances..."
pkill -9 -f "python.*main.py" 2>/dev/null
pkill -9 -f "monitor.sh" 2>/dev/null
sleep 2

# Verify they're all dead
REMAINING=$(ps aux | grep -E "python.*main.py" | grep -v grep | wc -l | tr -d ' ')
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  Warning: $REMAINING instance(s) still running, forcing kill..."
    ps aux | grep -E "python.*main.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "✅ All previous instances killed"
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv .venv"
    exit 1
fi

# Activate venv and launch
echo "🚀 Launching VoiceVibe4..."
echo ""

cd "$(dirname "$0")"
source .venv/bin/activate

# Ensure PyTorch can fall back to CPU for unsupported MPS ops
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Launch in background with logging (UNBUFFERED output)
nohup python -u main.py > /tmp/voicevibe4.log 2>&1 &
APP_PID=$!

# Save PID
echo $APP_PID > /tmp/voicevibe4.pid

sleep 2

# Verify it's running
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ Application launched successfully!"
    echo "   PID: $APP_PID"
    echo "   Logs: /tmp/voicevibe4.log"
    echo ""
    echo "📊 To monitor logs:"
    echo "   tail -f /tmp/voicevibe4.log"
    echo ""
    echo "🛑 To stop:"
    echo "   kill $APP_PID"
    echo "   or: ./stop.sh"
    echo ""
    echo "=========================================="
else
    echo "❌ Failed to launch application"
    echo "   Check logs: /tmp/voicevibe4.log"
    tail -20 /tmp/voicevibe4.log 2>/dev/null
    exit 1
fi
