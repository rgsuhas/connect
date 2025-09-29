#!/bin/bash
set -euo pipefail

# Pi Player Service Installation Script
# Installs and configures the Pi Player systemd service

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi-player.service"
SERVICE_TEMPLATE="$SCRIPT_DIR/services/pi-player.service.template"
SYSTEM_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
USER_NAME="$(whoami)"
USER_ID="$(id -u)"

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                     Pi Player Service Installation                           ║"
    echo "║                                                                              ║"
    echo "║  This script will install Pi Player as a systemd service for boot startup   ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check if we have systemd
    if ! command -v systemctl >/dev/null 2>&1; then
        error "systemctl not found. This system doesn't use systemd."
        exit 1
    fi
    
    # Check if template exists
    if [[ ! -f "$SERVICE_TEMPLATE" ]]; then
        error "Service template not found: $SERVICE_TEMPLATE"
        exit 1
    fi
    
    # Check if main.py exists
    if [[ ! -f "$SCRIPT_DIR/main.py" ]]; then
        error "Pi Player main.py not found in $SCRIPT_DIR"
        exit 1
    fi
    
    # Check if we can write to systemd directory
    if [[ ! -w "/etc/systemd/system" ]]; then
        warning "Cannot write to /etc/systemd/system - you may need sudo privileges"
    fi
    
    success "System requirements check passed"
}

create_service_file() {
    log "Creating systemd service file..."
    
    # Create a temporary service file with current paths
    local temp_service="/tmp/pi-player.service"
    
    # Replace template variables with actual values
    sed \
        -e "s|User=rgsuhas|User=$USER_NAME|g" \
        -e "s|Group=rgsuhas|Group=$USER_NAME|g" \
        -e "s|WorkingDirectory=/home/rgsuhas/pi-player|WorkingDirectory=$SCRIPT_DIR|g" \
        -e "s|Environment=HOME=/home/rgsuhas|Environment=HOME=$HOME|g" \
        -e "s|Environment=XDG_RUNTIME_DIR=/run/user/1000|Environment=XDG_RUNTIME_DIR=/run/user/$USER_ID|g" \
        -e "s|ExecStart=/usr/bin/python3 /home/rgsuhas/pi-player/main.py|ExecStart=/usr/bin/python3 $SCRIPT_DIR/main.py|g" \
        -e "s|ReadWritePaths=/home/rgsuhas/pi-player|ReadWritePaths=$SCRIPT_DIR|g" \
        -e "s|StandardOutput=append:/home/rgsuhas/pi-player/logs/service.log|StandardOutput=append:$SCRIPT_DIR/logs/service.log|g" \
        -e "s|StandardError=append:/home/rgsuhas/pi-player/logs/service_error.log|StandardError=append:$SCRIPT_DIR/logs/service_error.log|g" \
        "$SERVICE_TEMPLATE" > "$temp_service"
    
    # Copy to system location
    if sudo cp "$temp_service" "$SYSTEM_SERVICE_PATH"; then
        success "Service file installed to $SYSTEM_SERVICE_PATH"
    else
        error "Failed to install service file"
        return 1
    fi
    
    # Set correct permissions
    sudo chmod 644 "$SYSTEM_SERVICE_PATH"
    
    # Clean up
    rm -f "$temp_service"
}

install_service() {
    log "Installing Pi Player service..."
    
    # Reload systemd daemon
    log "Reloading systemd daemon..."
    sudo systemctl daemon-reload
    
    # Enable service for boot startup
    log "Enabling service for boot startup..."
    sudo systemctl enable "$SERVICE_NAME"
    
    success "Pi Player service installed and enabled"
}

start_service() {
    log "Starting Pi Player service..."
    
    if sudo systemctl start "$SERVICE_NAME"; then
        success "Pi Player service started"
    else
        error "Failed to start Pi Player service"
        return 1
    fi
}

check_service_status() {
    log "Checking service status..."
    
    echo ""
    echo "Service Status:"
    systemctl status "$SERVICE_NAME" --no-pager --lines=10
    
    echo ""
    echo "Service Logs (last 10 lines):"
    sudo journalctl -u "$SERVICE_NAME" --no-pager --lines=10
}

uninstall_service() {
    log "Uninstalling Pi Player service..."
    
    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Stopping service..."
        sudo systemctl stop "$SERVICE_NAME"
    fi
    
    # Disable service
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log "Disabling service..."
        sudo systemctl disable "$SERVICE_NAME"
    fi
    
    # Remove service file
    if [[ -f "$SYSTEM_SERVICE_PATH" ]]; then
        log "Removing service file..."
        sudo rm -f "$SYSTEM_SERVICE_PATH"
    fi
    
    # Reload daemon
    sudo systemctl daemon-reload
    
    success "Pi Player service uninstalled"
}

show_help() {
    echo "Pi Player Service Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install     Install and enable the Pi Player service"
    echo "  uninstall   Remove the Pi Player service"
    echo "  start       Start the service"
    echo "  stop        Stop the service"
    echo "  restart     Restart the service" 
    echo "  status      Show service status and logs"
    echo "  logs        Show recent service logs"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install          # Install service for boot startup"
    echo "  $0 status           # Check if service is running"
    echo "  $0 logs             # View recent logs"
}

main() {
    local command="${1:-help}"
    
    case "$command" in
        install)
            show_banner
            check_requirements
            create_service_file
            install_service
            start_service
            sleep 3
            check_service_status
            echo ""
            success "Pi Player service installation complete!"
            echo ""
            echo "The service will now start automatically on boot."
            echo "Use 'sudo systemctl status pi-player' to check status."
            echo "Use 'sudo journalctl -u pi-player -f' to view live logs."
            ;;
        uninstall)
            uninstall_service
            ;;
        start)
            start_service
            ;;
        stop)
            log "Stopping Pi Player service..."
            sudo systemctl stop "$SERVICE_NAME"
            success "Pi Player service stopped"
            ;;
        restart)
            log "Restarting Pi Player service..."
            sudo systemctl restart "$SERVICE_NAME"
            success "Pi Player service restarted"
            ;;
        status)
            check_service_status
            ;;
        logs)
            echo "Recent Pi Player service logs:"
            sudo journalctl -u "$SERVICE_NAME" --no-pager --lines=20
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"