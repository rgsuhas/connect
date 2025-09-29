#!/usr/bin/env python3
"""
Playlist Manager for Pi Player
Manages playlist loading with backend API integration and default fallback
"""

import json
import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from config import config
from backend_client import get_backend_client

# Setup logging
logger = logging.getLogger("playlist_manager")
logger.setLevel(getattr(logging, config.LOG_LEVEL))
if not logger.handlers:
    fh = logging.FileHandler(config.get_log_path("playlist_manager"))
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

# Hard-coded default Cloudinary collection URLs for fallback
DEFAULT_CLOUDINARY_COLLECTIONS = [
    "https://collection.cloudinary.com/dxfhfpaym/8006a0aeec057b5fdae295b27ea0f1e2",
    "https://collection.cloudinary.com/dxfhfpaym/a8763aa70fe1ae9284552d3b2aba5ebf",
    "https://collection.cloudinary.com/dxfhfpaym/173ef9cfc1e34d25a3241c1bfdc6c733",
    "https://collection.cloudinary.com/dxfhfpaym/329afc666ff08426da6c2f2f2a529ea8",
    "https://collection.cloudinary.com/dxfhfpaym/d4ac678778867b5fbe15e2a1f10fb589",
    "https://collection.cloudinary.com/dxfhfpaym/152008e9ff99a72cb8de06f125dab9b8",
    "https://collection.cloudinary.com/dxfhfpaym/9a919c47d389473ff2d9b4ceff7b1093"
]

