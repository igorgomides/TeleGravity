#!/bin/bash
# Stop any running instances of bot.py for this directory
PID=$(pgrep -f "bot.py")
if [ ! -z "$PID" ]; then
    echo "Stopping existing bot instance(s) (PID: $PID)..."
    kill -9 $PID
    sleep 2
fi

echo "Starting TeleGravity bot..."
nohup /opt/alt/python311/bin/python3 bot.py > bot.log 2>&1 &
echo "Bot started in background. Logs are written to bot.log."
