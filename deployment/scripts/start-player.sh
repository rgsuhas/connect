#!/bin/bash
set -e

# Pi Player Fullscreen Kiosk Startup Script
# This script ensures the media player takes over the full screen

# Colors for logging
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" >> /home/pi/connect/logs/kiosk.log
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >> /home/pi/connect/logs/kiosk.log
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" >> /home/pi/connect/logs/kiosk.log
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Ensure log directory exists
mkdir -p /home/pi/connect/logs

log "Starting Pi Player Fullscreen Kiosk"

# Set display environment
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

log "Display environment: DISPLAY=$DISPLAY"

# Wait for X server to be ready
log "Waiting for X server to be ready..."
timeout=30
while [ $timeout -gt 0 ]; do
    if xdpyinfo >/dev/null 2>&1; then
        log "X server is ready"
        break
    fi
    sleep 1
    timeout=$((timeout-1))
done

if [ $timeout -eq 0 ]; then
    error "X server not available after 30 seconds"
    exit 1
fi

# Kill desktop file manager to free up the screen
log "Stopping desktop file manager..."
pkill -f "pcmanfm.*desktop" || true

# Disable screen blanking and hide cursor
log "Configuring display settings..."
xset s off -dpms 2>/dev/null || warning "Could not disable screen blanking"

# Install unclutter if not present and hide cursor
if command -v unclutter >/dev/null 2>&1; then
    unclutter -idle 0 -root &
    log "Cursor hidden with unclutter"
else
    warning "unclutter not installed - cursor will be visible"
fi

# Wait a moment for desktop to stop
sleep 2

# Start the Python media player
log "Starting Python media player..."
cd /home/pi/connect

# Try to start the media player
if [ -f "/home/pi/connect/venv/bin/python" ]; then
    log "Using virtual environment Python"
    exec /home/pi/connect/venv/bin/python /home/pi/connect/player.py
elif [ -f "/home/pi/connect/player.py" ]; then
    log "Using system Python"
    exec /usr/bin/python3 /home/pi/connect/player.py
else
    error "player.py not found"
    
    # Fallback: Show a simple fullscreen image
    log "Starting fallback fullscreen display..."
    if [ -f "/home/pi/connect/default_assets/default_screen.png" ]; then
        exec feh --fullscreen --hide-pointer --zoom fill /home/pi/connect/default_assets/default_screen.png
    else
        error "No fallback media available"
        exit 1
    fi
fi
