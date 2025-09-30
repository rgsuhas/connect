#!/usr/bin/env python3
"""
Cache Cleanup for Pi Player
Removes old cached media files that are not in the current playlist
"""

import json
import os
from pathlib import Path
from typing import Set, List
from datetime import datetime

from config import config

def get_current_playlist_filenames() -> Set[str]:
    """Get set of filenames from current playlist"""
    try:
        if not config.PLAYLIST_FILE.exists():
            print("No current playlist file found")
            return set()
        
        with open(config.PLAYLIST_FILE, 'r') as f:
            playlist = json.load(f)
        
        items = playlist.get('items', [])
        filenames = {item.get('filename') for item in items if item.get('filename')}
        
        print(f"Current playlist contains {len(filenames)} files")
        for filename in sorted(filenames):
            print(f"  - {filename}")
        
        return filenames
        
    except Exception as e:
        print(f"Error reading playlist: {e}")
        return set()

def get_cached_filenames() -> Set[str]:
    """Get set of filenames currently in cache"""
    try:
        cache_dir = config.MEDIA_CACHE_DIR
        if not cache_dir.exists():
            return set()
        
        cached_files = set()
        for file_path in cache_dir.iterdir():
            if file_path.is_file() and file_path.name != '.gitkeep':
                cached_files.add(file_path.name)
        
        print(f"Cache contains {len(cached_files)} files")
        for filename in sorted(cached_files):
            print(f"  - {filename}")
        
        return cached_files
        
    except Exception as e:
        print(f"Error reading cache directory: {e}")
        return set()

def cleanup_old_cache_files(dry_run: bool = False) -> dict:
    """
    Remove cached files that are not in current playlist
    
    Args:
        dry_run: If True, only show what would be deleted without actually deleting
    
    Returns:
        Dict with cleanup statistics
    """
    print("🧹 Starting cache cleanup...")
    
    # Get current playlist files
    playlist_files = get_current_playlist_filenames()
    
    # Get cached files
    cached_files = get_cached_filenames()
    
    # Find files to delete (in cache but not in playlist)
    files_to_delete = cached_files - playlist_files
    files_to_keep = cached_files & playlist_files
    
    print(f"\n📊 Cache Analysis:")
    print(f"  Files in playlist: {len(playlist_files)}")
    print(f"  Files in cache: {len(cached_files)}")
    print(f"  Files to keep: {len(files_to_keep)}")
    print(f"  Files to delete: {len(files_to_delete)}")
    
    if not files_to_delete:
        print("✅ No old files to clean up!")
        return {
            "deleted_count": 0,
            "deleted_files": [],
            "freed_bytes": 0,
            "kept_files": list(files_to_keep)
        }
    
    # Calculate sizes and delete files
    deleted_files = []
    total_freed_bytes = 0
    
    for filename in files_to_delete:
        try:
            file_path = config.MEDIA_CACHE_DIR / filename
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                
                if dry_run:
                    print(f"  [DRY RUN] Would delete: {filename} ({file_size / (1024*1024):.1f} MB)")
                else:
                    print(f"  🗑️  Deleting: {filename} ({file_size / (1024*1024):.1f} MB)")
                    file_path.unlink()
                
                deleted_files.append(filename)
                total_freed_bytes += file_size
                
        except Exception as e:
            print(f"  ❌ Error deleting {filename}: {e}")
    
    freed_mb = total_freed_bytes / (1024 * 1024)
    
    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(deleted_files)} files, freeing {freed_mb:.1f} MB")
    else:
        print(f"\n✅ Cleanup complete!")
        print(f"  Deleted: {len(deleted_files)} files")
        print(f"  Freed space: {freed_mb:.1f} MB")
        print(f"  Kept: {len(files_to_keep)} files")
    
    return {
        "deleted_count": len(deleted_files),
        "deleted_files": deleted_files,
        "freed_bytes": total_freed_bytes,
        "kept_files": list(files_to_keep),
        "dry_run": dry_run
    }

if __name__ == "__main__":
    import sys
    
    # Check for dry run argument
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will actually be deleted\n")
    
    result = cleanup_old_cache_files(dry_run=dry_run)
    
    if not dry_run and result["deleted_count"] > 0:
        print(f"\n💾 Storage freed: {result['freed_bytes'] / (1024*1024):.1f} MB")
