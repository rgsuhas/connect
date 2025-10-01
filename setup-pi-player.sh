#!/bin/bash

# Pi Player Kiosk Setup Script
# This script sets up the complete pi-player digital signage system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_USER="pi"
INSTALL_DIR="/home/pi/connect"
SERVICE_NAME="pi-player-kiosk"
BACKEND_URL=""

print_header() {
    echo -e "${BLUE}"
    echo "============================================="
    echo "  Pi Player Digital Signage Setup Script"
    echo "============================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_step "Checking system requirements..."
    
    # Check if running as pi user
    if [ "$USER" != "$PI_USER" ]; then
        print_error "This script must be run as the 'pi' user"
        exit 1
    fi
    
    # Check if running on Raspberry Pi OS
    if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        print_warning "Not detected as Raspberry Pi - continuing anyway"
    fi
    
    # Check internet connection
    if ! ping -c 1 google.com &> /dev/null; then
        print_error "No internet connection available"
        exit 1
    fi
    
    print_info "System requirements check passed"
}

install_system_packages() {
    print_step "Installing system packages..."
    
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        mpv \
        vlc \
        ffmpeg \
        feh \
        unclutter \
        git \
        curl \
        systemd
    
    print_info "System packages installed"
}

setup_directories() {
    print_step "Setting up project directories..."
    
    # Create main directory if it doesn't exist
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    
    # Create required subdirectories
    mkdir -p media_cache
    mkdir -p default_assets
    mkdir -p logs
    mkdir -p bin
    
    print_info "Project directories created"
}

install_python_dependencies() {
    print_step "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f requirements.txt ]; then
        cat > requirements.txt << 'PYREQS'
requests==2.31.0
urllib3==2.0.7
Pillow==10.0.1
python-dateutil==2.8.2
PYREQS
    fi
    
    # Install Python packages
    pip3 install --user -r requirements.txt
    
    print_info "Python dependencies installed"
}

create_config_files() {
    print_step "Creating configuration files..."
    
    cd "$INSTALL_DIR"
    
    # Create config.py if it doesn't exist
    if [ ! -f config.py ]; then
        cat > config.py << 'PYCONFIG'
from pathlib import Path
import os

class Config:
    def __init__(self):
        # Base directory
        self.BASE_DIR = Path(__file__).parent.absolute()
        
        # Core directories
        self.MEDIA_CACHE_DIR = self.BASE_DIR / "media_cache"
        self.DEFAULT_ASSETS_DIR = self.BASE_DIR / "default_assets"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        
        # Ensure directories exist
        self.MEDIA_CACHE_DIR.mkdir(exist_ok=True)
        self.DEFAULT_ASSETS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        
        # Configuration files
        self.PLAYLIST_FILE = self.BASE_DIR / "current_playlist.json"
        self.STATE_FILE = self.BASE_DIR / "player_state.json"
        
        # Download settings
        self.MAX_CONCURRENT_DOWNLOADS = 3
        self.DOWNLOAD_TIMEOUT = 60
        self.DOWNLOAD_RETRY_ATTEMPTS = 3
        self.CHECKSUM_ALGORITHM = "sha256"
        
        # Backend settings
        self.BACKEND_URL = os.getenv("BACKEND_URL", "")
        self.FETCH_INTERVAL = 300  # 5 minutes
        
        # Player settings
        self.DEFAULT_DISPLAY_DURATION = 10
        self.LOOP_PLAYLIST = True
        
        # Logging settings
        self.LOG_LEVEL = "INFO"
        self.LOG_RETENTION_DAYS = 7
    
    def get_media_path(self, filename: str) -> Path:
        """Get full path for cached media file"""
        return self.MEDIA_CACHE_DIR / filename
    
    def get_log_path(self, component_name: str) -> Path:
        """Get log file path for a component"""
        return self.LOGS_DIR / f"{component_name}.log"
    
    def is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        return Path(filename).suffix.lower() in image_extensions
    
    def is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        return Path(filename).suffix.lower() in video_extensions

# Global config instance
config = Config()
PYCONFIG
    fi
    
    # Create empty playlist if it doesn't exist
    if [ ! -f current_playlist.json ]; then
        cat > current_playlist.json << 'PLAYLIST'
{
  "version": "v1.0.0",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")",
  "loop": true,
  "description": "Default playlist",
  "source": "setup_script",
  "items": []
}
PLAYLIST
    fi
    
    print_info "Configuration files created"
}

