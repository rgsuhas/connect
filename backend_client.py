#!/usr/bin/env python3
"""
Backend Client for Pi Player
Handles communication with backend API for heartbeat, telemetry, and playlist management
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import config
from logger_setup import get_component_logger

logger = get_component_logger("backend_client", console=False)


class BackendClient:
    """Client for backend API communication"""
    
    def __init__(self):
        self.base_url = config.BACKEND_BASE_URL
        self.api_key = config.BACKEND_API_KEY
        self.device_id = config.DEVICE_ID
        self.hardware_id = config.HARDWARE_ID
        self.session = self._create_session()
        
        # Tracking variables
        self.boot_time = time.time()
        self.last_heartbeat = None
        self.last_telemetry = None
        self.errors = []
        
        # Threading for periodic tasks
        self.heartbeat_thread = None
        self.telemetry_thread = None
        self.playlist_thread = None
        self.should_stop = False
        
        # Playlist management
        self.last_playlist_fetch = None
        self.last_playlist_version = None
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retries and proper headers"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=config.HEARTBEAT_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'User-Agent': f'Pi-Player/{config.API_VERSION}'
        })
        
        return session
    
    def _get_uptime_seconds(self) -> int:
        """Get system uptime in seconds"""
        return int(time.time() - self.boot_time)
    
    def _add_error(self, error_msg: str):
        """Add error to error list with timestamp"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": error_msg
        }
        
        # Keep only last 10 errors
        self.errors.append(error_entry)
        if len(self.errors) > 10:
            self.errors = self.errors[-10:]
        
        logger.error(f"Backend error: {error_msg}")
    
    def send_heartbeat(self, last_ad_playback_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Send heartbeat to backend
        
        Expected format:
        {
            "device_id": "CTRL-TRUCK-001",
            "status": "online",
            "uptime_seconds": 1860,
            "last_ad_playback_timestamp": "2025-09-29T06:35:40.000Z"
        }
        """
        if not config.BACKEND_ENABLED:
            return {"status": "disabled", "message": "Backend integration disabled"}
        
        try:
            # Prepare heartbeat data
            heartbeat_data = {
                "device_id": self.device_id,
                "status": "online",
                "uptime_seconds": self._get_uptime_seconds()
            }
            
            # Add last playback timestamp if provided
            if last_ad_playback_timestamp:
                heartbeat_data["last_ad_playback_timestamp"] = last_ad_playback_timestamp
            
            # Construct URL
            url = f"{self.base_url}/api/hardware/{self.hardware_id}/heartbeat"
            
            logger.debug(f"Sending heartbeat to {url}")
            logger.debug(f"Heartbeat data: {heartbeat_data}")
            
            # Send request
            response = self.session.post(
                url,
                json=heartbeat_data,
                timeout=config.HEARTBEAT_TIMEOUT
            )
            
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            self.last_heartbeat = datetime.now().isoformat()
            
            logger.info(f"Heartbeat sent successfully: {response_data.get('status', 'unknown')}")
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Heartbeat request failed: {str(e)}"
            self._add_error(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Heartbeat unexpected error: {str(e)}"
            self._add_error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def get_playlist_from_backend(self) -> Optional[Dict[str, Any]]:
        """
        Fetch playlist from backend API
        
        Expected backend response format:
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
        """
        if not config.BACKEND_ENABLED:
            logger.debug("Backend integration disabled, no playlist fetch")
            return None
        
        try:
            # Construct playlist URL
            url = f"{self.base_url}/api/hardware/{self.hardware_id}/playlist"
            
            logger.debug(f"Fetching playlist from {url}")
            
            # Send request
            response = self.session.get(
                url,
                timeout=config.HEARTBEAT_TIMEOUT  # Reuse heartbeat timeout
            )
            
            # Handle 404 as "no playlist available" rather than error
            if response.status_code == 404:
                logger.info("No playlist available from backend (404)")
                return None
            
            response.raise_for_status()
            
            # Parse response
            playlist_data = response.json()
            
            logger.info(f"Received playlist from backend: version {playlist_data.get('version', 'unknown')}")
            return playlist_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Playlist fetch failed: {str(e)}"
            logger.warning(error_msg)  # Warning instead of error since this is optional
            return None
        except Exception as e:
            error_msg = f"Playlist fetch unexpected error: {str(e)}"
            logger.warning(error_msg)
            return None
    
    def send_telemetry(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send telemetry data to backend
        
        Expected backend response format:
        {
            "timestamp": "2025-09-29T16:24:54.707Z",
            "device": {
                "id": "TRUCK_001",
                "uptime_sec": 1860,
                "status": "online",
                "last_heartbeat": "2025-09-29T16:22:46.319Z"
            },
            "player": {
                "status": "ready",
                "playlist_version": "v0",
                "last_ad_playback": "2025-09-29T06:35:40.000Z"
            },
            "errors": []
        }
        """
        if not config.BACKEND_ENABLED:
            return {"status": "disabled", "message": "Backend integration disabled"}
        
        try:
            # Transform our telemetry to backend format
            backend_telemetry = self._transform_telemetry_for_backend(telemetry_data)
            
            # Construct URL
            url = f"{self.base_url}/api/hardware/{self.hardware_id}/telemetry"
            
            logger.debug(f"Sending telemetry to {url}")
            
            # Send request
            response = self.session.post(
                url,
                json=backend_telemetry,
                timeout=config.TELEMETRY_TIMEOUT
            )
            
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            self.last_telemetry = datetime.now().isoformat()
            
            logger.info("Telemetry sent successfully")
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Telemetry request failed: {str(e)}"
            self._add_error(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Telemetry unexpected error: {str(e)}"
            self._add_error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def _transform_telemetry_for_backend(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Pi Player telemetry to backend format"""
        
        # Extract playback info
        playback_info = telemetry_data.get("playback", {})
        playlist_info = telemetry_data.get("playlist", {})
        
        # Determine player status
        playback_status = playback_info.get("status", "unknown")
        if playback_status in ["playing", "showing_default"]:
            player_status = "ready"
        elif playback_status == "waiting":
            player_status = "waiting"
        else:
            player_status = "offline"
        
        # Get playlist version
        playlist_version = playlist_info.get("version", "v0")
        
        # Format for backend
        backend_data = {
            "timestamp": datetime.now().isoformat(),
            "device": {
                "id": self.device_id,
                "uptime_sec": self._get_uptime_seconds(),
                "status": "online",
                "last_heartbeat": self.last_heartbeat or datetime.now().isoformat()
            },
            "player": {
                "status": player_status,
                "playlist_version": playlist_version,
                "last_ad_playback": self._get_last_playback_timestamp(playback_info)
            },
            "errors": [error["message"] for error in self.errors[-5:]]  # Last 5 errors
        }
        
        # Add system info if available
        if "system" in telemetry_data:
            system_info = telemetry_data["system"]
            backend_data["system"] = {
                "cpu_percent": system_info.get("cpu", {}).get("percent", 0),
                "memory_percent": system_info.get("memory", {}).get("percent", 0),
                "disk_percent": system_info.get("disk", {}).get("percent", 0),
                "temperature_celsius": telemetry_data.get("temperature_celsius", 0)
            }
        
        return backend_data
    
    def _get_last_playback_timestamp(self, playback_info: Dict[str, Any]) -> Optional[str]:
        """Get last playback timestamp in ISO format"""
        
        # Try to get from playback state
        last_updated = playback_info.get("last_updated")
        if last_updated and playback_info.get("status") == "playing":
            return last_updated
        
        # Default to current time if actively playing
        if playback_info.get("current_item"):
            return datetime.now().isoformat()
        
        return None
    
    def get_backend_status(self) -> Dict[str, Any]:
        """Get current backend integration status"""
        return {
            "enabled": config.BACKEND_ENABLED,
            "backend_url": self.base_url,
            "device_id": self.device_id,
            "hardware_id": self.hardware_id,
            "last_heartbeat": self.last_heartbeat,
            "last_telemetry": self.last_telemetry,
            "uptime_seconds": self._get_uptime_seconds(),
            "error_count": len(self.errors),
            "recent_errors": self.errors[-3:] if self.errors else []
        }
    
    def start_periodic_tasks(self):
        """Start periodic heartbeat and telemetry reporting"""
        if not config.BACKEND_ENABLED:
            logger.info("Backend integration disabled, skipping periodic tasks")
            return
        
        logger.info("Starting periodic backend tasks")
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            daemon=True,
            name="BackendHeartbeat"
        )
        self.heartbeat_thread.start()
        
        # Start telemetry thread
        self.telemetry_thread = threading.Thread(
            target=self._telemetry_worker,
            daemon=True,
            name="BackendTelemetry"
        )
        self.telemetry_thread.start()
        
        # Start playlist fetching thread
        self.playlist_thread = threading.Thread(
            target=self._playlist_worker,
            daemon=True,
            name="BackendPlaylist"
        )
        self.playlist_thread.start()
        
        logger.info("Backend periodic tasks started")
    
    def _heartbeat_worker(self):
        """Worker thread for periodic heartbeat"""
        while not self.should_stop:
            try:
                # Get last playback timestamp from playback state
                last_playback = self._get_current_playback_timestamp()
                self.send_heartbeat(last_playback)
                
                # Wait for next heartbeat
                time.sleep(config.HEARTBEAT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Heartbeat worker error: {e}")
                time.sleep(config.HEARTBEAT_INTERVAL)
    
    def _telemetry_worker(self):
        """Worker thread for periodic telemetry"""
        while not self.should_stop:
            try:
                # Get current telemetry from telemetry module
                from telemetry import get_stats
                telemetry_data = get_stats()
                self.send_telemetry(telemetry_data)
                
                # Wait for next telemetry report
                time.sleep(config.TELEMETRY_REPORT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Telemetry worker error: {e}")
                time.sleep(config.TELEMETRY_REPORT_INTERVAL)
    
    def _playlist_worker(self):
        """Worker thread for periodic playlist fetching"""
        # Initial delay to allow system to start up
        time.sleep(30)
        
        while not self.should_stop:
            try:
                # Fetch playlist from backend
                playlist_data = self.get_playlist_from_backend()
                
                if playlist_data:
                    # Check if playlist changed
                    new_version = playlist_data.get('version', 'unknown')
                    if new_version != self.last_playlist_version:
                        logger.info(f"New playlist version {new_version} received from backend")
                        self.last_playlist_version = new_version
                        
                        # Send playlist to local API
                        self._update_local_playlist(playlist_data)
                    else:
                        logger.debug(f"Playlist version {new_version} unchanged")
                
                self.last_playlist_fetch = datetime.now().isoformat()
                
                # Wait for next playlist check (default: check every 5 minutes)
                playlist_interval = getattr(config, 'PLAYLIST_FETCH_INTERVAL', 300)
                time.sleep(playlist_interval)
                
            except Exception as e:
                logger.error(f"Playlist worker error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _update_local_playlist(self, playlist_data: Dict[str, Any]):
        """Update local Pi Player playlist via API"""
        try:
            import requests
            
            # Send to local API endpoint
            response = requests.post(
                "http://localhost:8000/playlist",
                json=playlist_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Successfully updated local playlist from backend")
            else:
                logger.warning(f"Failed to update local playlist: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to update local playlist: {e}")
    
    def _get_current_playback_timestamp(self) -> Optional[str]:
        """Get current playback timestamp from state file"""
        try:
            if config.PLAYBACK_STATE_FILE.exists():
                with open(config.PLAYBACK_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    if state.get("status") == "playing":
                        return state.get("last_updated")
            return None
        except Exception as e:
            logger.debug(f"Could not get playback timestamp: {e}")
            return None
    
    def stop_periodic_tasks(self):
        """Stop periodic tasks"""
        logger.info("Stopping backend periodic tasks")
        self.should_stop = True
        
        # Wait for threads to finish
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        
        if self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=5)
            
        if self.playlist_thread and self.playlist_thread.is_alive():
            self.playlist_thread.join(timeout=5)
        
        logger.info("Backend periodic tasks stopped")


# Global backend client instance
backend_client = BackendClient()


def get_backend_client() -> BackendClient:
    """Get the global backend client instance"""
    return backend_client


if __name__ == "__main__":
    # Test backend client
    client = BackendClient()
    
    print("Testing backend client...")
    
    # Test heartbeat
    result = client.send_heartbeat()
    print(f"Heartbeat result: {result}")
    
    # Test telemetry
    from telemetry import get_stats
    telemetry = get_stats()
    result = client.send_telemetry(telemetry)
    print(f"Telemetry result: {result}")
    
    # Show status
    status = client.get_backend_status()
    print(f"Backend status: {json.dumps(status, indent=2)}")