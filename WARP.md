# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

Pi Player is a Raspberry Pi media player system designed for digital signage and kiosk applications. It provides remote playlist management via REST API with automatic media downloading, caching, and fullscreen playback.

The system is architected around three main components:
1. **REST API Server** (`pi_server.py`) - FastAPI-based playlist management
2. **Media Player Daemon** (`player.py`/`media_player.py`) - Handles playback via VLC/MPV/feh
3. **Backend Integration** (`backend_client.py`) - Cloudinary and external API integration

## Quick Commands

### Installation
```bash
# Full installation with systemd services
./install.sh

# Headless installation (no GUI dependencies)  
./install_headless.sh

# Install only systemd services
./install_service.sh
```

### Development Mode
```bash
# Enable development mode (uses current directory instead of /home/pi/pi-player)
export PI_PLAYER_DEV=true

# Run main application
python3 main.py

# Run specific components
python3 pi_server.py          # API server only
python3 main.py --player-only # Media player only
python3 main.py --download    # Download playlist and exit
```

### Testing
```bash
# Run comprehensive test suite
python3 test_system.py

# Run specific tests
python3 test_playlist_integration.py
python3 test_playlist_simple.py
```

### Service Management
```bash
# Control main API service
sudo systemctl start pi-player.service
sudo systemctl stop pi-player.service
sudo systemctl restart pi-player.service
sudo systemctl status pi-player.service

# Control media player service
sudo systemctl start media-player.service
sudo systemctl stop media-player.service
sudo systemctl status media-player.service

# View logs
sudo journalctl -u pi-player.service -f
sudo journalctl -u media-player.service -f
```

### Cache Management
```bash
# Reset/clear media cache
python3 main.py --reset-cache

# Clean old cached files
python3 cleanup_old_cache.py

# Check cache status
python3 main.py --status
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REST API      │    │  Media Player   │    │ Backend Client  │
│  (pi_server.py) │◄──►│   (player.py)   │    │(backend_client) │
│                 │    │                 │    │                 │
│ • Playlist CRUD │    │ • VLC/MPV/feh   │    │ • Cloudinary    │
│ • Telemetry     │    │ • Format detect │    │ • Heartbeat     │
│ • Health check  │    │ • Loop control  │    │ • Playlist sync │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Download Manager│
                    │(download_mgr.py)│
                    │                 │
                    │ • SHA256 verify │
                    │ • Cache mgmt    │
                    │ • Parallel DL   │
                    └─────────────────┘
```

### Key Subsystems

1. **Configuration** (`config.py`)
   - Centralized dataclass-based configuration
   - Auto-creates directories on initialization
   - Environment-aware (development vs production)

2. **Media Player** (`player.py`, `media_player.py`)
   - Supports video (MP4, AVI, MKV), audio (MP3, WAV), images (JPG, PNG)
   - Primary: VLC (cvlc), Secondary: MPV, Images: feh
   - Fullscreen kiosk mode with cursor hiding

3. **Download Manager** (`download_manager.py`)
   - SHA256 checksum verification
   - Incremental cache updates
   - Concurrent downloading with configurable limits

4. **Telemetry** (`telemetry.py`)
   - System stats (CPU, memory, disk, temperature)
   - Process monitoring
   - Playback state tracking

5. **Logging** (`log_setup.py`, `logger_setup.py`)
   - Structured logging with rotation
   - Component-specific log files in `logs/` directory
   - Console + file output support

## Development Patterns

### Configuration Pattern
All components use the centralized config:
```python
from config import config

# Access paths
config.MEDIA_CACHE_DIR
config.PLAYLIST_FILE
config.API_PORT

# File type detection
if config.is_video_file(filename):
    # Handle video
```

### Logging Pattern
Consistent logging setup across components:
```python
from log_setup import setup_logging

logger = setup_logging("component_name", log_level="INFO")
logger.info("Component started")
```

### Service Pattern
Background tasks use threading for non-blocking operations:
```python
import threading
from download_manager import update_cache_for_playlist

def background_download_task(playlist_data):
    # Download in background thread
    threading.Thread(target=update_cache_for_playlist).start()
```

### State Management
Playback state is persisted to JSON files:
- `current_playlist.json` - Active playlist
- `playback_state.json` - Current playback status
- `last_playback.json` - Last played item

## File Structure

```
pi-player/
├── config.py              # Central configuration
├── main.py                 # Main entry point
├── pi_server.py           # FastAPI REST server
├── player.py              # Main media player
├── media_player.py        # Player implementation
├── download_manager.py    # Media download & cache
├── backend_client.py      # External API client
├── telemetry.py          # System monitoring
├── playlist_manager.py   # Playlist operations
├── log_setup.py          # Logging utilities
├── services/             # Systemd service files
│   ├── pi-player.service
│   ├── media-player.service
│   └── pi-player-startup.service
├── logs/                 # Application logs
├── media_cache/          # Downloaded media files
├── playlists/           # Playlist storage
├── default_assets/      # Default screens
└── deployment/          # Deployment scripts
```

## Environment Configuration

The system supports both production and development environments:

**Production** (default):
- Base directory: `/home/pi/pi-player/`
- Systemd services enabled
- Runs as `pi` user

**Development**:
```bash
export PI_PLAYER_DEV=true
# Uses current working directory
# Logs to console + files
# No systemd dependency
```

## Common Tasks

### Adding New Media Format
1. Update `config.py` file type detection methods
2. Add player command in `media_player.py` or `player.py`
3. Test with sample files

### Modifying API Endpoints
1. Edit `pi_server.py` FastAPI routes
2. Update playlist schema validation
3. Test with `python3 test_system.py`

### Changing Backend Integration
1. Modify `backend_client.py` client implementation
2. Update `config.py` backend settings
3. Test with `python3 fetch_backend_playlist.py`

## Troubleshooting

### Common Issues

**Media not playing:**
```bash
# Check display environment
echo $DISPLAY
export DISPLAY=:0

# Check service status
sudo systemctl status media-player.service
```

**API not responding:**
```bash
# Check service and port
sudo systemctl status pi-player.service
netstat -tlnp | grep :8000
```

**Download failures:**
```bash
# Check network and logs
tail -f logs/downloader.log
curl -I https://example.com/test-media.mp4
```

**Permission errors:**
```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/pi-player
chmod +x *.py
```

### Debug Mode
Enable verbose logging:
```python
# In config.py
LOG_LEVEL = "DEBUG"
```

### Service Logs
```bash
# View all pi-player logs
sudo journalctl -u pi-player.service -u media-player.service -f

# View specific component logs  
tail -f logs/pi_server.log
tail -f logs/media_player.log
tail -f logs/telemetry.log
```

## API Usage

### Base URL
`http://localhost:8000` (or Pi's IP address)

### Key Endpoints
- `GET /health` - Health check
- `GET /telemetry` - System telemetry
- `GET /playlist` - Get current playlist
- `POST /playlist` - Update playlist
- `POST /control/{action}` - Control playback

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
        }
    ]
}
```

