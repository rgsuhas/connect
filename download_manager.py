#!/usr/bin/env python3
"""
Enhanced Download & Cache Manager for Pi Player
Handles downloading, caching, and validation of playlist media with comprehensive logging
"""

import hashlib
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import our logging setup
from log_setup import setup_logging
from config import config

# Global logger
logger = setup_logging("download_manager", log_level="DEBUG")

class ProgressTracker:
    """Track download progress for monitoring"""
    
    def __init__(self):
        self.downloads = {}
        self.lock = threading.Lock()
    
    def start_download(self, filename: str, total_size: int = 0):
        with self.lock:
            self.downloads[filename] = {
                "status": "downloading",
                "total_bytes": total_size,
                "downloaded_bytes": 0,
                "start_time": time.time(),
                "speed": 0,
                "eta": 0
            }
    
    def update_progress(self, filename: str, bytes_downloaded: int):
        with self.lock:
            if filename in self.downloads:
                info = self.downloads[filename]
                info["downloaded_bytes"] = bytes_downloaded
                elapsed = time.time() - info["start_time"]
                if elapsed > 0:
                    info["speed"] = bytes_downloaded / elapsed
                    if info["total_bytes"] > 0 and info["speed"] > 0:
                        remaining = info["total_bytes"] - bytes_downloaded
                        info["eta"] = remaining / info["speed"]
    
    def finish_download(self, filename: str, status: str, error: str = None):
        with self.lock:
            if filename in self.downloads:
                info = self.downloads[filename]
                info["status"] = status
                info["end_time"] = time.time()
                info["duration"] = info["end_time"] - info["start_time"]
                if error:
                    info["error"] = error
    
    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.downloads)

# Global progress tracker
progress = ProgressTracker()

def calculate_checksum(file_path: Path, algorithm: str = "sha256") -> Optional[str]:
    """Calculate file checksum with progress logging"""
    try:
        logger.debug(f"Calculating {algorithm} checksum for {file_path}")
        
        hasher = hashlib.new(algorithm)
        file_size = file_path.stat().st_size
        bytes_read = 0
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
                bytes_read += len(chunk)
                
                # Log progress for large files
                if file_size > 10 * 1024 * 1024:  # > 10MB
                    progress_pct = (bytes_read / file_size) * 100
                    if bytes_read % (1024 * 1024) == 0:  # Every MB
                        logger.debug(f"Checksum progress for {file_path.name}: {progress_pct:.1f}%")
        
        checksum = hasher.hexdigest()
        logger.info(f"Calculated {algorithm} checksum for {file_path.name}", extra={
            "custom_fields": {
                "event_type": "checksum_calculated",
                "filename": file_path.name,
                "algorithm": algorithm,
                "checksum": checksum,
                "file_size": file_size
            }
        })
        
        return checksum
        
    except Exception as e:
        logger.error(f"Failed to calculate checksum for {file_path}: {e}", extra={
            "custom_fields": {
                "event_type": "checksum_error",
                "filename": str(file_path),
                "error": str(e)
            }
        })
        return None

def needs_download(item: Dict) -> Tuple[bool, str, Optional[Path]]:
    """
    Determine if an item needs to be downloaded
    Returns: (needs_download, reason, cached_path)
    """
    filename = item.get("filename")
    url = item.get("url")
    expected_checksum = item.get("checksum")
    
    if not filename:
        return False, "missing filename", None
    
    if not url:
        return False, "missing url", None
    
    # Check in media cache
    cached_path = config.get_media_path(filename)
    
    # Check if file exists in cache
    if not cached_path.exists():
        logger.debug(f"File not in cache: {filename}")
        return True, "not cached", cached_path
    
    # Check file size
    file_size = cached_path.stat().st_size
    if file_size == 0:
        logger.warning(f"Cached file is empty: {filename}")
        return True, "empty file", cached_path
    
    # If checksum is provided, verify it
    if expected_checksum:
        logger.debug(f"Verifying checksum for cached file: {filename}")
        actual_checksum = calculate_checksum(cached_path, config.CHECKSUM_ALGORITHM)
        
        if actual_checksum != expected_checksum:
            logger.warning(f"Checksum mismatch for {filename}: expected {expected_checksum}, got {actual_checksum}")
            return True, "checksum mismatch", cached_path
        
        logger.info(f"Checksum verified for {filename}")
        return False, "checksum valid", cached_path
    
    # If no checksum provided, trust that the file exists and has content
    logger.debug(f"File exists in cache (no checksum verification): {filename} ({file_size} bytes)")
    return False, "exists in cache", cached_path

