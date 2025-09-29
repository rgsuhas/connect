#!/usr/bin/env python3
"""
Pi Player FastAPI Server
Provides REST API endpoints for playlist management and telemetry
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from config import config
from telemetry import get_stats
from media_downloader import update_cache_for_playlist
from backend_client import get_backend_client
from playlist_manager import get_playlist_manager

# Setup logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger("pi_server")

# Add file handler for server logs
if not logger.handlers:
    fh = logging.FileHandler(config.get_log_path("pi_server"))
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

# FastAPI app instance
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description="Pi Player API for playlist management and system telemetry"
)

# Global state for tracking updates
playlist_update_status = {
    "updating": False,
    "last_update": None,
    "last_error": None
}


def update_playback_state(status: str, current_item: str = None, position: int = 0):
    """Update playback state file for telemetry"""
    try:
        state = {
            "status": status,
            "current_item": current_item,
            "playlist_position": position,
            "last_updated": datetime.now().isoformat()
        }
        with open(config.PLAYBACK_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update playback state: {e}")


def background_download_task(playlist_data: Dict):
    """Background task to download playlist items"""
    global playlist_update_status
    
    try:
        playlist_update_status["updating"] = True
        playlist_update_status["last_error"] = None
        
        # Save playlist to disk
        with open(config.PLAYLIST_FILE, 'w') as f:
            json.dump(playlist_data, f, indent=2)
        
        logger.info(f"Playlist updated with {len(playlist_data.get('items', []))} items")
        
        # Download media files
        download_result = update_cache_for_playlist(config.PLAYLIST_FILE)
        
        # Update status
        playlist_update_status["last_update"] = datetime.now().isoformat()
        
        if "error" in download_result:
            playlist_update_status["last_error"] = download_result["error"]
            logger.error(f"Download failed: {download_result['error']}")
        else:
            logger.info(f"Download completed: {download_result.get('downloaded', 0)} new files")
            
            # Signal media player to restart
            update_playback_state("playlist_updated")
        
    except Exception as e:
        playlist_update_status["last_error"] = str(e)
        logger.exception(f"Background download task failed: {e}")
    finally:
        playlist_update_status["updating"] = False


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/playlist")
async def update_playlist(playlist: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Update the current playlist
    Expected format:
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
    try:
        # Validate playlist structure
        if not isinstance(playlist, dict):
            raise HTTPException(status_code=400, detail="Playlist must be a JSON object")
        
        if "items" not in playlist or not isinstance(playlist["items"], list):
            raise HTTPException(status_code=400, detail="Playlist must contain 'items' list")
        
        # Add metadata if missing
        if "version" not in playlist:
            playlist["version"] = "1.0"
        
        if "last_updated" not in playlist:
            playlist["last_updated"] = datetime.now().isoformat()
        
        if "loop" not in playlist:
            playlist["loop"] = config.PLAYLIST_LOOP
        
        # Validate items
        for i, item in enumerate(playlist["items"]):
            if not isinstance(item, dict):
                raise HTTPException(status_code=400, detail=f"Item {i} must be an object")
            
            if "url" not in item or "filename" not in item:
                raise HTTPException(status_code=400, detail=f"Item {i} missing required 'url' or 'filename'")
        
        # Check if already updating
        if playlist_update_status["updating"]:
            return JSONResponse(
                status_code=409,
                content={"message": "Playlist update already in progress", "status": "updating"}
            )
        
        # Start background download task
        background_tasks.add_task(background_download_task, playlist)
        
        return {
            "message": "Playlist update started",
            "items_count": len(playlist["items"]),
            "version": playlist["version"],
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Playlist update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/playlist")
async def get_playlist():
    """Get the current playlist, creating default if none exists"""
    try:
        # Check if we need to ensure a playlist is available
        playlist_manager = get_playlist_manager()
        
        if not config.PLAYLIST_FILE.exists():
            logger.info("No playlist file exists, attempting to ensure one is available")
            playlist_manager.ensure_playlist_available()
        
        # Try to read playlist
        if config.PLAYLIST_FILE.exists():
            with open(config.PLAYLIST_FILE, 'r') as f:
                playlist_data = json.load(f)
            
            # Get playlist manager status for additional context
            manager_status = playlist_manager.get_playlist_status()
            
            return {
                "playlist": playlist_data,
                "update_status": playlist_update_status,
                "playlist_manager_status": manager_status
            }
        else:
            # Still no playlist after trying to create one
            manager_status = playlist_manager.get_playlist_status()
            return {
                "message": "No playlist could be created",
                "playlist": None,
                "update_status": playlist_update_status,
                "playlist_manager_status": manager_status
            }
        
    except Exception as e:
        logger.exception(f"Failed to get playlist: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read playlist: {str(e)}")


@app.get("/telemetry")
async def get_telemetry():
    """Get system telemetry and health information"""
    try:
        stats = get_stats()
        
        # Add server-specific information
        stats["server"] = {
            "api_version": config.API_VERSION,
            "playlist_update_status": playlist_update_status,
            "config": {
                "api_port": config.API_PORT,
                "media_cache_dir": str(config.MEDIA_CACHE_DIR),
                "playlist_loop": config.PLAYLIST_LOOP,
                "image_display_duration": config.IMAGE_DISPLAY_DURATION
            }
        }
        
        # Add backend integration status
        if config.BACKEND_ENABLED:
            backend_client = get_backend_client()
            stats["backend"] = backend_client.get_backend_status()
        
        return stats
        
    except Exception as e:
        logger.exception(f"Failed to get telemetry: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    }


@app.post("/control/{action}")
async def control_playback(action: str):
    """Control playback actions"""
    valid_actions = ["play", "pause", "stop", "next", "restart"]
    
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")
    
    try:
        # Update playback state to signal media player
        update_playback_state(f"control_{action}")
        
        logger.info(f"Playback control: {action}")
        
        return {
            "message": f"Control action '{action}' executed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Control action failed: {e}")
        raise HTTPException(status_code=500, detail=f"Control action failed: {str(e)}")


@app.post("/backend/heartbeat")
async def backend_heartbeat():
    """Manual heartbeat trigger for backend"""
    try:
        if not config.BACKEND_ENABLED:
            return {"status": "disabled", "message": "Backend integration disabled"}
        
        backend_client = get_backend_client()
        result = backend_client.send_heartbeat()
        
        return result
        
    except Exception as e:
        logger.exception(f"Manual heartbeat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Heartbeat failed: {str(e)}")


@app.post("/backend/telemetry")
async def backend_telemetry_push():
    """Manual telemetry push to backend"""
    try:
        if not config.BACKEND_ENABLED:
            return {"status": "disabled", "message": "Backend integration disabled"}
        
        backend_client = get_backend_client()
        telemetry_data = get_stats()
        result = backend_client.send_telemetry(telemetry_data)
        
        return result
        
    except Exception as e:
        logger.exception(f"Manual telemetry push failed: {e}")
        raise HTTPException(status_code=500, detail=f"Telemetry push failed: {str(e)}")


@app.get("/backend/status")
async def backend_status():
    """Get backend integration status"""
    try:
        backend_client = get_backend_client()
        status = backend_client.get_backend_status()
        
        return status
        
    except Exception as e:
        logger.exception(f"Backend status check failed: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@app.get("/playlist/manager/status")
async def playlist_manager_status():
    """Get playlist manager status"""
    try:
        playlist_manager = get_playlist_manager()
        status = playlist_manager.get_playlist_status()
        
        return status
        
    except Exception as e:
        logger.exception(f"Playlist manager status failed: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@app.post("/playlist/manager/refresh")
async def playlist_manager_refresh():
    """Force playlist refresh from backend or load default"""
    try:
        playlist_manager = get_playlist_manager()
        success = playlist_manager.force_refresh_from_backend()
        
        if success:
            return {
                "message": "Playlist refresh completed",
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
        else:
            return {
                "message": "Playlist refresh failed",
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
        
    except Exception as e:
        logger.exception(f"Playlist manager refresh failed: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@app.post("/playlist/load-default")
async def load_default_playlist(use_cloudinary: bool = True):
    """Manually load default playlist"""
    try:
        playlist_manager = get_playlist_manager()
        success = playlist_manager.load_default_playlist(use_cloudinary=use_cloudinary)
        
        if success:
            return {
                "message": f"Default playlist loaded ({'Cloudinary' if use_cloudinary else 'sample videos'})",
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
        else:
            return {
                "message": "Failed to load default playlist",
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
        
    except Exception as e:
        logger.exception(f"Load default playlist failed: {e}")
        raise HTTPException(status_code=500, detail=f"Load default failed: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Initialize server state on startup"""
    app.state.start_time = time.time()
    
    # Ensure directories exist
    config.MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize playback state
    update_playback_state("server_started")
    
    # Initialize playlist manager
    playlist_manager = get_playlist_manager()
    logger.info("Playlist manager initialized")
    
    # Start backend integration
    if config.BACKEND_ENABLED:
        backend_client = get_backend_client()
        backend_client.start_periodic_tasks()
        logger.info("Backend integration started")
        
        # Give backend a moment to try fetching playlist, then ensure we have a fallback
        def delayed_playlist_check():
            import time
            time.sleep(45)  # Wait 45 seconds for backend to try
            playlist_manager.ensure_playlist_available()
            logger.info("Initial playlist availability check completed")
        
        import threading
        threading.Thread(target=delayed_playlist_check, daemon=True).start()
    else:
        # No backend, immediately ensure we have a default playlist
        playlist_manager.ensure_playlist_available()
        logger.info("Default playlist loaded (no backend enabled)")
    
    logger.info(f"Pi Player API server started on {config.API_HOST}:{config.API_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    # Stop backend integration
    if config.BACKEND_ENABLED:
        backend_client = get_backend_client()
        backend_client.stop_periodic_tasks()
        logger.info("Backend integration stopped")
    
    update_playback_state("server_stopped")
    logger.info("Pi Player API server stopped")


if __name__ == "__main__":
    # For development/testing - in production use systemd service
    import os
    
    # Enable development mode
    os.environ["PI_PLAYER_DEV"] = "true"
    
    # Reload config with dev paths
    import importlib
    import config as config_module
    importlib.reload(config_module)
    from config import config
    
    # Run server
    uvicorn.run(
        "pi_server:app",
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=True
    )