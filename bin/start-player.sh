#!/bin/bash
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"
echo "$LOG_PREFIX Starting Pi Player Fullscreen Kiosk"
echo "$LOG_PREFIX Display environment: $DISPLAY"

# Wait briefly for X server
for i in {1..30}; do
  if xset q >/dev/null 2>&1; then break; fi
  sleep 1
done

pkill -f pcmanfm || true
xset s off || true
xset -dpms || true
xset s noblank || true
unclutter -idle 0 -root >/dev/null 2>&1 &
sleep 1

cd /home/pi/connect
exec python3 player.py
