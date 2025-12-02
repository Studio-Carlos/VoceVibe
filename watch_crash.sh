#!/bin/bash
# Monitor application for crashes

PID_FILE="/tmp/voicevibe.pid"
LOG_FILE="/tmp/voicevibe.log"

echo "🔍 Monitoring VoiceVibe for crashes..."
echo ""

while true; do
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "❌ CRASH DETECTED! Process $PID is not running"
            echo ""
            echo "📋 Last 30 lines of log:"
            tail -30 "$LOG_FILE" 2>/dev/null
            echo ""
            echo "🔄 Restarting application..."
            cd "$(dirname "$0")"
            ./start.sh
            sleep 3
        else
            echo "✅ Process $PID is running ($(date +%H:%M:%S))"
        fi
    else
        echo "⚠️  No PID file found"
    fi
    sleep 5
done

