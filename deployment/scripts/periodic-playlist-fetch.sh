#!/bin/bash
set -e

# Periodic Backend Playlist Fetcher
# Fetches playlist from backend every few minutes

SCRIPT_DIR="/home/pi/connect"
LOG_FILE="$SCRIPT_DIR/logs/playlist_fetch.log"
FETCH_SCRIPT="$SCRIPT_DIR/fetch_backend_playlist.py"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting periodic playlist fetch"

cd "$SCRIPT_DIR"

# Try to fetch new playlist
if python3 -c "import sys; sys.path.append('.'"); from fetch_backend_playlist import fetch_and_save_backend_playlist_with_cleanup; fetch_and_save_backend_playlist_with_cleanup()" >> "$LOG_FILE" 2>&1; then
    log "✅ Playlist fetch completed successfully"
else
    log "❌ Playlist fetch failed"
fi

log "Periodic playlist fetch finished"
