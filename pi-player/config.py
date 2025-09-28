#!/usr/bin/env python3
"""
Pi Player Configuration
Centralized configuration for all Pi player components
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration settings for Pi Player system"""
    
    # Base paths
    BASE_DIR: Path = Path("/home/pi/pi-player")
    MEDIA_CACHE_DIR: Path = BASE_DIR / "media_cache"
    LOGS_DIR: Path = BASE_DIR / "logs" 
    SERVICES_DIR: Path = BASE_DIR / "services"
    
    # Data files
    PLAYLIST_FILE: Path = BASE_DIR / "current_playlist.json"
    PLAYBACK_STATE_FILE: Path = BASE_DIR / "playback_state.json"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Pi Player API"
    API_VERSION: str = "1.0.0"
    
    # Media player settings
    PLAYER_CHECK_INTERVAL: float = 1.0  # seconds
    IMAGE_DISPLAY_DURATION: int = 10    # seconds for image display
    PLAYLIST_LOOP: bool = True
    
    # Download settings
    DOWNLOAD_TIMEOUT: int = 30          # seconds
    MAX_CONCURRENT_DOWNLOADS: int = 3
    CHECKSUM_ALGORITHM: str = "sha256"
    VERIFY_SSL: bool = True
    
    # Telemetry settings
    TELEMETRY_INTERVAL: float = 5.0     # seconds
    TEMPERATURE_SENSOR_PATH: str = "/sys/class/thermal/thermal_zone0/temp"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 3
    
    # Process names for monitoring
    PLAYER_PROCESSES: list = None
    
    def __post_init__(self):
        """Initialize computed values and create directories"""
        if self.PLAYER_PROCESSES is None:
            self.PLAYER_PROCESSES = ["vlc", "cvlc", "ffmpeg", "feh"]
        
        # Ensure directories exist
        self.MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_log_path(self, component_name: str) -> Path:
        """Get log file path for a component"""
        return self.LOGS_DIR / f"{component_name}.log"
    
    def get_media_path(self, filename: str) -> Path:
        """Get full path for cached media file"""
        return self.MEDIA_CACHE_DIR / filename
    
    def is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        return Path(filename).suffix.lower() in image_extensions
    
    def is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        return Path(filename).suffix.lower() in video_extensions
    
    def is_audio_file(self, filename: str) -> bool:
        """Check if file is audio based on extension"""
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
        return Path(filename).suffix.lower() in audio_extensions


# Global configuration instance
config = Config()

# Update paths if running in development environment
if os.getenv('PI_PLAYER_DEV', '').lower() == 'true':
    # Use current directory for development
    current_dir = Path.cwd()
    config.BASE_DIR = current_dir / "pi-player"
    config.MEDIA_CACHE_DIR = config.BASE_DIR / "media_cache"
    config.LOGS_DIR = config.BASE_DIR / "logs"
    config.SERVICES_DIR = config.BASE_DIR / "services"
    config.PLAYLIST_FILE = config.BASE_DIR / "current_playlist.json"
    config.PLAYBACK_STATE_FILE = config.BASE_DIR / "playback_state.json"
    
    # Recreate directories with new paths
    config.__post_init__()