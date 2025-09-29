#!/usr/bin/env python3
"""
Pi Player Main Entry Point
Orchestrates the complete Pi Player system with comprehensive logging
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from log_setup import setup_logging, log_system_startup
from config import config
from init_dirs import init_directories
from download_manager import load_and_download_playlist, get_cache_status
from player import MediaPlayer

# Setup main logging
logger = setup_logging("main", log_level="INFO")

def reset_cache() -> bool:
    """Reset/clear the media cache"""
    try:
        logger.info("Resetting media cache...")
        
        cache_dir = config.MEDIA_CACHE_DIR
        if not cache_dir.exists():
            logger.info("Cache directory doesn't exist, nothing to reset")
            return True
        
        # Remove all cached files except .gitkeep
        removed_count = 0
        total_size = 0
        
        for file_path in cache_dir.rglob('*'):
            if file_path.is_file() and file_path.name != '.gitkeep':
                file_size = file_path.stat().st_size
                file_path.unlink()
                removed_count += 1
                total_size += file_size
                logger.debug(f"Removed cached file: {file_path.name}")
        
        logger.info(f"Cache reset complete: removed {removed_count} files ({total_size/(1024*1024):.1f} MB)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset cache: {e}", exc_info=True)
        return False

def initialize_system() -> bool:
    """Initialize the Pi Player system"""
    try:
        logger.info("Initializing Pi Player system...")
        
        # Initialize directories
        result = init_directories()
        logger.info(f"Directory initialization: {result['total']} directories ready")
        
        # Check for playlist
        if not config.PLAYLIST_FILE.exists():
            # Copy default playlist if available
            if config.DEFAULT_PLAYLIST_FILE.exists():
                logger.info("Copying default playlist as active playlist")
                import shutil
                shutil.copy2(config.DEFAULT_PLAYLIST_FILE, config.PLAYLIST_FILE)
            else:
                logger.warning("No default playlist found")
        
        # Initial cache status
        cache_status = get_cache_status()
        logger.info(f"Initial cache status: {cache_status.get('total_files', 0)} files, {cache_status.get('total_size_mb', 0)} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}", exc_info=True)
        return False

def run_download_sync() -> bool:
    """Run download manager to sync playlist"""
    try:
        logger.info("Starting playlist download sync...")
        
        result = load_and_download_playlist()
        
        if "error" in result:
            logger.error(f"Download sync failed: {result['error']}")
            return False
        
        logger.info("Download sync completed", extra={
            "custom_fields": {
                "event_type": "download_sync_completed",
                "downloaded": result.get('downloaded', 0),
                "cached": result.get('cached', 0),
                "errors": result.get('errors', 0),
                "total_bytes": result.get('total_bytes_downloaded', 0)
            }
        })
        
        if result.get('errors', 0) > 0:
            logger.warning(f"Download sync completed with {result['errors']} errors")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Download sync failed: {e}", exc_info=True)
        return False

def run_player_only() -> int:
    """Run only the media player (assumes cache is ready)"""
    try:
        logger.info("Starting Pi Player (player only mode)")
        
        player = MediaPlayer()
        player.run_playback_loop()
        
        return 0
        
    except Exception as e:
        logger.error(f"Player failed: {e}", exc_info=True)
        return 1

def run_full_system() -> int:
    """Run the complete Pi Player system"""
    try:
        logger.info("Starting Pi Player (full system mode)")
        log_system_startup(logger)
        
        # Initialize system
        if not initialize_system():
            logger.error("System initialization failed")
            return 1
        
        # Run initial download sync
        if not run_download_sync():
            logger.warning("Initial download sync failed, will continue with cached files")
        
        # Start the media player
        logger.info("Starting media player...")
        player = MediaPlayer()
        player.run_playback_loop()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Pi Player stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Pi Player system failed: {e}", exc_info=True)
        return 1

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Pi Player - Media Player with Caching and Logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run full Pi Player system
  %(prog)s --player-only      # Run only the media player
  %(prog)s --download         # Download/sync playlist and exit
  %(prog)s --reset-cache      # Clear cache and download fresh
  %(prog)s --status           # Show system status and exit
  %(prog)s --init             # Initialize directories and exit
        """
    )
    
    parser.add_argument(
        "--player-only", 
        action="store_true",
        help="Run only the media player (skip downloads)"
    )
    
    parser.add_argument(
        "--download", 
        action="store_true",
        help="Download/sync playlist files and exit"
    )
    
    parser.add_argument(
        "--reset-cache", 
        action="store_true",
        help="Reset cache and trigger fresh downloads"
    )
    
    parser.add_argument(
        "--status", 
        action="store_true",
        help="Show system status and exit"
    )
    
    parser.add_argument(
        "--init", 
        action="store_true",
        help="Initialize directory structure and exit"
    )
    
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
        default="INFO",
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Update logger level if specified
    if args.log_level != "INFO":
        logger.setLevel(getattr(__import__('logging'), args.log_level))
        logger.info(f"Log level set to {args.log_level}")
    
    # Print banner
    print("🎬 Pi Player - Enhanced Media Player")
    print("=" * 50)
    print(f"Working Directory: {Path.cwd()}")
    print(f"Config Base Dir: {config.BASE_DIR}")
    print()
    
    # Handle different modes
    try:
        if args.init:
            # Initialize directories only
            logger.info("Initializing Pi Player directories...")
            result = init_directories()
            print(f"✅ Initialized {result['total']} directories")
            return 0
        
        elif args.status:
            # Show status and exit
            logger.info("Getting Pi Player status...")
            cache_status = get_cache_status()
            
            print("📊 Pi Player Status:")
            print(f"   Cache Files: {cache_status.get('total_files', 0)}")
            print(f"   Cache Size: {cache_status.get('total_size_mb', 0)} MB")
            print(f"   Cache Dir: {cache_status.get('cache_directory', 'unknown')}")
            print(f"   Playlist File: {'✓' if config.PLAYLIST_FILE.exists() else '❌'}")
            print(f"   Default Assets: {'✓' if (config.BASE_DIR / 'default_assets').exists() else '❌'}")
            
            # Show some recent files
            files = cache_status.get('files', [])
            if files:
                print("\n   Recent Files:")
                for file_info in sorted(files, key=lambda x: x.get('modified', 0), reverse=True)[:5]:
                    size_mb = file_info.get('size', 0) / (1024*1024)
                    print(f"     • {file_info.get('filename', 'unknown')} ({size_mb:.1f} MB)")
            
            return 0
        
        elif args.reset_cache:
            # Reset cache and download fresh
            logger.info("Resetting cache and downloading fresh...")
            
            if not reset_cache():
                print("❌ Cache reset failed")
                return 1
            
            print("✅ Cache reset complete")
            
            if not run_download_sync():
                print("❌ Fresh download failed")
                return 1
            
            print("✅ Fresh download complete")
            return 0
        
        elif args.download:
            # Download only
            logger.info("Running download sync...")
            
            if not run_download_sync():
                print("❌ Download sync failed")
                return 1
            
            print("✅ Download sync complete")
            return 0
        
        elif args.player_only:
            # Player only mode
            return run_player_only()
        
        else:
            # Full system mode (default)
            return run_full_system()
    
    except KeyboardInterrupt:
        logger.info("Pi Player interrupted by user")
        print("\n👋 Pi Player stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Pi Player failed with unexpected error: {e}", exc_info=True)
        print(f"\n❌ Pi Player failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())