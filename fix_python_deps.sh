#!/bin/bash
set -euo pipefail

# Pi Player Python Dependencies Fix
# Handles PEP 668 externally managed environment

echo "🔧 Fixing Python dependencies for Pi Player..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# Configuration
INSTALL_DIR="/home/pi/pi-player"
CURRENT_DIR="$(pwd)"

# Create install directory if we're not already there
if [[ "$(basename "$CURRENT_DIR")" != "pi-player" ]]; then
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown -R "${USER}:${USER}" "$INSTALL_DIR"
    
    # Copy files if we're in a different location
    if [[ -f "pi_server.py" ]]; then
        log "Copying Pi Player files to $INSTALL_DIR"
        cp *.py "$INSTALL_DIR/" 2>/dev/null || true
        cp -r services "$INSTALL_DIR/" 2>/dev/null || true
        cp *.sh "$INSTALL_DIR/" 2>/dev/null || true
        cp *.md "$INSTALL_DIR/" 2>/dev/null || true
    fi
else
    INSTALL_DIR="$CURRENT_DIR"
fi

cd "$INSTALL_DIR"

log "Working directory: $(pwd)"

# Method 1: Try system packages first
log "Trying system packages..."
if sudo DEBIAN_FRONTEND=noninteractive apt install -y -qq python3-fastapi python3-uvicorn python3-psutil python3-requests python3-full 2>/dev/null; then
    log "System packages installed successfully"
    
    # Test if they work
    if python3 -c "import fastapi, uvicorn, psutil, requests" 2>/dev/null; then
        success "All dependencies working with system packages!"
        exit 0
    else
        log "System packages installed but not working, trying virtual environment..."
    fi
else
    log "System packages not available, using virtual environment..."
fi

# Method 2: Virtual environment
log "Setting up virtual environment..."

# Remove old venv if exists
rm -rf venv

# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install packages
log "Installing packages in virtual environment..."
pip install fastapi uvicorn psutil requests

# Test installation
if python -c "import fastapi, uvicorn, psutil, requests; print('✓ All packages working!')" 2>/dev/null; then
    success "Virtual environment setup complete!"
    
    # Update systemd services
    log "Updating systemd services..."
    
    # Copy updated service files
    if [[ -f "services/pi-player.service" ]]; then
        sudo cp services/pi-player.service /etc/systemd/system/
        sudo cp services/media-player.service /etc/systemd/system/
        sudo systemctl daemon-reload
        success "Systemd services updated"
    fi
    
    deactivate
    
    echo
    success "Python dependencies fixed!"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Test the system: python3 test_system.py"
    echo "2. Or start services: sudo systemctl start pi-player.service media-player.service"
    echo "3. Check status: sudo systemctl status pi-player.service"
    
else
    # Method 3: Break system packages (last resort)
    warning "Virtual environment failed, trying --break-system-packages..."
    deactivate
    rm -rf venv
    
    python3 -m pip install --user --break-system-packages fastapi uvicorn psutil requests
    
    if python3 -c "import fastapi, uvicorn, psutil, requests; print('✓ All packages working!')" 2>/dev/null; then
        success "Dependencies installed with --break-system-packages"
    else
        echo "❌ All methods failed. Please check your Python installation."
        exit 1
    fi
fi

echo
echo "🎉 Pi Player dependencies are now ready!"