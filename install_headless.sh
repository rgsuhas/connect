#!/bin/bash
set -euo pipefail

# Pi Player Headless Installation Script
# Completely non-interactive installation for remote deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_USER="${SUDO_USER:-pi}"
PI_HOME="/home/${PI_USER}"
INSTALL_DIR="${PI_HOME}/pi-player"
PYTHON_REQUIREMENTS="fastapi uvicorn psutil requests"

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

# Banner
show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                     Pi Player Headless Installer                            ║"
    echo "║                                                                              ║"
    echo "║  Completely automated installation for Raspberry Pi                         ║"
    echo "║  No prompts, no interaction required                                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Pre-configure apt to be non-interactive
setup_noninteractive() {
    log "Configuring non-interactive environment..."
    
    export DEBIAN_FRONTEND=noninteractive
    export APT_LISTCHANGES_FRONTEND=none
    
    # Set debconf to non-interactive
    echo 'debconf debconf/frontend select Noninteractive' | sudo debconf-set-selections
    
    # Disable service restarts during package installation
    sudo tee /etc/needrestart/conf.d/50local.conf > /dev/null << 'EOF'
$nrconf{kernelhints} = 0;
$nrconf{restart} = 'l';
EOF
}

# Update system packages
update_system() {
    log "Updating system packages..."
    
    sudo apt-get update -qq
    sudo apt-get upgrade -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
    sudo apt-get autoremove -y -qq
    
    success "System packages updated"
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    local packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "python3-full"
        "vlc"
        "vlc-bin"
        "ffmpeg"
        "feh"
        "curl"
        "wget"
        "git"
        "htop"
        "unzip"
    )
    
    # Install all packages at once for efficiency
    sudo apt-get install -y -qq "${packages[@]}"
    
    success "System dependencies installed"
}

# Install Python dependencies
install_python_deps() {
    log "Setting up Python environment..."
    
    # Try system packages first
    log "Attempting system Python packages..."
    if sudo apt-get install -y -qq python3-fastapi python3-uvicorn python3-psutil python3-requests 2>/dev/null; then
        if python3 -c "import fastapi, uvicorn, psutil, requests" 2>/dev/null; then
            success "System Python packages installed successfully"
            return 0
        fi
    fi
    
    log "System packages unavailable, creating virtual environment..."
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip and install packages
    pip install --upgrade pip --quiet
    pip install $PYTHON_REQUIREMENTS --quiet
    
    deactivate
    
    # Test installation
    if "$INSTALL_DIR/venv/bin/python" -c "import fastapi, uvicorn, psutil, requests" 2>/dev/null; then
        success "Virtual environment created and tested"
    else
        error "Failed to verify Python installation"
        exit 1
    fi
}

