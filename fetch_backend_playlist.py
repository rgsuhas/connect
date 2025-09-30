#!/usr/bin/env python3
"""
Backend Playlist Fetcher for Pi Player
Fetches playlist from backend API, converts format, and saves locally
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from backend_client import BackendClient
from config import config

def extract_filename_from_url(url: str, item_id: str = None) -> str:
    """Extract filename from Cloudinary URL or generate one"""
    try:
        # Parse the URL to get the path
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # For Cloudinary URLs, extract the filename from the path
        if 'cloudinary' in url.lower():
            # Example: /video/upload/v1759147825/conekt/videos/video_1759147816545_bdbbo6k1k.mp4
            filename = Path(path).name
            if filename and '.' in filename:
                return filename
        
        # Fallback: generate filename from item_id or URL hash
        if item_id:
            return f"{item_id}.mp4"
        else:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            return f"video_{url_hash}.mp4"
            
    except Exception as e:
        print(f"Warning: Could not extract filename from {url}: {e}")
        # Last resort: generate a random filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"video_{url_hash}.mp4"

def convert_backend_playlist_to_player_format(backend_playlist: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert backend playlist format to player format
    
    Backend format:
    {
        'timestamp': '2025-09-30T19:34:04.349Z',
        'version': 'v1759151026822',
        'playlist': [
            {
                'id': '68da7739325d28ed8aaca264',
                'type': 'video',
                'url': 'https://res.cloudinary.com/dwvkpgwor/video/upload/...',
                'checksum': '29a0dbea59bc9dfb8fbdb7b1894b627b',
                'duration': 20,
                'loop': False
            }
        ]
    }
    
    Player format:
    {
        "version": "v1.0",
        "last_updated": "2024-01-01T12:00:00Z",
        "loop": true,
        "description": "Backend playlist",
        "source": "backend_api",
        "items": [
            {
                "filename": "video.mp4",
                "url": "https://example.com/video.mp4",
                "duration": 30,
                "checksum": "sha256hash"
            }
        ]
    }
    """
    
    # Extract basic info
    version = backend_playlist.get('version', 'unknown')
    timestamp = backend_playlist.get('timestamp', datetime.now().isoformat())
    backend_items = backend_playlist.get('playlist', [])
    
    # Determine if any item has loop=True (use OR logic)
    should_loop = True  # force loop on device
    
    # Convert items
    player_items = []
    for item in backend_items:
        filename = extract_filename_from_url(item.get('url', ''), item.get('id'))
        
        player_item = {
            "filename": filename,
            "url": item.get('url', ''),
            "duration": item.get('duration', 30),
            "checksum": item.get('checksum')
        }
        
        player_items.append(player_item)
    
    # Create player format
    player_playlist = {
        "version": version,
        "last_updated": timestamp,
        "loop": should_loop,
        "description": f"Backend playlist fetched at {timestamp}",
        "source": "backend_api",
        "items": player_items
    }
    
    return player_playlist

def fetch_and_save_backend_playlist() -> bool:
    """Fetch playlist from backend and save in player format"""
    try:
        print("Fetching playlist from backend...")
        
        # Create backend client
        client = BackendClient()
        
        # Fetch playlist
        backend_playlist = client.get_playlist_from_backend()
        
        if not backend_playlist:
            print("No playlist available from backend")
            return False
        
        print(f"Backend playlist received: {len(backend_playlist.get('playlist', []))} items")
        
        # Convert format
        player_playlist = convert_backend_playlist_to_player_format(backend_playlist)
        
        print(f"Converted to player format: {len(player_playlist.get('items', []))} items")
        
        # Save to current playlist file
        playlist_file = config.PLAYLIST_FILE
        
        # Create backup of existing playlist if it exists
        if playlist_file.exists():
            backup_file = playlist_file.with_suffix('.json.backup')
            print(f"Creating backup: {backup_file}")
            with open(backup_file, 'w') as f:
                with open(playlist_file, 'r') as orig:
                    f.write(orig.read())
        
        # Write new playlist
        with open(playlist_file, 'w') as f:
            json.dump(player_playlist, f, indent=2)
        
        print(f"Backend playlist saved to: {playlist_file}")
        print(f"Playlist version: {player_playlist.get('version')}")
        print(f"Items: {len(player_playlist.get('items', []))}")
        
        # Print item details
        for i, item in enumerate(player_playlist.get('items', []), 1):
            print(f"  {i}. {item.get('filename')} ({item.get('duration')}s)")
        
        return True
        
    except Exception as e:
        print(f"Error fetching backend playlist: {e}")
        return False

