#!/bin/bash
set -euo pipefail

# Deploy Pi Player files to /home/pi/connect for Raspberry Pi
# This script fixes the path issues and deploys everything correctly

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                     Pi Player Deploy to Connect                             ║"
echo "║                                                                              ║"
echo "║  Deploying files to /home/pi/connect with corrected paths                   ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/home/pi/connect"

# Check if running as correct user or with sudo
if [[ $EUID -eq 0 ]]; then
    SUDO_PREFIX=""
else
    SUDO_PREFIX="sudo"
    log "Using sudo for file operations"
fi

# Create target directory structure
log "Creating directory structure..."
$SUDO_PREFIX mkdir -p "$TARGET_DIR"
$SUDO_PREFIX mkdir -p "$TARGET_DIR/media_cache"
$SUDO_PREFIX mkdir -p "$TARGET_DIR/logs"
$SUDO_PREFIX mkdir -p "$TARGET_DIR/services"
$SUDO_PREFIX mkdir -p "$TARGET_DIR/default_assets"

# Copy Python files
log "Copying Python application files..."
$SUDO_PREFIX cp -v "$SCRIPT_DIR"/*.py "$TARGET_DIR/" || {
    error "Failed to copy Python files"
    exit 1
}

# Copy shell scripts
log "Copying shell scripts..."
$SUDO_PREFIX cp -v "$SCRIPT_DIR"/*.sh "$TARGET_DIR/" || {
    warning "Some shell scripts may not be available"
}

# Copy service files
log "Copying systemd service files..."
$SUDO_PREFIX cp -v "$SCRIPT_DIR/services/"*.service "$TARGET_DIR/services/" || {
    warning "Service files not found in $SCRIPT_DIR/services/"
}

# Install service files to systemd
log "Installing systemd services..."
if [[ -f "$TARGET_DIR/services/pi-player.service" ]]; then
    $SUDO_PREFIX cp "$TARGET_DIR/services/pi-player.service" /etc/systemd/system/
    success "Installed pi-player.service"
fi

if [[ -f "$TARGET_DIR/services/media-player.service" ]]; then
    $SUDO_PREFIX cp "$TARGET_DIR/services/media-player.service" /etc/systemd/system/
    success "Installed media-player.service"
fi

# Set correct permissions
log "Setting correct permissions..."
$SUDO_PREFIX chown -R pi:pi "$TARGET_DIR" 2>/dev/null || {
    warning "Could not set pi:pi ownership, trying current user"
    $SUDO_PREFIX chown -R $(whoami):$(whoami) "$TARGET_DIR" 2>/dev/null || {
        warning "Could not set ownership, continuing anyway"
    }
}

$SUDO_PREFIX chmod +x "$TARGET_DIR"/*.py

# Create utility scripts
log "Creating utility scripts..."

# Status script
cat > "/tmp/status.sh" << 'EOF'
#!/bin/bash
echo "Pi Player System Status"
echo "======================"
echo
echo "Services:"
systemctl is-active pi-player.service | sed 's/^/  pi-player: /'
systemctl is-active media-player.service | sed 's/^/  media-player: /'
echo
echo "API Status:"
curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool || echo "  API not responding"
echo
echo "Logs (last 5 lines):"
echo "  API Server:"
tail -5 /home/pi/connect/logs/pi_server.log 2>/dev/null | sed 's/^/    /' || echo "    No logs found"
echo "  Media Player:"
tail -5 /home/pi/connect/logs/media_player.log 2>/dev/null | sed 's/^/    /' || echo "    No logs found"
EOF

$SUDO_PREFIX mv /tmp/status.sh "$TARGET_DIR/status.sh"
$SUDO_PREFIX chmod +x "$TARGET_DIR/status.sh"

# Restart script
cat > "/tmp/restart.sh" << 'EOF'
#!/bin/bash
echo "Restarting Pi Player services..."
sudo systemctl daemon-reload
sudo systemctl restart pi-player.service
sudo systemctl restart media-player.service
echo "Services restarted"
sleep 2
echo "Checking status..."
systemctl is-active pi-player.service
systemctl is-active media-player.service
EOF

$SUDO_PREFIX mv /tmp/restart.sh "$TARGET_DIR/restart.sh"
$SUDO_PREFIX chmod +x "$TARGET_DIR/restart.sh"

# Test playlist script
log "Creating test playlist..."
cat > "/tmp/create_test_playlist.py" << 'EOF'
#!/usr/bin/env python3
import json
import sys
import os
sys.path.insert(0, '/home/pi/connect')

try:
    from playlist_manager import get_playlist_manager
    
    print("Creating default Cloudinary playlist...")
    manager = get_playlist_manager()
    success = manager.load_default_playlist(use_cloudinary=True)
    
    if success:
        print("✅ Default Cloudinary playlist created successfully!")
        print("   Your 7 collection URLs are now available as fallback content")
        status = manager.get_playlist_status()
        print(f"   Playlist source: {status.get('current_source')}")
        if 'current_playlist' in status:
            print(f"   Items: {status['current_playlist'].get('item_count', 0)}")
    else:
        print("❌ Failed to create default playlist")
        
except Exception as e:
    print(f"Error: {e}")
    print("Creating simple fallback...")
    
    # Fallback: create playlist manually
    from datetime import datetime
    playlist = {
        "version": "manual-fallback-v1.0",
        "last_updated": datetime.now().isoformat(),
        "loop": True,
        "description": "Manual fallback playlist with Cloudinary collections",
        "source": "manual_fallback",
        "items": [
            {
                "filename": f"cloudinary_collection_{i}.mp4",
                "url": url,
                "duration": 30,
                "checksum": None,
                "metadata": {"collection_id": url.split('/')[-1]}
            }
            for i, url in enumerate([
                "https://collection.cloudinary.com/dxfhfpaym/8006a0aeec057b5fdae295b27ea0f1e2",
                "https://collection.cloudinary.com/dxfhfpaym/a8763aa70fe1ae9284552d3b2aba5ebf",
                "https://collection.cloudinary.com/dxfhfpaym/173ef9cfc1e34d25a3241c1bfdc6c733",
                "https://collection.cloudinary.com/dxfhfpaym/329afc666ff08426da6c2f2f2a529ea8",
                "https://collection.cloudinary.com/dxfhfpaym/d4ac678778867b5fbe15e2a1f10fb589",
                "https://collection.cloudinary.com/dxfhfpaym/152008e9ff99a72cb8de06f125dab9b8",
                "https://collection.cloudinary.com/dxfhfpaym/9a919c47d389473ff2d9b4ceff7b1093"
            ], 1)
        ]
    }
    
    with open('/home/pi/connect/current_playlist.json', 'w') as f:
        json.dump(playlist, f, indent=2)
    
    print("✅ Manual fallback playlist created!")
    print(f"   Items: {len(playlist['items'])}")
EOF

$SUDO_PREFIX mv /tmp/create_test_playlist.py "$TARGET_DIR/create_test_playlist.py"
$SUDO_PREFIX chmod +x "$TARGET_DIR/create_test_playlist.py"

# Reload systemd and restart services
log "Reloading systemd and restarting services..."
$SUDO_PREFIX systemctl daemon-reload

# Enable services
$SUDO_PREFIX systemctl enable pi-player.service || warning "Failed to enable pi-player.service"
$SUDO_PREFIX systemctl enable media-player.service || warning "Failed to enable media-player.service"

# Stop services first (in case they were running with wrong paths)
$SUDO_PREFIX systemctl stop pi-player.service 2>/dev/null || true
$SUDO_PREFIX systemctl stop media-player.service 2>/dev/null || true

# Start services
log "Starting pi-player.service..."
if $SUDO_PREFIX systemctl start pi-player.service; then
    success "Pi Player API service started"
else
    error "Pi Player API service failed to start"
    $SUDO_PREFIX systemctl status pi-player.service --no-pager --lines=5
fi

log "Starting media-player.service..."
if $SUDO_PREFIX systemctl start media-player.service; then
    success "Media Player daemon started"
else
    warning "Media Player daemon may have issues (normal if no display)"
    $SUDO_PREFIX systemctl status media-player.service --no-pager --lines=5
fi

# Create test playlist
log "Creating default playlist..."
cd "$TARGET_DIR"
python3 create_test_playlist.py

# Final status
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                            Deployment Complete!                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo

echo "📍 Files deployed to: $TARGET_DIR"
echo "🔧 Utility scripts:"
echo "   Status check: $TARGET_DIR/status.sh"
echo "   Restart services: $TARGET_DIR/restart.sh"
echo "   Test playlist: $TARGET_DIR/create_test_playlist.py"
echo
echo "🌐 API Endpoints:"
echo "   Health: http://$(hostname -I | awk '{print $1}' || echo localhost):8000/health"
echo "   Playlist: http://$(hostname -I | awk '{print $1}' || echo localhost):8000/playlist"
echo "   API Docs: http://$(hostname -I | awk '{print $1}' || echo localhost):8000/docs"
echo
echo "🧪 Test commands:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:8000/playlist"
echo "   $TARGET_DIR/status.sh"
echo
success "Pi Player with Cloudinary fallback is now deployed!"