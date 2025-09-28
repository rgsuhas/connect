#!/bin/bash
set -euo pipefail

# Pi Player Installation Script
# Installs all dependencies and sets up services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_USER="pi"
PI_HOME="/home/${PI_USER}"
INSTALL_DIR="${PI_HOME}/pi-player"
PYTHON_REQUIREMENTS="fastapi[standard] uvicorn[standard] psutil requests"

# Logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as the pi user."
        exit 1
    fi
}

# Check if running on Raspberry Pi OS
check_os() {
    if [[ ! -f /etc/os-release ]]; then
        warning "Cannot determine OS version"
        return
    fi
    
    . /etc/os-release
    log "Detected OS: $PRETTY_NAME"
    
    if [[ "${ID:-}" != "raspbian" ]] && [[ "${ID_LIKE:-}" != *"debian"* ]]; then
        warning "This script is designed for Raspberry Pi OS/Debian. Continuing anyway..."
    fi
}

# Update system packages
update_system() {
    log "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
    success "System packages updated"
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    local packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "vlc"
        "vlc-bin"
        "ffmpeg"
        "feh"
        "curl"
        "wget"
        "git"
    )
    
    for package in "${packages[@]}"; do
        if dpkg -l | grep -qw "$package"; then
            log "$package is already installed"
        else
            log "Installing $package..."
            sudo apt install -y "$package"
        fi
    done
    
    success "System dependencies installed"
}

# Create virtual environment and install Python dependencies
install_python_deps() {
    log "Setting up Python environment..."
    
    # Try system packages first (preferred method)
    log "Installing Python packages via apt..."
    sudo apt install -y python3-fastapi python3-uvicorn python3-psutil python3-requests 2>/dev/null || {
        log "Some packages not available via apt, using pip with virtual environment..."
        
        # Create virtual environment
        python3 -m venv "$INSTALL_DIR/venv"
        source "$INSTALL_DIR/venv/bin/activate"
        
        # Upgrade pip in virtual environment
        pip install --upgrade pip
        
        # Install Python packages in virtual environment
        pip install $PYTHON_REQUIREMENTS
        
        # Create activation script
        cat > "$INSTALL_DIR/activate_venv.sh" << 'EOF'
#!/bin/bash
source /home/pi/pi-player/venv/bin/activate
exec "$@"
EOF
        chmod +x "$INSTALL_DIR/activate_venv.sh"
        
        deactivate
        
        log "Virtual environment created at $INSTALL_DIR/venv"
    }
    
    # Try to verify installation (works with both system and venv packages)
    if command -v "$INSTALL_DIR/venv/bin/python" >/dev/null 2>&1; then
        "$INSTALL_DIR/venv/bin/python" -c "import fastapi, uvicorn, psutil, requests; print('Python dependencies verified (venv)')"
    else
        python3 -c "import fastapi, uvicorn, psutil, requests; print('Python dependencies verified (system)')" 2>/dev/null || {
            warning "Could not verify all Python packages. Trying pip with --break-system-packages..."
            python3 -m pip install --user --break-system-packages $PYTHON_REQUIREMENTS
            python3 -c "import fastapi, uvicorn, psutil, requests; print('Python dependencies verified (user install)')"
        }
    fi
    
    success "Python dependencies installed"
}

# Setup project directories
setup_directories() {
    log "Setting up project directories..."
    
    # Create main directory structure
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown -R "${PI_USER}:${PI_USER}" "$INSTALL_DIR"
    
    # Create subdirectories
    mkdir -p "${INSTALL_DIR}/media_cache"
    mkdir -p "${INSTALL_DIR}/logs"
    mkdir -p "${INSTALL_DIR}/services"
    
    success "Project directories created"
}

# Copy files to installation directory
install_files() {
    log "Installing Pi Player files..."
    
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy Python files
    cp "${script_dir}/config.py" "$INSTALL_DIR/"
    cp "${script_dir}/pi_server.py" "$INSTALL_DIR/"
    cp "${script_dir}/media_player.py" "$INSTALL_DIR/"
    cp "${script_dir}/media_downloader.py" "$INSTALL_DIR/"
    cp "${script_dir}/telemetry.py" "$INSTALL_DIR/"
    
    # Make Python files executable
    chmod +x "${INSTALL_DIR}/"*.py
    
    success "Pi Player files installed"
}

# Install systemd services
install_services() {
    log "Installing systemd services..."
    
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy service files
    sudo cp "${script_dir}/services/pi-player.service" /etc/systemd/system/
    sudo cp "${script_dir}/services/media-player.service" /etc/systemd/system/
    
    # Set correct permissions
    sudo chmod 644 /etc/systemd/system/pi-player.service
    sudo chmod 644 /etc/systemd/system/media-player.service
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    success "Systemd services installed"
}

