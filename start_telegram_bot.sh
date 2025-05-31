#!/bin/bash
cd /home/runner/workspace
export PYTHONPATH=/home/runner/workspace
nohup python3 telegram_monitor.py > telegram_bot.log 2>&1 &
echo "Telegram bot started with PID: $!"
sleep 2
tail -10 telegram_bot.log