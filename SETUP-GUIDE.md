# Pi Player Setup Guide - Kiosk Media Player

This guide covers setting up the Pi Player kiosk media player system on a fresh Raspberry Pi installation.

## 🎯 Overview

The Pi Player is a complete kiosk media player solution that:
- Fetches playlists from a backend API or uses hardcoded fallback playlists
- Downloads and caches media files locally
- Displays videos/images in fullscreen kiosk mode
- Provides a REST API for remote management
- Shows a branded default screen when no content is playing

## 📋 Prerequisites

### Hardware
- Raspberry Pi (tested on Pi 4/5)
- MicroSD card (16GB+ recommended, avoid 8GB due to space constraints)
- Display connected via HDMI
- Network connectivity (WiFi or Ethernet)

### Software
- Fresh Raspberry Pi OS installation (Debian 12 Bookworm)
- SSH access enabled

## 🚀 Quick Setup

### 1. Initial System Preparation

```bash
# SSH into your Pi
ssh pi@pi.local

# Update package lists (but don't upgrade all packages to save space)
sudo apt update

# Clean up to free space if needed
sudo apt clean && sudo apt autoremove -y
sudo journalctl --vacuum-size=50M

# Check available disk space (should have 1GB+ free)
df -h
```

### 2. Clone and Setup the Repository

```bash
# Clone the repository to /home/pi/connect
cd /home/pi
git clone <your-repo-url> connect
cd connect

# Switch to the hardcoded branch (contains sample videos)
git checkout hardcoded
```

### 3. Install Dependencies

Install only the essential packages to minimize disk usage:

```bash
# Install Python packages via apt (avoids pip externally-managed-environment issue)
sudo apt install -y python3-fastapi python3-uvicorn python3-psutil python3-requests python3-yaml

# Install media players
sudo apt install -y feh  # for images
# vlc and ffmpeg should already be installed
```

### 4. Configure Backend Connection

Edit the backend configuration in `config.py`:

```bash
# Update backend URL (if different from default)
sed -i 's|BACKEND_BASE_URL: str = ".*"|BACKEND_BASE_URL: str = "https://conekt-ai-backend.onrender.com"|' config.py
```

The system uses these settings:
- Backend URL: `https://conekt-ai-backend.onrender.com` 
- Hardware ID: `68da17212d8ff0001d095d88`
- API Key: `12345678` (configure as needed)

### 5. Install System Services

```bash
# Copy service files to systemd
sudo cp services/*.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable pi-player.service media-player.service

# Start services
sudo systemctl start pi-player.service media-player.service
```

### 6. Load Sample Content

The system will show a default branded screen initially. To load sample videos:

```bash
# Wait for services to start (about 10 seconds)
sleep 10

# Load sample video playlist (Big Buck Bunny, Elephants Dream, etc.)
curl -X POST "http://localhost:8000/playlist/load-default?use_cloudinary=false"
```

### 7. Verify Setup

```bash
# Check service status
sudo systemctl status pi-player.service media-player.service

# Check API health
curl -s http://localhost:8000/health

# Check current playlist
curl -s http://localhost:8000/playlist | python3 -m json.tool

# View logs
journalctl -u pi-player.service -f
journalctl -u media-player.service -f
```

## 🔧 Configuration

### Backend Integration

The system automatically connects to the backend API:
- **Heartbeat**: Sends device status every 30 seconds
- **Telemetry**: Reports system metrics 
- **Playlist Sync**: Fetches playlists from backend (when available)

### Directory Structure

```
/home/pi/connect/
├── *.py                    # Python application files
├── services/               # Systemd service files  
├── media_cache/           # Downloaded media files (auto-created)
├── logs/                  # Application logs (auto-created)
├── default_assets/        # Default screen assets
├── current_playlist.json  # Active playlist (auto-generated)
├── playback_state.json   # Current playback state (auto-generated)
└── config.py             # Configuration settings
```

### Default Behavior