class PlaylistManager:
    """Manages playlist with backend integration and default fallback"""
    
    def __init__(self):
        self.last_backend_check = None
        self.backend_available = False
        self.default_playlist_loaded = False
        self.current_playlist_source = None  # "backend", "default", or None
        self.lock = threading.Lock()
        
        # Time tracking
        self.startup_time = time.time()
        self.default_fallback_delay = getattr(config, 'DEFAULT_PLAYLIST_DELAY', 120)  # 2 minutes
    
    def get_default_cloudinary_playlist(self) -> Dict[str, Any]:
        """Create default playlist with Cloudinary collection URLs"""
        
        # Create placeholder items for each collection
        items = []
        for i, collection_url in enumerate(DEFAULT_CLOUDINARY_COLLECTIONS, 1):
            # Extract collection ID from URL
            collection_id = collection_url.split('/')[-1]
            
            items.append({
                "filename": f"cloudinary_collection_{i}.mp4",
                "url": collection_url,  # Use collection URL directly
                "duration": 30,  # Default duration
                "checksum": None,  # No checksum for placeholder
                "metadata": {
                    "source": "cloudinary_collection", 
                    "collection_id": collection_id,
                    "collection_url": collection_url,
                    "note": "This is a Cloudinary collection URL - requires JavaScript to access actual videos"
                }
            })
        
        playlist = {
            "version": "default-cloudinary-v1.0",
            "last_updated": datetime.now().isoformat(),
            "loop": True,
            "description": "Default Cloudinary collection playlist - fallback when no backend playlist available",
            "source": "default_fallback",
            "cloudinary_collections": DEFAULT_CLOUDINARY_COLLECTIONS,
            "items": items
        }
        
        return playlist
    
    def create_sample_video_playlist(self) -> Dict[str, Any]:
        """Create a playlist with working sample videos for immediate testing"""
        
        sample_videos = [
            {
                "filename": "big_buck_bunny.mp4",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "duration": 60,
                "checksum": None
            },
            {
                "filename": "elephants_dream.mp4",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4", 
                "duration": 60,
                "checksum": None
            },
            {
                "filename": "for_bigger_blazes.mp4",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                "duration": 15,
                "checksum": None
            },
            {
                "filename": "for_bigger_escapes.mp4",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                "duration": 15,
                "checksum": None
            },
            {
                "filename": "for_bigger_fun.mp4",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                "duration": 60,
                "checksum": None
            }
        ]
        
        playlist = {
            "version": "default-samples-v1.0",
            "last_updated": datetime.now().isoformat(),
            "loop": True,
            "description": "Default sample video playlist - immediate playback capability",
            "source": "default_samples",
            "items": sample_videos
        }
        
        return playlist
    
    def check_backend_playlist_availability(self) -> Optional[Dict[str, Any]]:
        """Check if backend has a playlist available"""
        
        if not config.BACKEND_ENABLED:
            logger.debug("Backend integration disabled")
            return None
        
        try:
            backend_client = get_backend_client()
            playlist_data = backend_client.get_playlist_from_backend()
            
            if playlist_data:
                logger.info(f"Backend playlist available: version {playlist_data.get('version', 'unknown')}")
                self.backend_available = True
                self.last_backend_check = time.time()
                return playlist_data
            else:
                logger.info("No playlist available from backend")
                self.backend_available = False
                self.last_backend_check = time.time()
                return None
                
        except Exception as e:
            logger.warning(f"Backend playlist check failed: {e}")
            self.backend_available = False
            self.last_backend_check = time.time()
            return None
    
    def should_load_default_playlist(self) -> bool:
        """Determine if we should load the default playlist"""
        
        # Don't load default if we already have one loaded
        if self.default_playlist_loaded:
            return False
        
        # Don't load default if we have a current playlist file and it's not too old
        if config.PLAYLIST_FILE.exists():
            try:
                with open(config.PLAYLIST_FILE, 'r') as f:
                    existing_playlist = json.load(f)
                
                # If it's a backend playlist, don't override with default
                if existing_playlist.get('source') == 'backend':
                    return False
                
                # If it's already a default playlist, don't reload
                if existing_playlist.get('source') in ['default_fallback', 'default_samples']:
                    return False
            except Exception:
                pass  # If we can't read it, we'll create a new one
        
        # Load default if we've been running long enough without backend playlist
        time_since_startup = time.time() - self.startup_time
        
        if time_since_startup >= self.default_fallback_delay:
            if not self.backend_available or self.last_backend_check is None:
                return True
        
        return False
    
    def load_default_playlist(self, use_cloudinary: bool = True) -> bool:
        """Load the default playlist as fallback"""
        
        with self.lock:
            try:
                # Choose which default playlist to use
                if use_cloudinary:
                    playlist_data = self.get_default_cloudinary_playlist()
                    logger.info("Loading default Cloudinary collection playlist")
                else:
                    playlist_data = self.create_sample_video_playlist()
                    logger.info("Loading default sample video playlist")
                
                # Save to playlist file
                with open(config.PLAYLIST_FILE, 'w') as f:
                    json.dump(playlist_data, f, indent=2)
                
                self.default_playlist_loaded = True
                self.current_playlist_source = "default_fallback" if use_cloudinary else "default_samples"
                
                logger.info(f"Default playlist loaded with {len(playlist_data['items'])} items")
                logger.info(f"Playlist source: {self.current_playlist_source}")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to load default playlist: {e}")
                return False
    
    def ensure_playlist_available(self) -> bool:
        """Ensure a playlist is available, loading default if necessary"""
        
        # First, check if we have a recent backend playlist
        backend_playlist = self.check_backend_playlist_availability()
        
        if backend_playlist:
            # Backend playlist available, use it
            try:
                with open(config.PLAYLIST_FILE, 'w') as f:
                    json.dump(backend_playlist, f, indent=2)
                
                self.current_playlist_source = "backend"
                self.default_playlist_loaded = False  # Reset default flag
                
                logger.info(f"Backend playlist loaded: version {backend_playlist.get('version')}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save backend playlist: {e}")
        
        # No backend playlist, check if we should load default
        if self.should_load_default_playlist():
            logger.info("No backend playlist available, loading default fallback playlist")
            return self.load_default_playlist(use_cloudinary=True)
        
        # Check if we have any existing playlist
        if config.PLAYLIST_FILE.exists():
            try:
                with open(config.PLAYLIST_FILE, 'r') as f:
                    existing_playlist = json.load(f)
                
                if existing_playlist.get('items'):
                    logger.info(f"Using existing playlist: {existing_playlist.get('description', 'Unknown')}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Failed to read existing playlist: {e}")
        
        # No playlist available at all, create a minimal one
        logger.warning("No playlist available from any source, creating minimal default")
        return self.load_default_playlist(use_cloudinary=False)  # Use sample videos as last resort
    
    def get_playlist_status(self) -> Dict[str, Any]:
        """Get current playlist management status"""
        
        status = {
            "backend_enabled": config.BACKEND_ENABLED,
            "backend_available": self.backend_available,
            "last_backend_check": self.last_backend_check,
            "default_playlist_loaded": self.default_playlist_loaded,
            "current_source": self.current_playlist_source,
            "startup_time": self.startup_time,
            "time_since_startup": time.time() - self.startup_time,
            "fallback_delay": self.default_fallback_delay,
            "playlist_file_exists": config.PLAYLIST_FILE.exists()
        }
        
        # Add current playlist info if available
        if config.PLAYLIST_FILE.exists():
            try:
                with open(config.PLAYLIST_FILE, 'r') as f:
                    playlist_data = json.load(f)
                
                status["current_playlist"] = {
                    "version": playlist_data.get("version", "unknown"),
                    "description": playlist_data.get("description", ""),
                    "item_count": len(playlist_data.get("items", [])),
                    "source": playlist_data.get("source", "unknown"),
                    "last_updated": playlist_data.get("last_updated")
                }
            except Exception as e:
                status["current_playlist"] = {"error": f"Failed to read: {str(e)}"}
        
        return status
    
    def force_refresh_from_backend(self) -> bool:
        """Force a refresh attempt from backend, regardless of timing"""
        
        logger.info("Forcing playlist refresh from backend")
        self.last_backend_check = None  # Reset check time
        
        return self.ensure_playlist_available()


# Global playlist manager instance
playlist_manager = PlaylistManager()


def get_playlist_manager() -> PlaylistManager:
    """Get the global playlist manager instance"""
    return playlist_manager


if __name__ == "__main__":
    # Test the playlist manager
    manager = PlaylistManager()
    
    print("Testing Playlist Manager...")
    
    # Test default Cloudinary playlist creation
    cloudinary_playlist = manager.get_default_cloudinary_playlist()
    print(f"Cloudinary playlist: {len(cloudinary_playlist['items'])} items")
    
    # Test sample video playlist creation
    sample_playlist = manager.create_sample_video_playlist()
    print(f"Sample playlist: {len(sample_playlist['items'])} items")
    
    # Test playlist availability check
    success = manager.ensure_playlist_available()
    print(f"Playlist availability check: {'success' if success else 'failed'}")
    
    # Show status
    status = manager.get_playlist_status()
    print(f"Playlist status: {json.dumps(status, indent=2)}")