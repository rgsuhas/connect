#!/usr/bin/env python3
"""
Pi Player Telemetry Collector
Gathers system health and playback status information
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import psutil

from config import config


class TelemetryCollector:
    """Collects system telemetry and playback status"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.boot_time = psutil.boot_time()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for telemetry collector"""
        logger = logging.getLogger("telemetry")
        logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        if not logger.handlers:
            handler = logging.FileHandler(config.get_log_path("telemetry"))
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system performance statistics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage(str(config.BASE_DIR))
            
            # Network stats (summarized)
            network = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "total_mb": round(memory.total / 1024 / 1024, 2),
                    "available_mb": round(memory.available / 1024 / 1024, 2),
                    "used_mb": round(memory.used / 1024 / 1024, 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                    "percent": round((disk.used / disk.total) * 100, 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}
    
    def get_temperature(self) -> Optional[float]:
        """Get system temperature in Celsius"""
        try:
            # Try Pi-specific temperature sensor first
            temp_path = Path(config.TEMPERATURE_SENSOR_PATH)
            if temp_path.exists():
                temp_raw = temp_path.read_text().strip()
                return round(int(temp_raw) / 1000.0, 1)
            
            # Fallback to psutil sensors (if available)
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            return round(entry.current, 1)
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting temperature: {e}")
            return None
    
    def get_uptime_stats(self) -> Dict[str, Any]:
        """Get system uptime information"""
        try:
            current_time = time.time()
            uptime_seconds = current_time - self.boot_time
            
            return {
                "boot_time": datetime.fromtimestamp(self.boot_time).isoformat(),
                "uptime_seconds": int(uptime_seconds),
                "uptime_hours": round(uptime_seconds / 3600, 2),
                "current_time": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting uptime stats: {e}")
            return {}
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get information about player-related processes"""
        try:
            player_procs = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    if any(player_name in proc.info['name'] for player_name in config.PLAYER_PROCESSES):
                        player_procs.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cpu_percent": proc.info['cpu_percent'],
                            "memory_percent": round(proc.info['memory_percent'], 2),
                            "cmdline": ' '.join(proc.info['cmdline'][:3])  # First 3 args only
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return player_procs
        except Exception as e:
            self.logger.error(f"Error getting running processes: {e}")
            return []
    
    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status from state file"""
        try:
            if config.PLAYBACK_STATE_FILE.exists():
                with open(config.PLAYBACK_STATE_FILE, 'r') as f:
                    return json.load(f)
            else:
                return {
                    "status": "unknown",
                    "current_item": None,
                    "playlist_position": 0,
                    "last_updated": None
                }
        except Exception as e:
            self.logger.error(f"Error getting playback status: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_media_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached media files"""
        try:
            cache_dir = config.MEDIA_CACHE_DIR
            if not cache_dir.exists():
                return {"total_files": 0, "total_size_mb": 0}
            
            total_files = 0
            total_size = 0
            
            for file_path in cache_dir.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "cache_path": str(cache_dir)
            }
        except Exception as e:
            self.logger.error(f"Error getting media cache stats: {e}")
            return {"error": str(e)}
    
    def get_playlist_info(self) -> Dict[str, Any]:
        """Get current playlist information"""
        try:
            if config.PLAYLIST_FILE.exists():
                with open(config.PLAYLIST_FILE, 'r') as f:
                    playlist = json.load(f)
                    return {
                        "version": playlist.get("version", "unknown"),
                        "total_items": len(playlist.get("items", [])),
                        "last_updated": playlist.get("last_updated"),
                        "loop_enabled": playlist.get("loop", False)
                    }
            else:
                return {"status": "no_playlist"}
        except Exception as e:
            self.logger.error(f"Error getting playlist info: {e}")
            return {"error": str(e)}
    
    def get_full_telemetry(self) -> Dict[str, Any]:
        """Get complete telemetry data"""
        try:
            telemetry = {
                "timestamp": datetime.now().isoformat(),
                "system": self.get_system_stats(),
                "temperature_celsius": self.get_temperature(),
                "uptime": self.get_uptime_stats(),
                "processes": self.get_running_processes(),
                "playback": self.get_playback_status(),
                "media_cache": self.get_media_cache_stats(),
                "playlist": self.get_playlist_info()
            }
            
            return telemetry
        except Exception as e:
            self.logger.error(f"Error collecting full telemetry: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


# Global telemetry collector instance
telemetry_collector = TelemetryCollector()


def get_stats() -> Dict[str, Any]:
    """Public interface to get telemetry stats"""
    return telemetry_collector.get_full_telemetry()


if __name__ == "__main__":
    # Test telemetry collection
    import pprint
    
    print("Pi Player Telemetry Test")
    print("=" * 50)
    
    stats = get_stats()
    pprint.pprint(stats, width=80)