if __name__ == "__main__":
    success = fetch_and_save_backend_playlist()
    if success:
        print("✅ Backend playlist fetched and saved successfully!")
    else:
        print("❌ Failed to fetch backend playlist")

def cleanup_old_cache_after_playlist_update(new_version: str, old_version: str = None) -> bool:
    """Run cache cleanup after playlist update"""
    try:
        # Only run cleanup if playlist version actually changed
        if old_version and new_version == old_version:
            print("Playlist version unchanged, skipping cleanup")
            return True
        
        print(f"\nPlaylist changed from '{old_version}' to '{new_version}', running cache cleanup...")
        
        # Import and run cleanup
        from cleanup_old_cache import cleanup_old_cache_files
        result = cleanup_old_cache_files(dry_run=False)
        
        if result["deleted_count"] > 0:
            freed_mb = result["freed_bytes"] / (1024 * 1024)
            print(f"🧹 Cleaned up {result['deleted_count']} old files, freed {freed_mb:.1f} MB")
        else:
            print("✅ No old files to clean up")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Cache cleanup failed: {e}")
        return False

def fetch_and_save_backend_playlist_with_cleanup() -> bool:
    """Fetch playlist from backend, save, and cleanup old files"""
    try:
        print("Fetching playlist from backend...")
        
        # Get current playlist version (if exists)
        old_version = None
        if config.PLAYLIST_FILE.exists():
            try:
                with open(config.PLAYLIST_FILE, 'r') as f:
                    old_playlist = json.load(f)
                    old_version = old_playlist.get('version')
            except:
                pass
        
        # Create backend client
        client = BackendClient()
        
        # Fetch playlist
        backend_playlist = client.get_playlist_from_backend()
        
        if not backend_playlist:
            print("No playlist available from backend")
            return False
        
        print(f"Backend playlist received: {len(backend_playlist.get('playlist', []))} items")
        
        # Convert format
        player_playlist = convert_backend_playlist_to_player_format(backend_playlist)
        new_version = player_playlist.get('version')
        
        print(f"Converted to player format: {len(player_playlist.get('items', []))} items")
        
        # Save to current playlist file
        playlist_file = config.PLAYLIST_FILE
        
        # Create backup of existing playlist if it exists
        if playlist_file.exists():
            backup_file = playlist_file.with_suffix('.json.backup')
            print(f"Creating backup: {backup_file}")
            with open(backup_file, 'w') as f:
                with open(playlist_file, 'r') as orig:
                    f.write(orig.read())
        
        # Write new playlist
        with open(playlist_file, 'w') as f:
            json.dump(player_playlist, f, indent=2)
        
        print(f"Backend playlist saved to: {playlist_file}")
        print(f"Playlist version: {new_version}")
        print(f"Items: {len(player_playlist.get('items', []))}")
        
        # Print item details
        for i, item in enumerate(player_playlist.get('items', []), 1):
            print(f"  {i}. {item.get('filename')} ({item.get('duration')}s)")
        
        # Run cache cleanup if playlist changed
        cleanup_old_cache_after_playlist_update(new_version, old_version)
        
        return True
        
    except Exception as e:
        print(f"Error fetching backend playlist: {e}")
        return False

if __name__ == "__main__":
    # Use the new function with cleanup
    success = fetch_and_save_backend_playlist_with_cleanup()
    if success:
        print("✅ Backend playlist fetched, saved, and cache cleaned successfully!")
    else:
        print("❌ Failed to fetch backend playlist")
