# Pi Player Environment Configuration

This document describes all environment variables and configuration files required for the pi-player digital signage system.

## Configuration Files Overview

The pi-player system uses several configuration files and environment variables to control its behavior:

- `config.py` - Main Python configuration module
- `current_playlist.json` - Active playlist data
- `player_state.json` - Player runtime state
- Environment variables - Runtime configuration
- `.bashrc` additions - Shell environment setup

## Main Configuration (`config.py`)

The primary configuration is managed through a Python class in `config.py`:

### Template

```python
from pathlib import Path
import os

class Config:
    def __init__(self):
        # Base directory
        self.BASE_DIR = Path(__file__).parent.absolute()
        
        # Core directories
        self.MEDIA_CACHE_DIR = self.BASE_DIR / "media_cache"
        self.DEFAULT_ASSETS_DIR = self.BASE_DIR / "default_assets"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        
        # Ensure directories exist
        self.MEDIA_CACHE_DIR.mkdir(exist_ok=True)
        self.DEFAULT_ASSETS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        
        # Configuration files
        self.PLAYLIST_FILE = self.BASE_DIR / "current_playlist.json"
        self.STATE_FILE = self.BASE_DIR / "player_state.json"
        
        # Download settings
        self.MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
        self.DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
        self.DOWNLOAD_RETRY_ATTEMPTS = int(os.getenv("DOWNLOAD_RETRY_ATTEMPTS", "3"))
        self.CHECKSUM_ALGORITHM = os.getenv("CHECKSUM_ALGORITHM", "sha256")
        
        # Backend settings
        self.BACKEND_URL = os.getenv("BACKEND_URL", "")
        self.FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", "300"))  # 5 minutes
        self.API_KEY = os.getenv("API_KEY", "")
        self.API_TOKEN = os.getenv("API_TOKEN", "")
        
        # Player settings
        self.DEFAULT_DISPLAY_DURATION = int(os.getenv("DEFAULT_DISPLAY_DURATION", "10"))
        self.LOOP_PLAYLIST = os.getenv("LOOP_PLAYLIST", "true").lower() == "true"
        self.FULLSCREEN_MODE = os.getenv("FULLSCREEN_MODE", "true").lower() == "true"
        
        # Display settings
        self.DISPLAY_WIDTH = int(os.getenv("DISPLAY_WIDTH", "1920"))
        self.DISPLAY_HEIGHT = int(os.getenv("DISPLAY_HEIGHT", "1080"))
        self.ROTATION = int(os.getenv("ROTATION", "0"))  # 0, 90, 180, 270
        
        # Media player settings
        self.PREFERRED_VIDEO_PLAYER = os.getenv("PREFERRED_VIDEO_PLAYER", "mpv")  # mpv, vlc
        self.PREFERRED_IMAGE_VIEWER = os.getenv("PREFERRED_IMAGE_VIEWER", "feh")  # feh, imagemagick
        
        # Logging settings
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR
        self.LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))
        self.ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
        
        # Network settings
        self.CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))
        self.READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "60"))
        self.USER_AGENT = os.getenv("USER_AGENT", "Pi-Player-Digital-Signage/1.0")
        
        # Cache settings
        self.MAX_CACHE_SIZE_MB = int(os.getenv("MAX_CACHE_SIZE_MB", "1000"))
        self.CACHE_CLEANUP_ENABLED = os.getenv("CACHE_CLEANUP_ENABLED", "true").lower() == "true"
        self.CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "3600"))  # 1 hour
    
    def get_media_path(self, filename: str) -> Path:
        """Get full path for cached media file"""
        return self.MEDIA_CACHE_DIR / filename
    
    def get_log_path(self, component_name: str) -> Path:
        """Get log file path for a component"""
        return self.LOGS_DIR / f"{component_name}.log"
    
    def is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        return Path(filename).suffix.lower() in image_extensions
    
    def is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        return Path(filename).suffix.lower() in video_extensions

# Global config instance
config = Config()
```

### Configuration Options

#### Directory Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_DIR` | *Auto-detected* | Root directory of the pi-player installation |
| `MEDIA_CACHE_DIR` | `{BASE_DIR}/media_cache` | Directory for downloaded media files |
| `DEFAULT_ASSETS_DIR` | `{BASE_DIR}/default_assets` | Directory for default/fallback media |
| `LOGS_DIR` | `{BASE_DIR}/logs` | Directory for log files |

#### Download Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Maximum simultaneous downloads |
| `DOWNLOAD_TIMEOUT` | `60` | Timeout for downloads in seconds |
| `DOWNLOAD_RETRY_ATTEMPTS` | `3` | Number of retry attempts for failed downloads |
| `CHECKSUM_ALGORITHM` | `sha256` | Algorithm for file integrity checking |

#### Backend API Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `BACKEND_URL` | `""` | Base URL for the backend API (required if using API) |
| `FETCH_INTERVAL` | `300` | Interval to fetch new playlists (seconds) |
| `API_KEY` | `""` | API key for backend authentication |
| `API_TOKEN` | `""` | API token for backend authentication |

#### Player Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEFAULT_DISPLAY_DURATION` | `10` | Default display time for images (seconds) |
| `LOOP_PLAYLIST` | `true` | Whether to loop the playlist |
| `FULLSCREEN_MODE` | `true` | Whether to run in fullscreen mode |

#### Display Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DISPLAY_WIDTH` | `1920` | Display resolution width |
| `DISPLAY_HEIGHT` | `1080` | Display resolution height |
| `ROTATION` | `0` | Display rotation in degrees (0, 90, 180, 270) |

#### Media Player Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PREFERRED_VIDEO_PLAYER` | `mpv` | Video player to use (`mpv` or `vlc`) |
| `PREFERRED_IMAGE_VIEWER` | `feh` | Image viewer to use (`feh` or `imagemagick`) |

#### Logging Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_RETENTION_DAYS` | `7` | Days to keep log files |
| `ENABLE_FILE_LOGGING` | `true` | Enable logging to files |

#### Network Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CONNECTION_TIMEOUT` | `30` | Network connection timeout (seconds) |
| `READ_TIMEOUT` | `60` | Network read timeout (seconds) |
| `USER_AGENT` | `Pi-Player-Digital-Signage/1.0` | HTTP User-Agent string |

#### Cache Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MAX_CACHE_SIZE_MB` | `1000` | Maximum cache size in megabytes |
| `CACHE_CLEANUP_ENABLED` | `true` | Enable automatic cache cleanup |
| `CACHE_CLEANUP_INTERVAL` | `3600` | Cache cleanup interval (seconds) |

## Environment Variables Setup

### System Environment Variables

Create a system environment file for the pi-player service:

```bash
# Create environment file for systemd service
sudo tee /etc/systemd/system/pi-player-kiosk.service.d/environment.conf << 'EOF'
[Service]
Environment=BACKEND_URL=https://your-api.example.com
Environment=API_KEY=your-api-key-here
Environment=LOG_LEVEL=INFO
Environment=DEFAULT_DISPLAY_DURATION=15
Environment=MAX_CONCURRENT_DOWNLOADS=2