# Enable and start services
enable_services() {
    log "Enabling and starting services..."
    
    # Enable services to start on boot
    sudo systemctl enable pi-player.service
    sudo systemctl enable media-player.service
    
    # Start services
    log "Starting pi-player service..."
    sudo systemctl start pi-player.service
    
    log "Starting media-player service..."
    sudo systemctl start media-player.service
    
    # Check service status
    sleep 3
    
    if systemctl is-active --quiet pi-player.service; then
        success "Pi Player API service is running"
    else
        error "Pi Player API service failed to start"
        sudo systemctl status pi-player.service --no-pager
    fi
    
    if systemctl is-active --quiet media-player.service; then
        success "Media Player daemon is running"
    else
        warning "Media Player daemon may not be running (this is normal if no display is connected)"
        sudo systemctl status media-player.service --no-pager --lines=5
    fi
}

# Create sample playlist for testing
create_sample_playlist() {
    log "Creating sample playlist..."
    
    cat > "${INSTALL_DIR}/sample_playlist.json" << 'EOF'
{
    "version": "1.0",
    "last_updated": "2024-01-01T12:00:00Z",
    "loop": true,
    "items": [
        {
            "filename": "test_image.jpg",
            "url": "https://picsum.photos/1920/1080",
            "duration": 5,
            "checksum": null
        }
    ]
}
EOF
    
    success "Sample playlist created at ${INSTALL_DIR}/sample_playlist.json"
}

# Setup firewall (optional)
setup_firewall() {
    if command -v ufw >/dev/null 2>&1; then
        log "Configuring firewall..."
        sudo ufw allow 8000/tcp comment "Pi Player API"
        success "Firewall configured"
    else
        warning "UFW not installed, skipping firewall configuration"
    fi
}

# Create utility scripts
create_utilities() {
    log "Creating utility scripts..."
    
    # Status script
    cat > "${INSTALL_DIR}/status.sh" << 'EOF'
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
tail -5 /home/pi/pi-player/logs/pi_server.log 2>/dev/null | sed 's/^/    /' || echo "    No logs found"
echo "  Media Player:"
tail -5 /home/pi/pi-player/logs/media_player.log 2>/dev/null | sed 's/^/    /' || echo "    No logs found"
EOF
    
    # Restart script
    cat > "${INSTALL_DIR}/restart.sh" << 'EOF'
#!/bin/bash
echo "Restarting Pi Player services..."
sudo systemctl restart pi-player.service
sudo systemctl restart media-player.service
echo "Services restarted"
EOF
    
    # Update script
    cat > "${INSTALL_DIR}/update.sh" << 'EOF'
#!/bin/bash
echo "Updating Pi Player..."
cd /home/pi/pi-player
git pull origin main || echo "No git repository found"
sudo systemctl restart pi-player.service
sudo systemctl restart media-player.service
echo "Update complete"
EOF
    
    # Make scripts executable
    chmod +x "${INSTALL_DIR}/"*.sh
    
    success "Utility scripts created"
}

# Display final information
show_completion() {
    echo
    success "Pi Player installation completed!"
    echo
    echo -e "${BLUE}System Information:${NC}"
    echo "  Installation directory: $INSTALL_DIR"
    echo "  API endpoint: http://$(hostname -I | awk '{print $1}'):8000"
    echo "  Service logs: journalctl -u pi-player.service -f"
    echo "  Media player logs: journalctl -u media-player.service -f"
    echo
    echo -e "${BLUE}Quick Commands:${NC}"
    echo "  Check status: $INSTALL_DIR/status.sh"
    echo "  Restart services: $INSTALL_DIR/restart.sh"
    echo "  View API docs: http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo
    echo -e "${BLUE}Test the installation:${NC}"
    echo "  curl http://localhost:8000/health"
    echo "  curl http://localhost:8000/telemetry"
    echo
    echo -e "${YELLOW}Note:${NC} If you're using SSH, you may need to configure DISPLAY and audio"
    echo "      for the media player daemon to work properly."
    echo
}

# Main installation function
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                            Pi Player Installer                              ║"
    echo "║                                                                              ║"
    echo "║  This script will install Pi Player with all dependencies and services      ║"
    echo "║  Press Ctrl+C to cancel or Enter to continue...                             ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    log "Starting Pi Player installation..."
    
    check_root
    check_os
    update_system
    install_system_deps
    install_python_deps
    setup_directories
    install_files
    install_services
    enable_services
    create_sample_playlist
    setup_firewall
    create_utilities
    show_completion
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi