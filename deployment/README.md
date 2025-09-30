# Pi Player System Deployment

This directory contains all the system-level configurations and deployment scripts needed to set up a Raspberry Pi as a fullscreen media player kiosk.

## 📋 What Gets Deployed

### System Services
- **`pi-player-kiosk.service`** - Main systemd service that launches the fullscreen kiosk
- Replaces desktop environment with fullscreen media player on boot
- Configured with proper display environment variables and permissions

### Management Scripts (`/home/pi/bin/`)
- **`start-player.sh`** - Kiosk launch script (used by systemd)
- **`player-status.sh`** - Shows current player status and cache info  
- **`cleanup-cache.sh`** - Manual cache cleanup utility
- **`periodic-playlist-fetch.sh`** - Fetches new playlists from backend API

### System Configuration
- **Cron Job** - Automatic playlist fetching every 5 minutes
- **Sudo Permissions** - Allows `pi` user to manage systemd services
- **Display Setup** - X11/Wayland configuration for kiosk mode
- **Package Dependencies** - MPV, VLC, FFmpeg, unclutter, etc.

## 🚀 Quick Deployment

Run the deployment script to configure everything:

```bash
cd /home/pi/connect
./deployment/deploy-pi-player.sh
```

This will:
1. ✅ Install required packages (mpv, vlc, feh, unclutter, ffmpeg)
2. ✅ Configure systemd service for automatic startup
3. ✅ Install management scripts to `/home/pi/bin/`
4. ✅ Setup cron job for periodic playlist fetching
5. ✅ Configure sudo permissions for service management
6. ✅ Prepare display settings for kiosk mode

## 🎮 System Overview

### Boot Process
1. **Pi boots to graphical target** (LXDE desktop environment)
2. **systemd launches pi-player-kiosk.service** 
3. **start-player.sh kills desktop, configures display**
4. **Python media player starts in fullscreen**
5. **Unclutter hides cursor, xset disables screensaver**

### Display Management
- **X11 Server**: Uses existing X server (Xwayland or Xorg)
- **DISPLAY=:0**: Standard display configuration
- **XAUTHORITY**: Proper X11 authentication
- **Fullscreen Override**: Kills pcmanfm desktop manager
- **Hardware Acceleration**: MPV with GPU acceleration when possible

### Video Optimization
- **4K Detection**: Automatically detects high-resolution videos
- **Downscaling**: Uses FFmpeg to convert 4K → 1080p for Pi performance
- **Pi-Friendly Settings**: H.264 Main profile, yuv420p, no audio
- **Cache Management**: Automatically cleans old videos when playlist changes

## 📁 Directory Structure

```
deployment/
├── deploy-pi-player.sh          # Main deployment script
├── README.md                    # This documentation
├── systemd/
│   └── pi-player-kiosk.service  # Systemd service file
├── scripts/                     # Management scripts
│   ├── start-player.sh          # Kiosk launcher
│   ├── player-status.sh         # Status checker
│   ├── cleanup-cache.sh         # Cache cleaner
│   └── periodic-playlist-fetch.sh # Playlist fetcher
└── cron/
    └── pi-player-crontab        # Cron job configuration
```

## 🔧 Manual Configuration

If you prefer manual setup instead of using the deployment script:

### 1. Install Systemd Service
```bash
sudo cp deployment/systemd/pi-player-kiosk.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/pi-player-kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable pi-player-kiosk.service
```

### 2. Install Management Scripts
```bash
mkdir -p /home/pi/bin
cp deployment/scripts/* /home/pi/bin/
chmod +x /home/pi/bin/*
```

### 3. Setup Cron Job
```bash
(crontab -l 2>/dev/null; cat deployment/cron/pi-player-crontab) | crontab -
```

### 4. Configure Sudo Permissions
```bash
sudo cp deployment/sudoers.d/pi-player /etc/sudoers.d/
sudo chmod 644 /etc/sudoers.d/pi-player
```

## 🎯 Kiosk Mode Details

### Display Environment
- **Target**: `graphical.target` (waits for GUI to be ready)
- **Environment**: `DISPLAY=:0`, `XAUTHORITY=/home/pi/.Xauthority`
- **User Context**: Runs as `pi` user with access to `audio`, `video`, `render` groups

### Process Flow
1. **Desktop Suppression**: `pkill -f "pcmanfm.*desktop"` removes file manager
2. **Display Configuration**: `xset s off -dpms` disables screensaver
3. **Cursor Management**: `unclutter -idle 0 -root` hides mouse cursor  
4. **Media Player Launch**: Python player with MPV/VLC backend
5. **Fullscreen Enforcement**: All media plays with `--fullscreen` flag

### Restart Behavior
- **Automatic Restart**: Service restarts on failure with 5-second delay
- **Rate Limiting**: Max 3 restarts per 5 minutes to prevent boot loops
- **Graceful Shutdown**: Properly terminates media processes on stop

## 🔍 Troubleshooting

### Check Service Status
```bash
sudo systemctl status pi-player-kiosk.service
journalctl -u pi-player-kiosk.service -f
```

### Check Display Access  
```bash
DISPLAY=:0 xdpyinfo | head -5
```

### Manual Testing
```bash
# Test kiosk script directly
DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority /home/pi/bin/start-player.sh

# Check player status
/home/pi/bin/player-status.sh
```

### Common Issues
- **"X server not available"**: Check if graphical session is running
- **"Permission denied"**: Ensure sudoers configuration is correct
- **Video stuttering**: Videos automatically optimized to 1080p for Pi performance
- **No fullscreen**: Desktop manager may not be properly terminated

## 📊 System Requirements

### Hardware
- **Raspberry Pi 4** (recommended) or Pi 3B+
- **HDMI display** connected and configured
- **SD card** with at least 8GB free space for media cache
- **Network connection** for playlist fetching

### Software  
- **Raspberry Pi OS** (Bookworm/Bullseye) with desktop environment
- **Python 3.8+** with pip
- **Git** for code deployment
- **FFmpeg** for video optimization
- **Media players**: MPV (preferred), VLC, feh

### Network
- **Outbound HTTPS** access to backend API and Cloudinary
- **SSH access** (optional) for remote management

## 🔄 Updates and Maintenance

### Updating System Code
```bash
cd /home/pi/connect
git pull origin hardcoded
./deployment/deploy-pi-player.sh  # Re-run if needed
sudo systemctl restart pi-player-kiosk.service
```

### Cache Management
```bash
/home/pi/bin/cleanup-cache.sh           # Manual cleanup
/home/pi/bin/cleanup-cache.sh --dry-run # Preview cleanup
```

### Playlist Management
```bash
/home/pi/bin/periodic-playlist-fetch.sh # Manual fetch
```

This deployment system ensures your Pi Player can be easily reproduced on multiple Raspberry Pi devices with consistent configuration.