def create_http_session() -> requests.Session:
    """Create HTTP session with retry strategy"""
    session = requests.Session()
    
    # Configure retry strategy
    try:
        # Try new urllib3 parameter name first
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
    except TypeError:
        # Fall back to old parameter name for older urllib3 versions
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set user agent
    session.headers.update({
        'User-Agent': 'Pi-Player-Download-Manager/1.0'
    })
    
    return session

def download_single_item(item: Dict, session: requests.Session) -> Dict[str, Any]:
    """Download a single playlist item with comprehensive logging"""
    
    filename = item.get("filename", "unknown")
    url = item.get("url")
    expected_checksum = item.get("checksum")
    
    result = {
        "filename": filename,
        "url": url,
        "status": "unknown",
        "reason": "",
        "bytes_downloaded": 0,
        "download_time": 0,
        "cached_path": None
    }
    
    logger.info(f"Processing download request for {filename}")
    
    # Check if download is needed
    needs_dl, reason, cached_path = needs_download(item)
    result["cached_path"] = str(cached_path) if cached_path else None
    
    if not needs_dl:
        result["status"] = "cached"
        result["reason"] = reason
        logger.info(f"Using cached file: {filename} ({reason})")
        return result
    
    if not url:
        result["status"] = "error"
        result["reason"] = "missing url"
        logger.error(f"Cannot download {filename}: missing URL")
        return result
    
    # Ensure cache directory exists
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cached_path.with_suffix(cached_path.suffix + ".tmp")
    
    try:
        logger.info(f"Starting download: {filename} from {url}")
        start_time = time.time()
        
        # Start download with streaming
        response = session.get(url, stream=True, timeout=config.DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        
        # Get content length for progress tracking
        total_size = int(response.headers.get('content-length', 0))
        progress.start_download(filename, total_size)
        
        logger.info(f"Download started for {filename}", extra={
            "custom_fields": {
                "event_type": "download_started",
                "filename": filename,
                "url": url,
                "content_length": total_size,
                "content_type": response.headers.get('content-type', 'unknown')
            }
        })
        
        # Download with progress tracking
        bytes_downloaded = 0
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=64*1024):  # 64KB chunks
                if chunk:
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    progress.update_progress(filename, bytes_downloaded)
                    
                    # Log progress for large files
                    if total_size > 0 and bytes_downloaded % (1024*1024) == 0:  # Every MB
                        progress_pct = (bytes_downloaded / total_size) * 100
                        logger.debug(f"Download progress for {filename}: {progress_pct:.1f}% ({bytes_downloaded}/{total_size})")
        
        download_time = time.time() - start_time
        result["bytes_downloaded"] = bytes_downloaded
        result["download_time"] = download_time
        
        logger.info(f"Download completed for {filename}", extra={
            "custom_fields": {
                "event_type": "download_completed",
                "filename": filename,
                "bytes_downloaded": bytes_downloaded,
                "download_time": download_time,
                "speed_mbps": (bytes_downloaded / (1024*1024)) / download_time if download_time > 0 else 0
            }
        })
        
        # Verify checksum if provided
        if expected_checksum:
            logger.debug(f"Verifying downloaded file checksum: {filename}")
            actual_checksum = calculate_checksum(temp_path, config.CHECKSUM_ALGORITHM)
            
            if actual_checksum != expected_checksum:
                temp_path.unlink(missing_ok=True)
                result["status"] = "error"
                result["reason"] = "checksum verification failed"
                progress.finish_download(filename, "checksum_failed", "checksum verification failed")
                logger.error(f"Checksum verification failed for {filename}: expected {expected_checksum}, got {actual_checksum}")
                return result
            
            logger.info(f"Checksum verified for downloaded file: {filename}")
        
        # Move temp file to final location
        temp_path.replace(cached_path)
        
        result["status"] = "downloaded"
        result["reason"] = "successfully downloaded"
        progress.finish_download(filename, "completed")
        
        logger.info(f"File cached successfully: {filename} -> {cached_path}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        result["status"] = "error"
        result["reason"] = f"network error: {str(e)}"
        progress.finish_download(filename, "network_error", str(e))
        logger.error(f"Network error downloading {filename}: {e}")
        
    except Exception as e:
        result["status"] = "error"
        result["reason"] = f"unexpected error: {str(e)}"
        progress.finish_download(filename, "error", str(e))
        logger.error(f"Unexpected error downloading {filename}: {e}", exc_info=True)
        
    finally:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
    
    return result

def download_playlist_items(playlist_data: Dict, max_workers: int = None) -> Dict[str, Any]:
    """Download all items from playlist with comprehensive logging"""
    
    items = playlist_data.get("items", [])
    if not items:
        logger.warning("No items found in playlist")
        return {"error": "no items in playlist"}
    
    if max_workers is None:
        max_workers = config.MAX_CONCURRENT_DOWNLOADS
    
    logger.info(f"Starting playlist download", extra={
        "custom_fields": {
            "event_type": "playlist_download_started", 
            "playlist_version": playlist_data.get("version", "unknown"),
            "total_items": len(items),
            "max_workers": max_workers
        }
    })
    
    start_time = time.time()
    results = []
    
    # Create HTTP session with retry logic
    session = create_http_session()
    
    try:
        # Download items concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_item = {
                executor.submit(download_single_item, item, session): item 
                for item in items
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_item):
                result = future.result()
                results.append(result)
                
                # Log intermediate progress
                completed = len(results)
                logger.info(f"Download progress: {completed}/{len(items)} items completed ({result['filename']}: {result['status']})")
    
    finally:
        session.close()
    
    # Calculate summary statistics
    total_time = time.time() - start_time
    downloaded_count = sum(1 for r in results if r["status"] == "downloaded")
    cached_count = sum(1 for r in results if r["status"] == "cached")
    error_count = sum(1 for r in results if r["status"] == "error")
    total_bytes = sum(r.get("bytes_downloaded", 0) for r in results)
    
    summary = {
        "total_items": len(items),
        "downloaded": downloaded_count,
        "cached": cached_count,
        "errors": error_count,
        "total_bytes_downloaded": total_bytes,
        "total_time": total_time,
        "results": results,
        "error_details": [r for r in results if r["status"] == "error"]
    }
    
    logger.info(f"Playlist download completed", extra={
        "custom_fields": {
            "event_type": "playlist_download_completed",
            "summary": summary
        }
    })
    
    # Log any errors
    if error_count > 0:
        logger.warning(f"Download completed with {error_count} errors:")
        for error_result in summary["error_details"]:
            logger.error(f"  {error_result['filename']}: {error_result['reason']}")
    
    return summary

