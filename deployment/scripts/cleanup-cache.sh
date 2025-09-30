#!/bin/bash
# Manual cache cleanup script

cd /home/pi/connect
echo "🧹 Manual Cache Cleanup"
echo "======================="
python3 cleanup_old_cache.py "$@"