# Setup directories and files
setup_project() {
    log "Setting up Pi Player project..."
    
    # Create directories
    sudo mkdir -p "$INSTALL_DIR"/{media_cache,logs,services}
    sudo chown -R "${PI_USER}:${PI_USER}" "$INSTALL_DIR"
    
    # Copy files if we're not already in the target directory
    local current_dir="$(pwd)"
    if [[ "$(realpath "$current_dir")" != "$(realpath "$INSTALL_DIR")" ]]; then
        if [[ -f "pi_server.py" ]]; then
            log "Copying Pi Player files..."
            cp *.py "$INSTALL_DIR/" 2>/dev/null || true
            cp -r services "$INSTALL_DIR/" 2>/dev/null || true
            cp *.sh "$INSTALL_DIR/" 2>/dev/null || true
            cp *.md "$INSTALL_DIR/" 2>/dev/null || true
            chmod +x "$INSTALL_DIR"/*.py "$INSTALL_DIR"/*.sh 2>/dev/null || true
        fi
    fi
    
    # Create placeholder files
    touch "$INSTALL_DIR/media_cache/.gitkeep"
    touch "$INSTALL_DIR/logs/.gitkeep"
    
    success "Project setup complete"
}

# Install systemd services
install_services() {
    log "Installing systemd services..."
    
    # Check if service files exist
    if [[ ! -f "$INSTALL_DIR/services/pi-player.service" ]]; then
        error "Service files not found. Please ensure all files are copied correctly."
        return 1
    fi
    
    # Install service files
    sudo cp "$INSTALL_DIR/services/"*.service /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/pi-player.service
    sudo chmod 644 /etc/systemd/system/media-player.service
    
    # Reload systemd and enable services
    sudo systemctl daemon-reload
    sudo systemctl enable pi-player.service media-player.service
    
    success "Systemd services installed and enabled"
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    if command -v ufw >/dev/null 2>&1; then
        # Configure UFW silently
        sudo ufw --force reset >/dev/null 2>&1
        sudo ufw default deny incoming >/dev/null 2>&1
        sudo ufw default allow outgoing >/dev/null 2>&1
        sudo ufw allow ssh >/dev/null 2>&1
        sudo ufw allow 8000/tcp comment "Pi Player API" >/dev/null 2>&1
        sudo ufw --force enable >/dev/null 2>&1
        
        success "Firewall configured (SSH + Pi Player API)"
    else
        warning "UFW not available, skipping firewall setup"
    fi
}

# Start services
start_services() {
    log "Starting Pi Player services..."
    
    # Start services
    sudo systemctl start pi-player.service
    sudo systemctl start media-player.service
    
    # Wait for services to start
    sleep 3
    
    # Check status
    if systemctl is-active --quiet pi-player.service; then
        success "Pi Player API service started"
    else
        warning "Pi Player API service may have issues"
        sudo systemctl status pi-player.service --no-pager --lines=3
    fi
    
    if systemctl is-active --quiet media-player.service; then
        success "Media Player service started"
    else
        warning "Media Player service may have issues (normal if no display)"
        sudo systemctl status media-player.service --no-pager --lines=3
    fi
}

# Create utility scripts
create_utilities() {
    log "Creating utility scripts..."
    
    # Status script
    cat > "$INSTALL_DIR/status.sh" << 'EOF'
#!/bin/bash
echo "Pi Player System Status"
echo "======================"
echo "Services:"
systemctl is-active pi-player.service | sed 's/^/  API Server: /'
systemctl is-active media-player.service | sed 's/^/  Media Player: /'
echo
echo "API Health:"
curl -s http://localhost:8000/health 2>/dev/null | python3 -c "import json,sys; print('  Status:', json.load(sys.stdin)['status'])" || echo "  API not responding"
echo
echo "System:"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "  Memory: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "  Disk: $(df -h / | awk 'NR==2{print $5}')"
echo "  Temp: $(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 || echo 'N/A')"
EOF

    # Restart script
    cat > "$INSTALL_DIR/restart.sh" << 'EOF'
#!/bin/bash
echo "Restarting Pi Player services..."
sudo systemctl restart pi-player.service media-player.service
sleep 2
echo "Status:"
systemctl is-active pi-player.service | sed 's/^/  API Server: /'
systemctl is-active media-player.service | sed 's/^/  Media Player: /'
EOF

    # Log viewer script
    cat > "$INSTALL_DIR/logs.sh" << 'EOF'
#!/bin/bash
case "${1:-api}" in
    api)
        echo "=== Pi Player API Logs ==="
        sudo journalctl -u pi-player.service -f
        ;;
    player)
        echo "=== Media Player Logs ==="
        sudo journalctl -u media-player.service -f
        ;;
    both)
        echo "=== All Pi Player Logs ==="
        sudo journalctl -u pi-player.service -u media-player.service -f
        ;;
    *)
        echo "Usage: $0 [api|player|both]"
        echo "  api    - Show API server logs (default)"
        echo "  player - Show media player logs"
        echo "  both   - Show both service logs"
        ;;
esac
EOF

    chmod +x "$INSTALL_DIR"/*.sh
    success "Utility scripts created"
}

# Final status and information
show_completion() {
    local pi_ip=$(hostname -I | awk '{print $1}')
    
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    Pi Player Installation Complete!                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}System Information:${NC}"
    echo "  Pi IP Address: $pi_ip"
    echo "  API Endpoint: http://$pi_ip:8000"
    echo "  Installation: $INSTALL_DIR"
    echo
    echo -e "${BLUE}Quick Commands:${NC}"
    echo "  System Status:  $INSTALL_DIR/status.sh"
    echo "  Restart:        $INSTALL_DIR/restart.sh"
    echo "  View Logs:      $INSTALL_DIR/logs.sh [api|player|both]"
    echo "  API Health:     curl http://$pi_ip:8000/health"
    echo "  Telemetry:      curl http://$pi_ip:8000/telemetry"
    echo
    echo -e "${BLUE}Service Management:${NC}"
    echo "  Status:   sudo systemctl status pi-player.service"
    echo "  Restart:  sudo systemctl restart pi-player.service media-player.service"
    echo "  Logs:     sudo journalctl -u pi-player.service -f"
    echo
    echo -e "${GREEN}Pi Player is ready for remote playlist management!${NC}"
    echo "Visit http://$pi_ip:8000/docs for the API documentation."
}

# Main installation function
main() {
    show_banner
    
    log "Starting headless Pi Player installation..."
    
    setup_noninteractive
    update_system
    install_system_deps
    setup_project
    install_python_deps
    install_services
    setup_firewall
    start_services
    create_utilities
    
    show_completion
}

# Error handling
trap 'error "Installation failed at line $LINENO. Check the logs above."; exit 1' ERR

# Run installation
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi