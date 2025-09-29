#!/usr/bin/env python3
"""
Pi Player Monitoring CLI
Real-time monitoring of downloads, cache status, and playback
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from log_setup import setup_logging
from config import config
from download_manager import get_cache_status, progress

# Setup logging for monitor
logger = setup_logging("monitor", log_level="INFO")

class PiPlayerMonitor:
    """Real-time monitor for Pi Player status"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.last_update = None
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get basic system statistics"""
        try:
            # Get CPU usage
            cpu_usage = self._get_cpu_usage()
            
            # Get memory usage
            memory_info = self._get_memory_info()
            
            # Get disk usage for cache directory
            disk_info = self._get_disk_usage()
            
            # Get temperature (if available)
            temp = self._get_temperature()
            
            return {
                "cpu_usage_percent": cpu_usage,
                "memory": memory_info,
                "disk": disk_info,
                "temperature_c": temp,
                "uptime": str(datetime.now() - self.start_time).split('.')[0]
            }
        except Exception as e:
            logger.debug(f"Failed to get system stats: {e}")
            return {"error": "Could not get system stats"}
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'Cpu(s):' in line:
                    # Parse line like: "%Cpu(s):  2.3 us,  0.7 sy,  0.0 ni, 96.7 id,  0.3 wa,  0.0 hi,  0.0 si,  0.0 st"
                    idle = float(line.split(',')[3].split()[0])
                    return round(100 - idle, 1)
        except:
            pass
        return 0.0
    
    def _get_memory_info(self) -> Dict[str, int]:
        """Get memory usage info"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    key, value = line.split(':')
                    meminfo[key.strip()] = int(value.split()[0])
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', 0)
                used = total - available
                
                return {
                    "total_kb": total,
                    "used_kb": used,
                    "available_kb": available,
                    "used_percent": round((used / total) * 100, 1) if total > 0 else 0
                }
        except:
            return {"error": "Could not read memory info"}
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage for cache directory"""
        try:
            stat = os.statvfs(config.MEDIA_CACHE_DIR)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_avail * stat.f_frsize
            used = total - free
            
            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "used_percent": round((used / total) * 100, 1) if total > 0 else 0
            }
        except:
            return {"error": "Could not get disk usage"}
    
    def _get_temperature(self) -> Optional[float]:
        """Get system temperature if available"""
        try:
            if Path(config.TEMPERATURE_SENSOR_PATH).exists():
                with open(config.TEMPERATURE_SENSOR_PATH, 'r') as f:
                    temp_raw = int(f.read().strip())
                    return round(temp_raw / 1000.0, 1)
        except:
            pass
        return None
    
    def get_playlist_status(self) -> Dict[str, Any]:
        """Get current playlist status"""
        try:
            if not config.PLAYLIST_FILE.exists():
                return {"error": "No active playlist"}
                
            with open(config.PLAYLIST_FILE, 'r') as f:
                playlist = json.load(f)
                
            return {
                "version": playlist.get("version", "unknown"),
                "description": playlist.get("description", ""),
                "total_items": len(playlist.get("items", [])),
                "loop_enabled": playlist.get("loop", False),
                "last_updated": playlist.get("last_updated", "unknown")
            }
        except Exception as e:
            return {"error": f"Could not read playlist: {e}"}
    
    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        try:
            if not config.PLAYBACK_STATE_FILE.exists():
                return {"status": "unknown", "reason": "no state file"}
                
            with open(config.PLAYBACK_STATE_FILE, 'r') as f:
                state = json.load(f)
                
            return state
        except Exception as e:
            return {"error": f"Could not read playback state: {e}"}
    
    def get_log_tail(self, component: str = "download_manager", lines: int = 10) -> List[str]:
        """Get recent log entries"""
        try:
            log_file = config.get_log_path(component)
            if not log_file.exists():
                return [f"No log file found: {log_file}"]
                
            result = subprocess.run(['tail', f'-n{lines}', str(log_file)], 
                                  capture_output=True, text=True, timeout=5)
            
            log_entries = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        # Parse JSON log entry
                        entry = json.loads(line)
                        timestamp = entry.get('timestamp', '').split('T')[1].split('.')[0]
                        level = entry.get('level', 'INFO')
                        message = entry.get('message', '')
                        log_entries.append(f"[{timestamp}] {level}: {message}")
                    except json.JSONDecodeError:
                        # Fall back to raw line if not JSON
                        log_entries.append(line.strip())
                        
            return log_entries or ["No recent log entries"]
            
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def display_status(self, clear_screen: bool = True):
        """Display comprehensive status information"""
        
        if clear_screen:
            os.system('clear')
        
        print("🎬 Pi Player Real-Time Monitor")
        print("=" * 80)
        print(f"⏰ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Monitor Uptime: {str(datetime.now() - self.start_time).split('.')[0]}")
        print()
        
        # System Stats
        print("🖥️  System Status:")
        sys_stats = self.get_system_stats()
        if "error" not in sys_stats:
            print(f"   CPU Usage: {sys_stats.get('cpu_usage_percent', 0)}%")
            mem = sys_stats.get('memory', {})
            print(f"   Memory: {mem.get('used_percent', 0)}% used ({mem.get('used_kb', 0)//1024} MB / {mem.get('total_kb', 0)//1024} MB)")
            disk = sys_stats.get('disk', {})
            print(f"   Cache Disk: {disk.get('used_percent', 0)}% used ({disk.get('free_bytes', 0)//1024//1024//1024} GB free)")
            if sys_stats.get('temperature_c'):
                print(f"   Temperature: {sys_stats['temperature_c']}°C")
        else:
            print(f"   {sys_stats.get('error', 'Unknown error')}")
        print()
        
        # Cache Status
        print("📦 Media Cache Status:")
        cache_status = get_cache_status()
        if "error" not in cache_status:
            print(f"   Total Files: {cache_status.get('total_files', 0)}")
            print(f"   Total Size: {cache_status.get('total_size_mb', 0)} MB")
            print(f"   Directory: {cache_status.get('cache_directory', 'unknown')}")
            
            # Show recent files
            files = cache_status.get('files', [])
            if files:
                print("   Recent Files:")
                for file_info in sorted(files, key=lambda x: x.get('modified', 0), reverse=True)[:5]:
                    size_mb = round(file_info.get('size', 0) / (1024*1024), 1)
                    mod_time = datetime.fromtimestamp(file_info.get('modified', 0)).strftime('%H:%M:%S')
                    print(f"     • {file_info.get('filename', 'unknown')} ({size_mb} MB, modified {mod_time})")
        else:
            print(f"   Error: {cache_status.get('error', 'Unknown error')}")
        print()
        
        # Playlist Status
        print("🎵 Playlist Status:")
        playlist_status = self.get_playlist_status()
        if "error" not in playlist_status:
            print(f"   Version: {playlist_status.get('version', 'unknown')}")
            print(f"   Items: {playlist_status.get('total_items', 0)}")
            print(f"   Loop: {playlist_status.get('loop_enabled', False)}")
            print(f"   Description: {playlist_status.get('description', 'N/A')}")
        else:
            print(f"   Error: {playlist_status.get('error', 'No playlist loaded')}")
        print()
        
        # Playback Status
        print("▶️  Playback Status:")
        playback_status = self.get_playback_status()
        if "error" not in playback_status:
            print(f"   Status: {playback_status.get('status', 'unknown')}")
            print(f"   Current Item: {playback_status.get('current_item', 'none')}")
            print(f"   Position: {playback_status.get('playlist_position', 0)} / {playback_status.get('playlist_total', 0)}")
            if playback_status.get('last_updated'):
                last_update = playback_status['last_updated'].split('T')
                print(f"   Last Updated: {last_update[1].split('.')[0] if len(last_update) > 1 else last_update[0]}")
        else:
            print(f"   Error: {playback_status.get('error', 'No playback state')}")
        print()
        
        # Download Progress
        print("⬇️  Download Progress:")
        download_progress = progress.get_status()
        if download_progress:
            active_downloads = {k: v for k, v in download_progress.items() if v.get('status') == 'downloading'}
            if active_downloads:
                for filename, info in active_downloads.items():
                    progress_pct = 0
                    if info.get('total_bytes', 0) > 0:
                        progress_pct = (info.get('downloaded_bytes', 0) / info['total_bytes']) * 100
                    speed_mb = info.get('speed', 0) / (1024*1024)
                    print(f"   • {filename}: {progress_pct:.1f}% ({speed_mb:.1f} MB/s)")
            else:
                print("   No active downloads")
        else:
            print("   No download activity")
        print()
        
        # Recent Logs
        print("📋 Recent Activity (last 5 entries):")
        recent_logs = self.get_log_tail("download_manager", 5)
        for log_entry in recent_logs[-5:]:
            print(f"   {log_entry}")
        print()
        
        print("Press Ctrl+C to exit")

def main():
    """Main monitoring function"""
    monitor = PiPlayerMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            # Show status once and exit
            monitor.display_status(clear_screen=False)
            return
        elif sys.argv[1] == "--logs":
            # Show recent logs and exit
            component = sys.argv[2] if len(sys.argv) > 2 else "download_manager"
            logs = monitor.get_log_tail(component, 20)
            for log_entry in logs:
                print(log_entry)
            return
        elif sys.argv[1] == "--cache":
            # Show cache status and exit
            cache_status = get_cache_status()
            print(json.dumps(cache_status, indent=2))
            return
        elif sys.argv[1] == "--help":
            print("Pi Player Monitor")
            print("Usage: monitor.py [options]")
            print("  --once     Show status once and exit")
            print("  --logs     Show recent log entries")
            print("  --cache    Show cache status as JSON")
            print("  --help     Show this help")
            print("  (no args) Start real-time monitoring")
            return
    
    # Real-time monitoring
    print("Starting Pi Player real-time monitor...")
    print("Press Ctrl+C to exit")
    time.sleep(2)
    
    try:
        while True:
            monitor.display_status()
            time.sleep(5)  # Update every 5 seconds
            
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")
        logger.info("Monitor stopped by user")

if __name__ == "__main__":
    main()