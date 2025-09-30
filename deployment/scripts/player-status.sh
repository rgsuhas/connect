#!/bin/bash
# Pi Player Status Checker

echo "🎮 Pi Player Status"
echo "==================="

echo
echo "📺 Current Playback:"
if pgrep -f vlc >/dev/null; then
    VLC_PROCESS=$(ps aux | grep vlc | grep -v grep | head -1)
    echo "  Status: ▶️  PLAYING"
    CURRENT_FILE=$(echo "$VLC_PROCESS" | grep -o '/[^[:space:]]*\.mp4' | tail -1)
    if [[ -n "$CURRENT_FILE" ]]; then
        FILENAME=$(basename "$CURRENT_FILE")
        FILESIZE=$(ls -lh "$CURRENT_FILE" 2>/dev/null | awk '{print $5}')
        echo "  File: $FILENAME ($FILESIZE)"
    fi
elif pgrep -f feh >/dev/null; then
    echo "  Status: 🖼️  SHOWING DEFAULT SCREEN"
else
    echo "  Status: ⏸️  STOPPED/IDLE"
fi

echo
echo "📋 Current Playlist:"
if [[ -f /home/pi/connect/current_playlist.json ]]; then
    cd /home/pi/connect
    python3 -c "
import json
try:
    with open('current_playlist.json') as f:
        pl = json.load(f)
    print(f'  Version: {pl.get(\"version\", \"unknown\")}')
    print(f'  Source: {pl.get(\"source\", \"unknown\")}')
    print(f'  Items: {len(pl.get(\"items\", []))}')
    print(f'  Loop: {\"Yes\" if pl.get(\"loop\", False) else \"No\"}')
    print(f'  Updated: {pl.get(\"last_updated\", \"unknown\")}')
    for i, item in enumerate(pl.get('items', []), 1):
        print(f'    {i}. {item.get(\"filename\", \"unknown\")} ({item.get(\"duration\", \"?\")}s)')
except Exception as e:
    print(f'  Error: {e}')
"
else
    echo "  No playlist file found"
fi

echo
echo "💾 Cache Status:"
if [[ -d /home/pi/connect/media_cache ]]; then
    CACHE_COUNT=$(ls -1 /home/pi/connect/media_cache | grep -v '.gitkeep' | wc -l)
    CACHE_SIZE=$(du -sh /home/pi/connect/media_cache 2>/dev/null | cut -f1)
    echo "  Files: $CACHE_COUNT"
    echo "  Size: $CACHE_SIZE"
    echo "  Files:"
    ls -lh /home/pi/connect/media_cache | grep -v '.gitkeep' | grep -v '^total' | awk '{print "    " $9 " (" $5 ")"}'
else
    echo "  Cache directory not found"
fi

echo
echo "⚙️  Service Status:"
systemctl is-active pi-player-kiosk.service >/dev/null && echo "  pi-player-kiosk: ✅ RUNNING" || echo "  pi-player-kiosk: ❌ STOPPED"

echo
echo "🔄 Next playlist check in:"
NEXT_CRON=$(( 5 - $(date +%M) % 5 ))
echo "  ~$NEXT_CRON minutes (every 5 minutes)"