1. **On Boot**: Services start automatically
2. **No Playlist**: Shows branded default screen
3. **Backend Available**: Fetches playlist from backend API
4. **Backend Unavailable**: Uses hardcoded sample videos as fallback
5. **Media Playback**: Downloads files to `media_cache/`, plays in fullscreen loop

## 📡 API Endpoints

The system runs a REST API on port 8000:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/playlist` | GET | Current playlist |
| `/playlist` | POST | Update playlist |
| `/playlist/load-default` | POST | Load default playlist |
| `/telemetry` | GET | System telemetry |

### Load Default Playlist Options

```bash
# Load Cloudinary collections (requires JavaScript processing)
curl -X POST "http://localhost:8000/playlist/load-default?use_cloudinary=true"

# Load sample videos (immediate playback)  
curl -X POST "http://localhost:8000/playlist/load-default?use_cloudinary=false"
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Services Not Starting
```bash
# Check service status
sudo systemctl status pi-player.service media-player.service

# View detailed logs
journalctl -u pi-player.service --no-pager
journalctl -u media-player.service --no-pager

# Restart services
sudo systemctl restart pi-player.service media-player.service
```

#### 2. No Video Playback
- Check if playlist is loaded: `curl -s http://localhost:8000/playlist`
- Check media cache: `ls -la media_cache/`
- Load sample videos: `curl -X POST "http://localhost:8000/playlist/load-default?use_cloudinary=false"`

#### 3. Backend Connection Issues
- Check network connectivity: `curl -I https://conekt-ai-backend.onrender.com`
- Verify API key and hardware ID in `config.py`
- Check backend logs: `journalctl -u pi-player.service | grep backend`

#### 4. Storage Space Issues
```bash
# Check disk usage
df -h

# Clean up if needed
sudo apt clean
sudo apt autoremove -y
sudo journalctl --vacuum-size=50M

# Check media cache size
du -sh media_cache/
```

#### 5. Display Issues
- Ensure `DISPLAY=:0` environment is set
- Check if GUI session is running
- Verify HDMI connection

### Log Locations

- **API Server**: `journalctl -u pi-player.service`
- **Media Player**: `journalctl -u media-player.service`  
- **Application Logs**: `logs/` directory (if enabled)

## 🔒 Security Notes

- Services run as user `pi` (non-root)
- API binds to all interfaces (0.0.0.0:8000) - configure firewall if needed
- Default API key is basic - update for production use
- Consider HTTPS termination for external access

## 🚀 Boot Configuration

Services are configured to start automatically on boot:

```bash
# Check if enabled
sudo systemctl is-enabled pi-player.service media-player.service

# Enable if needed
sudo systemctl enable pi-player.service media-player.service
```

The media player service starts after the GUI session is available to ensure proper display access.

## 📝 Sample Videos Included

The hardcoded branch includes these publicly available sample videos:

1. **Big Buck Bunny** (60s) - https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4
2. **Elephants Dream** (60s) - https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4  
3. **For Bigger Blazes** (15s) - https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4
4. **For Bigger Escapes** (15s) - https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4
5. **For Bigger Fun** (60s) - https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4

These videos are used when the backend is unavailable or when explicitly loading sample content.

## ⚡ Quick Start Summary

For an existing Pi with the repository already cloned:

```bash
cd /home/pi/connect
git checkout hardcoded
sudo systemctl restart pi-player.service media-player.service
curl -X POST "http://localhost:8000/playlist/load-default?use_cloudinary=false"
```

The system should now display sample videos in fullscreen kiosk mode!

## 📞 Support

- Check service status: `sudo systemctl status pi-player.service media-player.service`
- View logs: `journalctl -u pi-player.service -f`  
- Test API: `curl http://localhost:8000/health`
- Load content: `curl -X POST "http://localhost:8000/playlist/load-default?use_cloudinary=false"`

---

**Happy Pi Playing! 🍓🎵📺**