create_startup_scripts() {
    print_step "Creating startup scripts..."
    
    cd "$INSTALL_DIR"
    
    # Create start-player.sh script
    cat > bin/start-player.sh << 'STARTSCRIPT'
#!/bin/bash

# Pi Player Kiosk Startup Script

LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$LOG_PREFIX Starting Pi Player Fullscreen Kiosk"
echo "$LOG_PREFIX Display environment: $DISPLAY"

# Wait for X server to be ready
echo "$LOG_PREFIX Waiting for X server to be ready..."
for i in {1..30}; do
    if xset q >/dev/null 2>&1; then
        echo "$LOG_PREFIX X server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "$LOG_PREFIX ERROR: X server not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Stop desktop file manager to prevent interference
echo "$LOG_PREFIX Stopping desktop file manager..."
pkill -f pcmanfm || true

# Configure display settings
echo "$LOG_PREFIX Configuring display settings..."
xset s off         # Disable screensaver
xset -dpms         # Disable power management
xset s noblank     # Disable screen blanking

# Hide cursor
echo "$LOG_PREFIX Cursor hidden with unclutter"
unclutter -idle 0 -root &

# Wait a moment for settings to apply
sleep 2

# Start the Python media player
echo "$LOG_PREFIX Starting Python media player..."
echo "$LOG_PREFIX Using system Python"
cd /home/pi/connect
exec python3 player.py
STARTSCRIPT
    
    chmod +x bin/start-player.sh
    
    # Create start-downloads.sh script
    cat > bin/start-downloads.sh << 'DOWNLOADSCRIPT'
#!/bin/bash
cd /home/pi/connect
python3 -c "from download_manager import load_and_download_playlist; print('Starting downloads...'); res=load_and_download_playlist(); print('Downloads complete:', res)" > /home/pi/connect/logs/boot_download.log 2>&1 &
DOWNLOADSCRIPT
    
    chmod +x bin/start-downloads.sh
    
    print_info "Startup scripts created"
}

create_systemd_service() {
    print_step "Creating systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << SERVICEEOF
[Unit]
Description=Pi Player Fullscreen Kiosk
Documentation=https://github.com/rgsuhas/pi-player
After=graphical.target
Wants=graphical.target
StartLimitBurst=3
StartLimitIntervalSec=300

[Service]
Type=simple
User=$PI_USER
Group=$PI_USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$PI_USER/.Xauthority
Environment=HOME=/home/$PI_USER
WorkingDirectory=/home/$PI_USER
ExecStartPre=/usr/bin/env bash -lc 'cd $INSTALL_DIR && python3 -c "from fetch_backend_playlist import fetch_and_save_backend_playlist_with_cleanup; fetch_and_save_backend_playlist_with_cleanup()" 2>&1'
ExecStart=$INSTALL_DIR/bin/start-player.sh
ExecStartPost=$INSTALL_DIR/bin/start-downloads.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Allow access to display and audio devices
SupplementaryGroups=audio video render

# Security settings - less restrictive for GUI apps
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false

[Install]
WantedBy=graphical.target
SERVICEEOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME.service
    
    print_info "Systemd service created and enabled"
}