def load_and_download_playlist(playlist_path: Path = None) -> Dict[str, Any]:
    """Load playlist and download all required media"""
    
    if playlist_path is None:
        playlist_path = config.PLAYLIST_FILE
    
    logger.info(f"Loading playlist from {playlist_path}")
    
    try:
        if not playlist_path.exists():
            logger.error(f"Playlist file not found: {playlist_path}")
            return {"error": f"playlist file not found: {playlist_path}"}
        
        # Load playlist
        with open(playlist_path, 'r') as f:
            playlist_data = json.load(f)
        
        logger.info(f"Loaded playlist: {playlist_data.get('version', 'unknown')} with {len(playlist_data.get('items', []))} items")
        
        # Download items
        return download_playlist_items(playlist_data)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in playlist file {playlist_path}: {e}")
        return {"error": f"invalid json: {e}"}
        
    except Exception as e:
        logger.error(f"Failed to load and download playlist: {e}", exc_info=True)
        return {"error": str(e)}

def get_cache_status() -> Dict[str, Any]:
    """Get current cache status and statistics"""
    
    cache_dir = config.MEDIA_CACHE_DIR
    
    try:
        # Count files and calculate total size
        cached_files = []
        total_size = 0
        
        for file_path in cache_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.endswith('.tmp'):
                size = file_path.stat().st_size
                cached_files.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(cache_dir)),
                    "size": size,
                    "modified": file_path.stat().st_mtime
                })
                total_size += size
        
        status = {
            "cache_directory": str(cache_dir),
            "total_files": len(cached_files),
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024*1024), 2),
            "files": cached_files,
            "download_progress": progress.get_status()
        }
        
        logger.debug(f"Cache status retrieved: {len(cached_files)} files, {status['total_size_mb']} MB")
        return status
        
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    
    print("🎬 Pi Player Download Manager")
    print("=" * 50)
    
    # Test logging
    logger.info("Download Manager started")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            # Show cache status
            status = get_cache_status()
            print(f"📦 Cache Status:")
            print(f"   Files: {status.get('total_files', 0)}")
            print(f"   Total Size: {status.get('total_size_mb', 0)} MB")
            print(f"   Directory: {status.get('cache_directory', 'unknown')}")
            
        elif sys.argv[1] == "--download":
            # Download current playlist
            print("⬇️  Downloading current playlist...")
            result = load_and_download_playlist()
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                sys.exit(1)
            else:
                print(f"✅ Download complete:")
                print(f"   Downloaded: {result.get('downloaded', 0)}")
                print(f"   Cached: {result.get('cached', 0)}")
                print(f"   Errors: {result.get('errors', 0)}")
                print(f"   Total Size: {result.get('total_bytes_downloaded', 0) / (1024*1024):.1f} MB")
                print(f"   Time: {result.get('total_time', 0):.1f} seconds")
        else:
            print("Usage: download_manager.py [--status|--download]")
    else:
        # Show available commands
        print("Available commands:")
        print("  --status    Show cache status")
        print("  --download  Download current playlist")
        print("\nFor detailed logs, check: logs/download_manager.log")