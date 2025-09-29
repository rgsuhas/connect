#!/bin/bash
set -euo pipefail

# Pi Player Boot Startup Script
# Ensures all services are running and Pi is ready for playlists

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PI_USER="${USER:-pi}"
INSTALL_DIR="/home/${PI_USER}/connect"
LOG_FILE="$INSTALL_DIR/logs/startup.log"
MAX_WAIT_TIME=60  # Maximum time to wait for services
HEALTH_CHECK_RETRIES=5
HEALTH_CHECK_INTERVAL=3

# Logging functions
log() {
    local message="$1"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${BLUE}[${timestamp}]${NC} $message" | tee -a "$LOG_FILE"
}

success() {
    local message="$1"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${GREEN}[${timestamp}] SUCCESS:${NC} $message" | tee -a "$LOG_FILE"
}

warning() {
    local message="$1"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${YELLOW}[${timestamp}] WARNING:${NC} $message" | tee -a "$LOG_FILE"
}

error() {
    local message="$1"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${RED}[${timestamp}] ERROR:${NC} $message" | tee -a "$LOG_FILE"
}

# Banner
show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        Pi Player Boot Startup                               ║"
    echo "║                                                                              ║"
    echo "║  Starting all services and preparing Pi for playlist management             ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# System preparation
prepare_system() {
    log "Preparing system for Pi Player..."
    
    # Create directories if they don't exist
    mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/media_cache" 2>/dev/null || true
    
    # Set proper permissions
    sudo chown -R "${PI_USER}:${PI_USER}" "$INSTALL_DIR" 2>/dev/null || true
    
    # Check display environment for GUI apps
    if [[ -z "${DISPLAY:-}" ]]; then
        export DISPLAY=:0
        log "Set DISPLAY environment variable to :0"
    fi
    
    # Check for audio setup
    if command -v amixer >/dev/null 2>&1; then
        # Ensure audio is not muted
        amixer set Master unmute 2>/dev/null || true
        amixer set PCM unmute 2>/dev/null || true
    fi
    
    success "System preparation complete"
}

# Service management functions
start_service() {
    local service_name="$1"
    local friendly_name="$2"
    
    log "Starting $friendly_name..."
    
    if systemctl is-active --quiet "$service_name"; then
        success "$friendly_name is already running"
        return 0
    fi
    
    sudo systemctl start "$service_name"
    
    # Wait for service to start
    local wait_count=0
    while [[ $wait_count -lt 10 ]]; do
        if systemctl is-active --quiet "$service_name"; then
            success "$friendly_name started successfully"
            return 0
        fi
        sleep 1
        ((wait_count++))
    done
    
    error "$friendly_name failed to start"
    sudo systemctl status "$service_name" --no-pager --lines=5
    return 1
}

enable_and_start_service() {
    local service_name="$1"
    local friendly_name="$2"
    
    # Enable service for boot startup
    if ! systemctl is-enabled --quiet "$service_name" 2>/dev/null; then
        log "Enabling $friendly_name for boot startup..."
        sudo systemctl enable "$service_name"
    fi
    
    # Start the service
    start_service "$service_name" "$friendly_name"
}

# Check if services are installed
check_services_installed() {
    log "Checking Pi Player services installation..."
    
    local services=("pi-player.service" "media-player.service")
    local all_installed=true
    
    for service in "${services[@]}"; do
        if [[ ! -f "/etc/systemd/system/$service" ]]; then
            error "Service $service not found in /etc/systemd/system/"
            all_installed=false
        fi
    done
    
    if [[ "$all_installed" == "false" ]]; then
        error "Pi Player services not properly installed"
        log "Please run the installation script first: ./install.sh"
        return 1
    fi
    
    success "All Pi Player services are installed"
    return 0
}

# Start all Pi Player services
start_pi_player_services() {
    log "Starting Pi Player services..."
    
    # Reload systemd daemon to pick up any changes
    sudo systemctl daemon-reload
    
    # Start API server first
    enable_and_start_service "pi-player.service" "Pi Player API Server"
    
    # Wait a moment for API to initialize
    sleep 2
    
    # Start media player daemon
    enable_and_start_service "media-player.service" "Media Player Daemon"
    
    success "All Pi Player services started"
}

# Health check functions
check_api_health() {
    local retries=$1
    local interval=$2
    
    log "Checking API health..."
    
    for ((i=1; i<=retries; i++)); do
        if curl -s --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
            success "API health check passed (attempt $i/$retries)"
            return 0
        fi
        
        if [[ $i -lt $retries ]]; then
            log "API health check failed (attempt $i/$retries), retrying in ${interval}s..."
            sleep $interval
        fi
    done
    
    error "API health check failed after $retries attempts"
    return 1
}

test_api_endpoints() {
    log "Testing API endpoints..."
    
    local api_base="http://localhost:8000"
    
    # Test health endpoint
    if curl -s "${api_base}/health" | grep -q '"status"'; then
        success "Health endpoint working"
    else
        warning "Health endpoint may have issues"
    fi
    
    # Test telemetry endpoint
    if curl -s "${api_base}/telemetry" | grep -q '"timestamp"'; then
        success "Telemetry endpoint working"
    else
        warning "Telemetry endpoint may have issues"
    fi
    
    # Test playlist endpoint
    if curl -s "${api_base}/playlist" >/dev/null 2>&1; then
        success "Playlist endpoint working"
    else
        warning "Playlist endpoint may have issues"
    fi
}

