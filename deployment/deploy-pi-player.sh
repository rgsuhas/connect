#!/bin/bash
set -euo pipefail

# Pi Player System Deployment Script
# Deploys all system configurations for Pi Player kiosk mode

# Colors for output
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

show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                         Pi Player System Deployment                         ║"
    echo "║                                                                              ║"
    echo "║  Configures Raspberry Pi for fullscreen media player kiosk mode            ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check if running on Pi
    if [[ ! -f /proc/device-tree/model ]] || ! grep -qi "raspberry\|pi" /proc/device-tree/model 2>/dev/null; then
        warning "This doesn't appear to be a Raspberry Pi"
    fi
    
    # Check if running as pi user
    if [[ "$USER" != "pi" ]]; then
        error "Please run this script as the 'pi' user"
        exit 1
    fi
    
    # Check for required packages
    local required_packages=("mpv" "vlc" "feh" "unclutter" "ffmpeg" "python3" "git")
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! command -v "$package" >/dev/null 2>&1; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        log "Installing missing packages: ${missing_packages[*]}"
        sudo apt-get update
        sudo apt-get install -y "${missing_packages[@]}"
    fi
    
    success "System requirements checked"
}

install_systemd_service() {
    log "Installing systemd service..."
    
    # Stop any existing services
    sudo systemctl stop pi-player-kiosk.service 2>/dev/null || true
    sudo systemctl stop pi-player.service 2>/dev/null || true
    sudo systemctl stop pi-player-startup.service 2>/dev/null || true
    
    # Disable old services
    sudo systemctl disable pi-player.service 2>/dev/null || true
    sudo systemctl disable pi-player-startup.service 2>/dev/null || true
    
    # Install new service
    sudo cp deployment/systemd/pi-player-kiosk.service /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/pi-player-kiosk.service
    
    # Reload and enable
    sudo systemctl daemon-reload
    sudo systemctl enable pi-player-kiosk.service
    
    success "Systemd service installed"
}

install_scripts() {
    log "Installing management scripts..."
    
    # Create bin directory
    mkdir -p /home/pi/bin
    
    # Copy scripts
    cp deployment/scripts/* /home/pi/bin/
    chmod +x /home/pi/bin/*
    
    success "Management scripts installed"
}

install_cron_job() {
    log "Installing cron job for periodic playlist fetching..."
    
    # Remove existing pi-player cron jobs
    (crontab -l 2>/dev/null | grep -v periodic-playlist-fetch || true) | crontab -
    
    # Add new cron job
    (crontab -l 2>/dev/null; cat deployment/cron/pi-player-crontab) | crontab -
    
    success "Cron job installed"
}

configure_display() {
    log "Configuring display settings for kiosk mode..."
    
    # Ensure X11 utilities are installed
    if ! command -v xset >/dev/null 2>&1; then
        sudo apt-get install -y x11-utils
    fi
    
    # Configure display for optimal kiosk performance
    # Note: These will be applied by the kiosk script at runtime
    
    success "Display configuration prepared"
}

setup_sudoers() {
    log "Setting up sudo permissions for service management..."
    
    local sudoers_file="/etc/sudoers.d/pi-player"
    
    # Create sudoers file for pi-player operations
    sudo tee "$sudoers_file" > /dev/null << 'SUDOERS'
# Pi Player service management permissions
pi ALL=(ALL) NOPASSWD: /bin/systemctl start pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl stop pi-player-kiosk.service  
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl status pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl enable pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl disable pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled pi-player-kiosk.service
pi ALL=(ALL) NOPASSWD: /bin/chown -R pi\\:pi /home/pi/connect
SUDOERS
    
    sudo chmod 644 "$sudoers_file"
    
    # Validate sudoers file
    if sudo visudo -c -f "$sudoers_file"; then
        success "Sudo permissions configured"
    else
        error "Sudoers configuration failed"
        sudo rm -f "$sudoers_file"
        return 1
    fi
}

show_completion() {
    echo
    success "Pi Player deployment completed successfully!"
    echo
    echo -e "${BLUE}System Configuration Summary:${NC}"
    echo "  ✓ Systemd service: pi-player-kiosk.service"
    echo "  ✓ Management scripts in: /home/pi/bin/"
    echo "  ✓ Cron job: Every 5 minutes playlist fetch"
    echo "  ✓ Display: Configured for fullscreen kiosk mode"
    echo "  ✓ Sudo permissions: Service management enabled"
    echo
    echo -e "${BLUE}Available Commands:${NC}"
    echo "  player-status.sh       - Show current player status"
    echo "  cleanup-cache.sh       - Manually clean media cache"
    echo "  start-player.sh        - Manual player start (used by systemd)"
    echo "  periodic-playlist-fetch.sh - Manual playlist fetch"
    echo
    echo -e "${BLUE}Service Management:${NC}"
    echo "  sudo systemctl start pi-player-kiosk    - Start player"
    echo "  sudo systemctl stop pi-player-kiosk     - Stop player"  
    echo "  sudo systemctl status pi-player-kiosk   - Check status"
    echo "  sudo systemctl restart pi-player-kiosk  - Restart player"
    echo
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Reboot your Pi to test automatic startup"
    echo "  2. Check player status: player-status.sh"
    echo "  3. Monitor logs: journalctl -u pi-player-kiosk -f"
    echo "  4. Configure your backend playlist API endpoint"
    echo
    echo -e "${GREEN}🎉 Your Pi is now ready for kiosk mode!${NC}"
}

main() {
    show_banner
    
    log "Starting Pi Player deployment..."
    log "Current user: $USER"
    log "Working directory: $(pwd)"
    
    check_requirements
    install_systemd_service
    install_scripts
    install_cron_job  
    configure_display
    setup_sudoers
    
    show_completion
}

# Check if being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