create_management_scripts() {
    print_step "Creating management scripts..."
    
    cd "$INSTALL_DIR"
    
    # Create player status script
    cat > bin/player-status.sh << 'STATUSSCRIPT'
#!/bin/bash

echo "=== Pi Player Status ==="
echo "Service Status:"
systemctl status pi-player-kiosk.service --no-pager -l | head -10

echo -e "\nRunning Processes:"
ps aux | grep -E "(python3.*player|mpv|vlc)" | grep -v grep

echo -e "\nCached Files:"
ls -lah /home/pi/connect/media_cache/

echo -e "\nRecent Logs:"
journalctl -u pi-player-kiosk.service --no-pager -n 5
STATUSSCRIPT
    
    chmod +x bin/player-status.sh
    
    # Create cache cleanup script
    cat > bin/cleanup-cache.sh << 'CLEANUPSCRIPT'
#!/bin/bash

echo "Cleaning up media cache..."
cd /home/pi/connect

# Remove all cached files except .gitkeep
find media_cache/ -type f ! -name ".gitkeep" -delete

echo "Cache cleaned."
ls -la media_cache/
CLEANUPSCRIPT
    
    chmod +x bin/cleanup-cache.sh
    
    print_info "Management scripts created"
}

create_default_assets() {
    print_step "Creating default assets..."
    
    cd "$INSTALL_DIR/default_assets"
    
    # Create a simple test image if imagemagick is available
    if command -v convert &> /dev/null; then
        convert -size 1920x1080 xc:black \
                -font Arial -pointsize 72 -fill white \
                -gravity center -annotate +0+0 "Pi Player\nDigital Signage" \
                test_image.png 2>/dev/null || true
    fi
    
    # Create .gitkeep files
    touch media_cache/.gitkeep
    touch default_assets/.gitkeep
    touch logs/.gitkeep
    
    print_info "Default assets created"
}

setup_environment() {
    print_step "Setting up environment..."
    
    # Add to PATH if not already there
    if ! grep -q "$INSTALL_DIR/bin" ~/.bashrc; then
        echo "export PATH=\$PATH:$INSTALL_DIR/bin" >> ~/.bashrc
    fi
    
    # Set environment variables for current session
    export PATH=$PATH:$INSTALL_DIR/bin
    
    print_info "Environment configured"
}

show_completion_info() {
    print_header
    echo -e "${GREEN}Pi Player Setup Complete!${NC}"
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    echo "  Install Directory: $INSTALL_DIR"
    echo "  Service Name: $SERVICE_NAME"
    echo "  User: $PI_USER"
    echo ""
    echo -e "${BLUE}Management Commands:${NC}"
    echo "  Start service:    sudo systemctl start $SERVICE_NAME"
    echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
    echo "  Check status:     $INSTALL_DIR/bin/player-status.sh"
    echo "  Clean cache:      $INSTALL_DIR/bin/cleanup-cache.sh"
    echo "  View logs:        journalctl -u $SERVICE_NAME -f"
    echo ""
    echo -e "${BLUE}Configuration Files:${NC}"
    echo "  Main config:      $INSTALL_DIR/config.py"
    echo "  Current playlist: $INSTALL_DIR/current_playlist.json"
    echo "  Service config:   /etc/systemd/system/$SERVICE_NAME.service"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Configure your backend URL in config.py (if using backend API)"
    echo "2. Add media files to $INSTALL_DIR/default_assets/ or configure playlist"
    echo "3. Test the service: sudo systemctl start $SERVICE_NAME"
    echo "4. Enable auto-start on boot (already enabled)"
    echo ""
    echo -e "${GREEN}Setup completed successfully!${NC}"
}

# Main execution
main() {
    print_header
    
    # Get backend URL if needed
    read -p "Enter backend URL (optional, press Enter to skip): " BACKEND_URL
    
    check_requirements
    install_system_packages
    setup_directories
    install_python_dependencies
    create_config_files
    create_startup_scripts
    create_systemd_service
    create_management_scripts
    create_default_assets
    setup_environment
    
    show_completion_info
}

# Run main function
main "$@"
