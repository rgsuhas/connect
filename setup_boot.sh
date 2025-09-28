#!/bin/bash
set -euo pipefail

# Pi Player Boot Setup Script
# Configures Pi Player to start automatically on boot using multiple methods

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
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

# Configuration
PI_USER="${SUDO_USER:-${USER:-pi}}"
INSTALL_DIR="/home/${PI_USER}/pi-player"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    Pi Player Boot Setup                                     ║"
    echo "║                                                                              ║"
    echo "║  Configure automatic startup on boot                                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Method 1: Systemd Service (Preferred)
setup_systemd_startup() {
    log "Setting up systemd startup service..."
    
    if [[ -f "$SCRIPT_DIR/services/pi-player-startup.service" ]]; then
        # Install the startup service
        sudo cp "$SCRIPT_DIR/services/pi-player-startup.service" /etc/systemd/system/
        sudo chmod 644 /etc/systemd/system/pi-player-startup.service
        
        # Reload systemd and enable
        sudo systemctl daemon-reload
        sudo systemctl enable pi-player-startup.service
        
        success "Systemd startup service installed and enabled"
        return 0
    else
        error "Startup service file not found"
        return 1
    fi
}

# Method 2: Crontab (Fallback)
setup_cron_startup() {
    log "Setting up cron startup (fallback method)..."
    
    # Check if cron entry already exists
    if crontab -l 2>/dev/null | grep -q "pi-player/run.sh"; then
        log "Cron entry already exists"
        return 0
    fi
    
    # Add cron job for boot startup
    (crontab -l 2>/dev/null; echo "@reboot sleep 60 && $INSTALL_DIR/run.sh >> $INSTALL_DIR/logs/startup.log 2>&1") | crontab -
    
    success "Cron startup job added"
}

# Method 3: rc.local (Last resort)
setup_rclocal_startup() {
    log "Setting up rc.local startup (last resort)..."
    
    local rc_local="/etc/rc.local"
    local startup_line="su - $PI_USER -c '$INSTALL_DIR/run.sh' >> $INSTALL_DIR/logs/startup.log 2>&1 &"
    
    if [[ -f "$rc_local" ]]; then
        # Check if entry already exists
        if grep -q "pi-player/run.sh" "$rc_local"; then
            log "rc.local entry already exists"
            return 0
        fi
        
        # Backup rc.local
        sudo cp "$rc_local" "${rc_local}.backup"
        
        # Add startup line before "exit 0"
        sudo sed -i "/exit 0/i $startup_line" "$rc_local"
        
        success "rc.local startup added"
    else
        # Create rc.local
        sudo tee "$rc_local" > /dev/null << EOF
#!/bin/bash
# Pi Player startup
$startup_line
exit 0
EOF
        sudo chmod +x "$rc_local"
        success "rc.local created with Pi Player startup"
    fi
}

# Method 4: Desktop autostart (for GUI environments)
setup_desktop_autostart() {
    log "Setting up desktop autostart..."
    
    local autostart_dir="/home/$PI_USER/.config/autostart"
    local desktop_file="$autostart_dir/pi-player.desktop"
    
    # Create autostart directory
    sudo mkdir -p "$autostart_dir"
    sudo chown -R "$PI_USER:$PI_USER" "/home/$PI_USER/.config"
    
    # Create desktop entry
    cat > "$desktop_file" << EOF
[Desktop Entry]
Type=Application
Name=Pi Player Startup
Comment=Start Pi Player services on desktop login
Exec=$INSTALL_DIR/run.sh
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
StartupNotify=false
Terminal=false
EOF
    
    chmod +x "$desktop_file"
    success "Desktop autostart configured"
}

# Test the startup script
test_startup_script() {
    log "Testing startup script..."
    
    if [[ ! -f "$INSTALL_DIR/run.sh" ]]; then
        error "run.sh not found at $INSTALL_DIR/run.sh"
        return 1
    fi
    
    if [[ ! -x "$INSTALL_DIR/run.sh" ]]; then
        error "run.sh is not executable"
        chmod +x "$INSTALL_DIR/run.sh"
    fi
    
    # Test basic syntax
    if bash -n "$INSTALL_DIR/run.sh"; then
        success "Startup script syntax is valid"
    else
        error "Startup script has syntax errors"
        return 1
    fi
    
    return 0
}

# Configure sudoers for service management
setup_sudoers() {
    log "Configuring sudo permissions for service management..."
    
    local sudoers_file="/etc/sudoers.d/pi-player"
    
    # Allow pi user to manage Pi Player services without password
    sudo tee "$sudoers_file" > /dev/null << EOF
# Pi Player service management
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl start pi-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop pi-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart pi-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl start media-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop media-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart media-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl start pi-player-startup.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl enable pi-player-startup.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl status pi-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl status media-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active pi-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active media-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled pi-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled media-player.service
$PI_USER ALL=(ALL) NOPASSWD: /bin/chown -R $PI_USER\\:$PI_USER $INSTALL_DIR
EOF
    
    sudo chmod 644 "$sudoers_file"
    
    # Test sudoers syntax
    if sudo visudo -c -f "$sudoers_file"; then
        success "Sudoers configuration added"
    else
        error "Sudoers configuration has syntax errors"
        sudo rm -f "$sudoers_file"
        return 1
    fi
}

# Show final instructions
show_completion() {
    echo
    success "Pi Player boot setup completed!"
    echo
    echo -e "${BLUE}Boot Methods Configured:${NC}"
    echo "  ✓ Systemd service (primary method)"
    echo "  ✓ Cron job (fallback)"
    echo "  ✓ Desktop autostart (if GUI enabled)"
    echo "  ✓ Sudo permissions for service management"
    echo
    echo -e "${BLUE}Testing:${NC}"
    echo "  Manual test: $INSTALL_DIR/run.sh"
    echo "  Service test: sudo systemctl start pi-player-startup.service"
    echo "  Boot test: sudo reboot"
    echo
    echo -e "${BLUE}Logs:${NC}"
    echo "  Startup log: $INSTALL_DIR/logs/startup.log"
    echo "  Service log: sudo journalctl -u pi-player-startup.service -f"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Reboot your Pi to test automatic startup"
    echo "  2. Check that services start automatically"
    echo "  3. Verify API is accessible: curl http://localhost:8000/health"
    echo "  4. Send test playlist from your backend"
    echo
    echo -e "${GREEN}🎉 Pi Player will now start automatically on every boot!${NC}"
}

# Main setup function
main() {
    show_banner
    
    log "Setting up Pi Player automatic startup..."
    log "User: $PI_USER"
    log "Install directory: $INSTALL_DIR"
    
    # Test the startup script first
    if ! test_startup_script; then
        exit 1
    fi
    
    # Setup sudoers permissions
    setup_sudoers
    
    # Setup multiple boot methods for reliability
    setup_systemd_startup
    setup_cron_startup
    setup_desktop_autostart
    
    # Create a manual test command
    cat > "$INSTALL_DIR/test_startup.sh" << 'EOF'
#!/bin/bash
echo "Testing Pi Player startup manually..."
/home/pi/pi-player/run.sh
EOF
    chmod +x "$INSTALL_DIR/test_startup.sh"
    
    show_completion
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "This script should not be run as root"
    error "Run as the pi user: ./setup_boot.sh"
    exit 1
fi

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi