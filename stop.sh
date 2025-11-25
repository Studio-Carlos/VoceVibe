#!/bin/bash
# VoiceVibe4 Stop Script

echo "🛑 Stopping VoiceVibe4..."

# Kill by PID if exists
if [ -f /tmp/voicevibe4.pid ]; then
    PID=$(cat /tmp/voicevibe4.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null
        echo "✅ Stopped process $PID"
    fi
    rm -f /tmp/voicevibe4.pid
fi

# Kill all instances
pkill -9 -f "python.*main.py" 2>/dev/null
pkill -9 -f "monitor.sh" 2>/dev/null

sleep 1

REMAINING=$(ps aux | grep -E "python.*main.py" | grep -v grep | wc -l | tr -d ' ')
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All instances stopped"
else
    echo "⚠️  $REMAINING instance(s) still running"
fi

