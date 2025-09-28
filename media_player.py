#!/usr/bin/env python3
"""
Media Player Daemon for Pi Player
Continuously plays cached media files based on playlist
"""

import json
import logging
import os
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import config

# Setup logging
logger = logging.getLogger("media_player")
logger.setLevel(getattr(logging, config.LOG_LEVEL))

if not logger.handlers:
    fh = logging.FileHandler(config.get_log_path("media_player"))
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)


class MediaPlayer:
    """Manages media playback loop"""
    
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self.playlist: List[Dict] = []
        self.current_index = 0
        self.should_stop = False
        self.playlist_version = None
        self.loop_enabled = True
        self.showing_default_screen = False
        self.no_playlist_since = None
        
        # Thread for watching playlist changes
        self.watcher_thread = None
        self.player_thread = None
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
    def update_playback_state(self, status: str, current_item: str = None):
        """Update playback state file"""
        try:
            state = {
                "status": status,
                "current_item": current_item,
                "playlist_position": self.current_index,
                "playlist_version": self.playlist_version,
                "playlist_total": len(self.playlist),
                "last_updated": datetime.now().isoformat()
            }
            with open(config.PLAYBACK_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update playback state: {e}")
    
    def load_playlist(self) -> bool:
        """Load playlist from disk and check if it changed"""
        try:
            if not config.PLAYLIST_FILE.exists():
                logger.info("No playlist file found")
                return False
            
            with open(config.PLAYLIST_FILE, 'r') as f:
                data = json.load(f)
            
            new_version = data.get("version", "unknown")
            
            # Check if playlist changed
            if new_version != self.playlist_version:
                with self.lock:
                    self.playlist = data.get("items", [])
                    self.playlist_version = new_version
                    self.loop_enabled = data.get("loop", True)
                    self.current_index = 0  # Reset to beginning
                    # Reset no playlist tracking when we get content
                    if self.playlist:
                        self.no_playlist_since = None
                        if self.showing_default_screen:
                            self.showing_default_screen = False
                
                logger.info(f"Loaded playlist v{new_version} with {len(self.playlist)} items")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load playlist: {e}")
            return False
    
    def stop_current_player(self):
        """Stop current media player process"""
        if self.current_process and self.current_process.poll() is None:
            try:
                logger.info(f"Stopping process {self.current_process.pid}")
                self.current_process.terminate()
                
                # Give it a moment to terminate gracefully
                time.sleep(2)
                
                if self.current_process.poll() is None:
                    logger.warning("Process didn't terminate, killing it")
                    self.current_process.kill()
                
                self.current_process.wait(timeout=5)
                logger.info("Process stopped successfully")
                
            except Exception as e:
                logger.error(f"Failed to stop player process: {e}")
            finally:
                self.current_process = None
    
    def create_default_screen_if_needed(self):
        """Create default screen image if it doesn't exist"""
        default_path = config.DEFAULT_SCREEN_PATH
        
        if not default_path.exists():
            try:
                # Create default assets directory
                default_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Try to create a simple default image using PIL
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    
                    # Create a simple branded image
                    width, height = 1920, 1080
                    image = Image.new('RGB', (width, height), color='#1a1a2e')
                    draw = ImageDraw.Draw(image)
                    
                    # Add text
                    try:
                        font = ImageFont.load_default()
                        text = "Pi Player - Ready for Content"
                        text_bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_x = (width - text_width) // 2
                        text_y = height // 2
                        draw.text((text_x, text_y), text, fill='white', font=font)
                    except:
                        # Fallback without font
                        draw.rectangle([(width//4, height//2-50), (3*width//4, height//2+50)], fill='#333366')
                    
                    image.save(str(default_path), 'PNG')
                    logger.info(f"Created default screen image at {default_path}")
                    
                except ImportError:
                    # PIL not available, create a simple text file that feh can't display
                    # This will cause feh to show an error, which is better than nothing
                    default_path.write_text("Pi Player - Default Screen\nWaiting for playlist...")
                    logger.warning("PIL not available, created text placeholder")
                    
            except Exception as e:
                logger.error(f"Failed to create default screen: {e}")
    
    def show_default_screen(self):
        """Display the default screen"""
        if not config.SHOW_DEFAULT_SCREEN:
            return False
            
        self.create_default_screen_if_needed()
        
        if not config.DEFAULT_SCREEN_PATH.exists():
            logger.warning("Default screen image not available")
            return False
        
        try:
            # Use feh to display the default screen
            cmd = [
                "feh",
                "--fullscreen",
                "--hide-pointer",
                "--quiet",
                "--no-menus",
                str(config.DEFAULT_SCREEN_PATH)
            ]
            
            logger.info("Showing default screen")
            self.update_playback_state("showing_default", "Default Screen")
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            self.showing_default_screen = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to show default screen: {e}")
            return False
    
    def get_player_command(self, media_path: Path, item: Dict) -> List[str]:
        """Get the appropriate player command for media type"""
        filename = media_path.name
        
        if config.is_video_file(filename) or config.is_audio_file(filename):
            # Use VLC for video and audio
            cmd = [
                "cvlc",
                "--intf", "dummy",  # No GUI
                "--quiet",
                "--no-video-title-show",
                "--fullscreen",
                "--no-osd",
                str(media_path)
            ]
            
            # Add duration for video files if specified
            duration = item.get("duration")
            if duration and isinstance(duration, (int, float)) and duration > 0:
                cmd.extend(["--run-time", str(int(duration))])
            
            return cmd
            
        elif config.is_image_file(filename):
            # Use feh for images
            duration = item.get("duration", config.IMAGE_DISPLAY_DURATION)
            return [
                "feh",
                "--fullscreen",
                "--hide-pointer",
                "--quiet",
                "--slideshow-delay", str(duration),
                str(media_path)
            ]
        
        else:
            logger.warning(f"Unknown media type for {filename}, trying VLC")
            return ["cvlc", "--intf", "dummy", "--quiet", str(media_path)]
    
    def play_media_item(self, item: Dict) -> bool:
        """Play a single media item"""
        filename = item.get("filename")
        if not filename:
            logger.error("Item missing filename")
            return False
        
        media_path = config.get_media_path(filename)
        if not media_path.exists():
            logger.error(f"Media file not found: {media_path}")
            return False
        
        try:
            cmd = self.get_player_command(media_path, item)
            logger.info(f"Playing: {filename} with command: {' '.join(cmd[:3])}...")
            
            self.update_playback_state("playing", filename)
            
            # Start the player process
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create process group for easier killing
            )
            
            # Wait for process to complete
            return_code = self.current_process.wait()
            
            if return_code == 0:
                logger.info(f"Finished playing: {filename}")
                return True
            else:
                logger.warning(f"Player process ended with code {return_code} for {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to play {filename}: {e}")
            return False
        finally:
            self.current_process = None
    
    def playback_loop(self):
        """Main playback loop"""
        logger.info("Starting playback loop")
        
        while not self.should_stop:
            try:
                # Load/reload playlist if needed
                if self.load_playlist():
                    logger.info("Playlist updated, restarting playback")
                    self.stop_current_player()
                
                # Check if we have a playlist
                if not self.playlist:
                    # Track when we first noticed no playlist
                    if self.no_playlist_since is None:
                        self.no_playlist_since = time.time()
                        logger.info("No playlist items, waiting...")
                        self.update_playback_state("waiting", "No playlist")
                    
                    # Show default screen after timeout
                    elif (time.time() - self.no_playlist_since >= config.DEFAULT_SCREEN_TIMEOUT and 
                          not self.showing_default_screen):
                        logger.info("No playlist for extended period, showing default screen")
                        if self.show_default_screen():
                            # Keep default screen running until playlist arrives
                            while not self.playlist and not self.should_stop:
                                if self.load_playlist():  # Check for new playlist
                                    break
                                time.sleep(config.PLAYER_CHECK_INTERVAL)
                            # Stop default screen when playlist becomes available
                            self.stop_current_player()
                            self.showing_default_screen = False
                        else:
                            # Fallback if default screen fails
                            time.sleep(config.PLAYER_CHECK_INTERVAL * 5)
                    else:
                        time.sleep(config.PLAYER_CHECK_INTERVAL * 2)
                    
                    continue
                
                # Get current item
                with self.lock:
                    if self.current_index >= len(self.playlist):
                        if self.loop_enabled:
                            self.current_index = 0
                            logger.info("Playlist finished, looping back to start")
                        else:
                            logger.info("Playlist finished, stopping (loop disabled)")
                            self.update_playback_state("finished", "Playlist complete")
                            time.sleep(config.PLAYER_CHECK_INTERVAL * 10)
                            continue
                    
                    current_item = self.playlist[self.current_index]
                
                # Play the current item
                logger.info(f"Playing item {self.current_index + 1}/{len(self.playlist)}: {current_item.get('filename')}")
                success = self.play_media_item(current_item)
                
                # Move to next item
                with self.lock:
                    self.current_index += 1
                
                # Brief pause between items
                if not self.should_stop:
                    time.sleep(config.PLAYER_CHECK_INTERVAL)
                
            except Exception as e:
                logger.exception(f"Error in playback loop: {e}")
                self.update_playback_state("error", f"Playback error: {str(e)}")
                time.sleep(config.PLAYER_CHECK_INTERVAL * 5)
        
        logger.info("Playback loop stopped")
        self.update_playback_state("stopped", "Player daemon stopped")
    
    def start(self):
        """Start the media player daemon"""
        logger.info("Starting media player daemon")
        
        # Start playback thread
        self.player_thread = threading.Thread(target=self.playback_loop, daemon=True)
        self.player_thread.start()
        
        # Signal handling
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # Keep main thread alive
            while not self.should_stop:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        self.stop()
    
    def stop(self):
        """Stop the media player daemon"""
        logger.info("Stopping media player daemon")
        
        self.should_stop = True
        self.stop_current_player()
        
        # Wait for threads to finish
        if self.player_thread and self.player_thread.is_alive():
            self.player_thread.join(timeout=5)
        
        self.update_playback_state("stopped", "Player daemon stopped")
        logger.info("Media player daemon stopped")
    
    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}")
        self.stop()


def main():
    """Main entry point"""
    try:
        # Initialize player
        player = MediaPlayer()
        
        # Initial state
        player.update_playback_state("starting", "Media player daemon starting")
        
        # Start the daemon
        player.start()
        
    except Exception as e:
        logger.exception(f"Media player daemon failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    
    # Enable development mode if running directly
    if len(sys.argv) > 1 and sys.argv[1] == "--dev":
        os.environ["PI_PLAYER_DEV"] = "true"
        
        # Reload config
        import importlib
        import config as config_module
        importlib.reload(config_module)
        from config import config
    
    sys.exit(main())