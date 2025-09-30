# Pi Player System Configuration Summary

This document summarizes all the system-level configurations applied to transform a Raspberry Pi into a fullscreen media player kiosk.

## 🎯 System Overview

The Pi Player system replaces the default LXDE desktop environment with a fullscreen media player that:
- Boots directly to fullscreen media playback
- Fetches playlists from backend APIs (Cloudinary integration)  
- Automatically optimizes 4K videos to 1080p for smooth Pi performance
- Manages media cache automatically (removes old files when playlists change)
- Provides remote management via SSH and systemd services

## 🔧 Applied Configurations

### 1. Display Management (X11/Wayland)
- **Environment**: Uses existing LXDE X server (Xwayland on Wayland, Xorg on X11)
- **Display**: `DISPLAY=:0` with proper `XAUTHORITY=/home/pi/.Xauthority`
- **Desktop Suppression**: Kills `pcmanfm --desktop` to free the screen  
- **Cursor Management**: Uses `unclutter` to hide mouse cursor
- **Screen Blanking**: Disabled via `xset s off -dpms`
- **Hardware Acceleration**: MPV with GPU acceleration where available

### 2. Systemd Service (`pi-player-kiosk.service`)
```ini
[Unit]
Description=Pi Player Fullscreen Kiosk
After=graphical.target
Wants=graphical.target

[Service]
Type=simple
User=pi
Group=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
Environment=HOME=/home/pi
ExecStart=/home/pi/bin/start-player.sh
Restart=on-failure
RestartSec=5
SupplementaryGroups=audio video render

[Install]
WantedBy=graphical.target
```

### 3. Kiosk Launch Script (`/home/pi/bin/start-player.sh`)
- Waits for X server to be available
- Kills desktop file manager (`pcmanfm`)
- Configures display settings (no screensaver, hidden cursor)
- Launches Python media player in fullscreen mode
- Handles fallbacks and error cases

### 4. Management Scripts (`/home/pi/bin/`)
- **`player-status.sh`**: Shows current playback status, cache info, system stats
- **`cleanup-cache.sh`**: Manual cache cleanup with dry-run option
- **`periodic-playlist-fetch.sh`**: Backend API playlist fetching
- All scripts have proper logging and error handling

### 5. Automated Tasks
- **Cron Job**: `*/5 * * * * /home/pi/bin/periodic-playlist-fetch.sh`
- **Playlist Sync**: Checks backend API every 5 minutes for new playlists
- **Cache Cleanup**: Automatically removes old media when playlist changes
- **Service Monitoring**: systemd handles automatic restarts on failure

### 6. System Permissions
- **Sudoers**: `/etc/sudoers.d/pi-player` allows `pi` user to manage systemd services
- **Groups**: `pi` user added to `audio`, `video`, `render` groups for hardware access
- **File Permissions**: Proper ownership of `/home/pi/connect` and cache directories

### 7. Video Optimization Pipeline
- **Detection**: Automatically detects videos >1080p resolution
- **Transcoding**: Uses FFmpeg to downscale 4K → 1080p
- **Pi-Friendly Settings**: H.264 Main profile, yuv420p, no audio, faststart
- **Performance**: Reduces 4K (58MB) to 1080p (5.5MB) with smooth playback

### 8. Media Player Configuration
- **Primary**: MPV (optimized for Pi hardware)
- **Fallback**: VLC with hardware acceleration (MMAL)
- **Image Viewer**: feh for static images and default screens
- **Settings**: All players configured with `--fullscreen` and performance optimizations

## 📊 Boot Process Flow

1. **System Boot** → LXDE desktop environment starts
2. **Graphical Target** → systemd reaches `graphical.target`
3. **Service Launch** → `pi-player-kiosk.service` starts automatically
4. **Display Takeover** → `start-player.sh` kills desktop, configures display
5. **Media Player Start** → Python player launches with MPV/VLC backend
6. **Fullscreen Mode** → Media plays fullscreen, cursor hidden, no desktop
7. **Background Tasks** → Cron job fetches new playlists every 5 minutes
8. **Auto Management** → Cache cleaned when playlists change, services restart on failure

## 🎮 Runtime Environment

### Process Tree (Typical)
```
systemd
└── pi-player-kiosk.service
    ├── start-player.sh
    │   ├── python3 player.py
    │   ├── mpv --fullscreen video.mp4
    │   └── unclutter -idle 0 -root
    └── dbus-launch (session management)
```

### Display Stack
```
Hardware (HDMI) 
↓
Kernel DRM/KMS drivers
↓  
X11 Server (Xwayland/Xorg)
↓
Window Manager suppressed  
↓
MPV/VLC fullscreen output
```

### Network Integration
```
Pi Player ←→ Backend API (playlists)
    ↓
Cloudinary CDN (media files)
    ↓
Local Cache (/home/pi/connect/media_cache/)
    ↓
MPV/VLC Player (optimized files)
```

## 🔄 Deployment and Reproduction

The entire system can be reproduced on new Pi devices using:

```bash
git clone https://github.com/rgsuhas/connect.git /home/pi/connect
cd /home/pi/connect
./deployment/deploy-pi-player.sh
```

This ensures consistent configuration across multiple Pi Player installations.

## 📈 Performance Optimizations Applied

### Video Processing
- **4K → 1080p**: Automatic downscaling for Pi hardware limitations
- **H.264 Profile**: Main profile (more Pi-friendly than High profile)
- **Audio Removal**: Saves CPU by removing audio tracks
- **Fast Start**: MP4 moov atom moved to beginning for streaming

### System Resources  
- **Memory**: Reduced by disabling desktop components
- **CPU**: Optimized video codecs and player settings
- **Storage**: Automatic cache cleanup prevents disk bloat
- **Network**: Efficient playlist fetching and caching

### Display Performance
- **Hardware Acceleration**: MPV GPU rendering where supported
- **Compositor Bypass**: Direct fullscreen rendering  
- **Buffer Management**: Optimized caching and memory usage

This configuration transforms a standard Raspberry Pi OS installation into a production-ready digital signage / media player kiosk system.