# Network connectivity check
check_network() {
    log "Checking network connectivity..."
    
    # Check local network
    if ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
        success "Internet connectivity available"
        return 0
    elif ping -c 1 -W 5 192.168.1.1 >/dev/null 2>&1 || ping -c 1 -W 5 10.0.0.1 >/dev/null 2>&1; then
        success "Local network available"
        return 0
    else
        warning "Network connectivity limited or unavailable"
        return 1
    fi
}

# System status report
show_system_status() {
    log "System Status Report"
    echo "===================="
    
    # System info
    echo "System Information:"
    echo "  Hostname: $(hostname)"
    echo "  IP Address: $(hostname -I | awk '{print $1}' || echo 'Not available')"
    echo "  Uptime: $(uptime -p 2>/dev/null || uptime)"
    echo "  Load: $(uptime | awk -F'load average:' '{print $2}' | xargs)"
    echo
    
    # Service status
    echo "Service Status:"
    printf "  %-20s %s\n" "API Server:" "$(systemctl is-active pi-player.service 2>/dev/null || echo 'unknown')"
    printf "  %-20s %s\n" "Media Player:" "$(systemctl is-active media-player.service 2>/dev/null || echo 'unknown')"
    echo
    
    # Resource usage
    echo "Resource Usage:"
    echo "  Memory: $(free -h | awk 'NR==2{printf "%.1f%% (%s/%s)", $3*100/$2, $3, $2}')"
    echo "  Disk: $(df -h / | awk 'NR==2{printf "%s (%s)", $5, $4" available"}')"
    echo "  Temperature: $(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 || echo 'N/A')"
    echo
    
    # API status
    echo "API Endpoints:"
    local api_ip=$(hostname -I | awk '{print $1}')
    echo "  Health: http://${api_ip}:8000/health"
    echo "  Telemetry: http://${api_ip}:8000/telemetry"
    echo "  Playlist: http://${api_ip}:8000/playlist"
    echo "  API Docs: http://${api_ip}:8000/docs"
}

# Cleanup on exit
cleanup() {
    log "Startup script completed"
}

# Wait for system to be ready
wait_for_system() {
    log "Waiting for system to be fully ready..."
    
    # Wait for network
    local network_wait=0
    while [[ $network_wait -lt 30 ]]; do
        if check_network >/dev/null 2>&1; then
            break
        fi
        sleep 2
        ((network_wait+=2))
    done
    
    # Wait for display (if GUI services are needed)
    if [[ -n "${DISPLAY:-}" ]]; then
        local display_wait=0
        while [[ $display_wait -lt 20 ]]; do
            if xdpyinfo >/dev/null 2>&1; then
                log "Display is available"
                break
            fi
            sleep 1
            ((display_wait++))
        done
    fi
    
    success "System readiness check complete"
}

# Restart services if they're not healthy
restart_unhealthy_services() {
    log "Checking service health..."
    
    # Check API service
    if ! systemctl is-active --quiet pi-player.service; then
        warning "API service not running, restarting..."
        sudo systemctl restart pi-player.service
        sleep 5
    fi
    
    # Check media player service  
    if ! systemctl is-active --quiet media-player.service; then
        warning "Media player service not running, restarting..."
        sudo systemctl restart media-player.service
        sleep 3
    fi
    
    # Verify API is responding
    if ! curl -s --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
        warning "API not responding, restarting API service..."
        sudo systemctl restart pi-player.service
        sleep 5
    fi
}

# Main startup sequence
main() {
    # Setup logging
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Show banner
    show_banner | tee -a "$LOG_FILE"
    
    log "Pi Player startup initiated at $(date)"
    log "Running as user: $USER"
    log "Install directory: $INSTALL_DIR"
    
    # System preparation
    prepare_system
    wait_for_system
    
    # Check installation
    if ! check_services_installed; then
        exit 1
    fi
    
    # Start services
    start_pi_player_services
    
    # Wait for services to stabilize
    log "Waiting for services to stabilize..."
    sleep 5
    
    # Health checks
    if check_api_health $HEALTH_CHECK_RETRIES $HEALTH_CHECK_INTERVAL; then
        test_api_endpoints
    else
        restart_unhealthy_services
        # Try health check one more time
        check_api_health 3 2
    fi
    
    # Network check
    check_network
    
    # Final status report
    echo | tee -a "$LOG_FILE"
    show_system_status | tee -a "$LOG_FILE"
    
    echo | tee -a "$LOG_FILE"
    success "🎉 Pi Player is ready for playlist management!"
    log "Backend can now send playlists to: http://$(hostname -I | awk '{print $1}'):8000/playlist"
    
    cleanup
}

# Error handling
trap 'error "Startup script failed at line $LINENO"' ERR
trap cleanup EXIT

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi