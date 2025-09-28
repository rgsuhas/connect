# Pi Player - Raspberry Pi Media Player System

A complete media player solution for Raspberry Pi that provides remote playlist management via REST API with automatic media downloading, caching, and playback.

## 🎯 Features

- **REST API** for remote playlist management
- **Automatic media downloading** with checksum verification
- **Intelligent caching** with incremental updates
- **Multi-format support**: Video (MP4, AVI, MKV), Audio (MP3, WAV, FLAC), Images (JPG, PNG, GIF)
- **Looping playback** with configurable durations
- **Default screen display** when no playlist is active
- **System telemetry** and health monitoring
- **Auto-start services** with systemd integration
- **Robust error handling** with automatic restarts

## 📁 System Architecture

```
/home/pi/pi-player/
├── config.py              # Centralized configuration
├── pi_server.py           # FastAPI REST server
├── media_player.py        # Media playback daemon
├── media_downloader.py    # Download manager with caching
├── telemetry.py          # System health monitoring
├── logger_setup.py       # Logging utilities
├── test_system.py        # Comprehensive test suite
├── install.sh            # Automated installer
├── run.sh                # Boot startup script
├── setup_boot.sh         # Boot configuration script
├── media_cache/          # Downloaded media files
├── logs/                 # Application logs
└── services/             # Systemd service files
    ├── pi-player.service
    ├── media-player.service
    └── pi-player-startup.service
```

## 🚀 Quick Installation

1. **Download and run the installer:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/your-org/pi-player/main/install.sh | bash
   ```

2. **Or manual installation:**
   ```bash
   git clone https://github.com/your-org/pi-player.git
   cd pi-player
   chmod +x install.sh
   ./install.sh
   ```

## 📋 Manual Installation Steps

### Prerequisites
- Raspberry Pi OS (Lite or Desktop)
- Internet connection
- sudo privileges

### Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system packages
sudo apt install -y python3 python3-pip vlc ffmpeg feh curl wget git

# Install Python packages
pip3 install --user fastapi[standard] uvicorn[standard] psutil requests
```

### Setup
```bash
# Create directories
sudo mkdir -p /home/pi/pi-player/{media_cache,logs,services}
sudo chown -R pi:pi /home/pi/pi-player

# Copy files to installation directory
cp *.py /home/pi/pi-player/
cp services/*.service /home/pi/pi-player/services/

# Install systemd services
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-player.service media-player.service

# Start services
sudo systemctl start pi-player.service media-player.service
```

## 🔧 Configuration

All configuration is centralized in `config.py`:

```python
# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000

# Media player settings
IMAGE_DISPLAY_DURATION = 10  # seconds
PLAYLIST_LOOP = True

# Download settings
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_TIMEOUT = 30

# Default screen settings
SHOW_DEFAULT_SCREEN = True       # Show branded screen when idle
DEFAULT_SCREEN_TIMEOUT = 30      # Seconds before showing default screen
```

## 🌐 API Endpoints

### Base URL: `http://your-pi-ip:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `GET` | `/telemetry` | System telemetry |
| `GET` | `/playlist` | Get current playlist |
| `POST` | `/playlist` | Update playlist |
| `POST` | `/control/{action}` | Control playback |

### Playlist Format

```json
{
    "version": "1.0",
    "last_updated": "2024-01-01T12:00:00Z",
    "loop": true,
    "items": [
        {
            "filename": "video1.mp4",
            "url": "https://example.com/video1.mp4",
            "checksum": "sha256hash",
            "duration": 30
        },
        {
            "filename": "image1.jpg",
            "url": "https://example.com/image1.jpg",
            "duration": 10
        }
    ]
}
```

## 📡 API Usage Examples

### Update Playlist
```bash
curl -X POST http://your-pi-ip:8000/playlist \
     -H "Content-Type: application/json" \
     -d '{
       "version": "1.0",
       "loop": true,
       "items": [
         {
           "filename": "sample.jpg",
           "url": "https://picsum.photos/1920/1080",
           "duration": 5
         }
       ]
     }'
```

### Get System Telemetry
```bash
curl http://your-pi-ip:8000/telemetry | python3 -m json.tool
```

### Check Health
```bash
curl http://your-pi-ip:8000/health
```

## 🎮 Media Player Features

### Supported Formats

- **Video**: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V
- **Audio**: MP3, WAV, FLAC, AAC, OGG, M4A, WMA  
- **Images**: JPG, JPEG, PNG, GIF, BMP, WebP, TIFF

### Players Used

- **VLC (cvlc)**: Video and audio files
- **feh**: Image files with slideshow functionality
- **ffmpeg**: Fallback for unsupported formats

### Playback Control

The media player daemon:
- Monitors playlist changes in real-time
- Automatically restarts playback when playlist updates
- Supports looping and sequential playback
- Handles process cleanup gracefully
- Updates playback state for telemetry
- Shows branded default screen when idle

## 📊 Telemetry Data

The system provides comprehensive telemetry:

```json
{
    "timestamp": "2024-01-01T12:00:00",
    "system": {
        "cpu": {"percent": 25.5, "count": 4},
        "memory": {"total_mb": 1024, "used_mb": 512},
        "disk": {"total_gb": 32, "used_gb": 8}
    },
    "temperature_celsius": 45.2,
    "uptime": {
        "boot_time": "2024-01-01T00:00:00",
        "uptime_hours": 12.5
    },
    "processes": [...],
    "playback": {
        "status": "playing",
        "current_item": "video1.mp4"
    },
    "playlist": {
        "version": "1.0",
        "total_items": 5
    }
}
```

## 🔧 System Management

### Service Control
```bash
# Check service status
sudo systemctl status pi-player.service
sudo systemctl status media-player.service

# Restart services
sudo systemctl restart pi-player.service
sudo systemctl restart media-player.service

# View logs
journalctl -u pi-player.service -f
journalctl -u media-player.service -f
```

### Utility Scripts

After installation, several utility scripts are available:

```bash
# Check system status
/home/pi/pi-player/status.sh

# Restart all services  
/home/pi/pi-player/restart.sh

# Update system (if using git)
/home/pi/pi-player/update.sh
```

### Log Files

All components write to rotating log files:

- `/home/pi/pi-player/logs/pi_server.log` - API server logs
- `/home/pi/pi-player/logs/media_player.log` - Media player logs
- `/home/pi/pi-player/logs/telemetry.log` - Telemetry logs
- `/home/pi/pi-player/logs/downloader.log` - Download logs

## 🧪 Testing

Run the comprehensive test suite:

```bash
cd /home/pi/pi-player
python3 test_system.py
```

The test suite validates:
- Module imports and configuration
- Telemetry collection
- Media downloader functionality
- API endpoints
- Media player logic
- Logging functionality

## 🔒 Security Considerations

- Services run as the `pi` user (non-root)
- Restricted file system access via systemd
- API server binds to all interfaces by default
- Consider using a firewall for production deployments
- HTTPS termination recommended for external access

## 🌐 Network Configuration

### Local Network Access
By default, the API is accessible on port 8000 from any device on your network.

### External Access Options

1. **Port Forwarding**: Forward router port 8000 to Pi
2. **VPN**: Use Tailscale, WireGuard, or OpenVPN
3. **Reverse Proxy**: Use ngrok for temporary access
4. **Cloud Tunnel**: Cloudflare Tunnel for permanent access

### Firewall Setup
```bash
# Allow API access
sudo ufw allow 8000/tcp
sudo ufw enable
```

## 🔄 Auto-Start Configuration

Services are configured to start automatically on boot:

```ini
[Unit]
After=network-online.target
Wants=network-online.target

[Service]
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🚀 Automatic Boot Startup

Pi Player includes a comprehensive boot startup system that ensures your Pi is ready for playlists immediately after power-on.

### Boot Startup Features

- **Multiple startup methods** for maximum reliability
- **Health checking** and service recovery
- **Network connectivity verification**
- **System preparation** and environment setup
- **Comprehensive logging** of startup process

### Manual Boot Setup

```bash
# Configure automatic startup
./setup_boot.sh

# Test startup manually
./run.sh

# Test specific startup script
./test_startup.sh
```

### Startup Methods Configured

1. **Systemd Service** (Primary)
   - `pi-player-startup.service` runs on boot
   - Handles service dependencies and timing
   - Automatic restart on failure

2. **Cron Job** (Fallback)
   - `@reboot` cron entry for backup startup
   - Runs after 60-second delay for system stability

3. **Desktop Autostart** (GUI environments)
   - Autostart entry for desktop sessions
   - Useful for Pi Desktop installations

### Boot Process

1. **System Preparation**
   - Wait for network connectivity
   - Set up display and audio environment
   - Create directories and set permissions

2. **Service Management**
   - Check service installation
   - Start API server and media player
   - Enable services for future boots

3. **Health Verification**
   - API endpoint testing
   - Service status validation
   - Network connectivity check

4. **Ready State**
   - Display system status report
   - Log startup completion
   - Pi ready for playlist management

### Startup Logs

```bash
# View startup logs
tail -f /home/pi/pi-player/logs/startup.log

# View systemd startup service logs
sudo journalctl -u pi-player-startup.service -f

# View main service logs
sudo journalctl -u pi-player.service -u media-player.service -f
```

## 🛠️ Troubleshooting

### Common Issues

1. **API not responding**
   ```bash
   sudo systemctl status pi-player.service
   journalctl -u pi-player.service --no-pager
   ```

2. **Media not playing**
   ```bash
   sudo systemctl status media-player.service
   # Check if display is available for GUI applications
   echo $DISPLAY
   ```

3. **Downloads failing**
   ```bash
   tail -f /home/pi/pi-player/logs/downloader.log
   # Check network connectivity
   curl -I https://example.com
   ```

4. **Permission errors**
   ```bash
   sudo chown -R pi:pi /home/pi/pi-player
   chmod +x /home/pi/pi-player/*.py
   ```

### Debug Mode

Enable verbose logging by editing `config.py`:
```python
LOG_LEVEL = "DEBUG"
```

Then restart services:
```bash
sudo systemctl restart pi-player.service media-player.service
```

## 📝 Development

### Development Mode

For development, set the environment variable:
```bash
export PI_PLAYER_DEV=true
python3 pi_server.py
```

This uses the current directory instead of `/home/pi/pi-player`.

### Adding New Features

1. **New media formats**: Update `config.py` file type detection
2. **New API endpoints**: Add to `pi_server.py`
3. **Custom players**: Modify `media_player.py` command generation
4. **Enhanced telemetry**: Extend `telemetry.py` collectors

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Logs**: Check systemd journals and log files
- **Testing**: Run `python3 test_system.py`

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

**Happy Pi Playing! 🍓🎵📺**