#!/usr/bin/env python3
"""
Media Downloader for Pi Player
- Incremental update logic
- Checksum verification
- Concurrent downloads
"""

import hashlib
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from config import config

logger = logging.getLogger("downloader")
logger.setLevel(getattr(logging, config.LOG_LEVEL))
if not logger.handlers:
    fh = logging.FileHandler(config.get_log_path("downloader"))
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)


def sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error(f"Checksum error for {path}: {e}")
        return None


def needs_download(item: Dict) -> Tuple[bool, str]:
    """Determine if an item needs to be downloaded.
    Playlist item format expected:
    {
      "url": "https://...",
      "filename": "file.mp4",
      "checksum": "<sha256>",
      "duration": 10  # optional for images
    }
    """
    filename = item.get("filename")
    checksum = item.get("checksum")
    if not filename:
        return False, "missing filename"

    dest = config.get_media_path(filename)
    if not dest.exists():
        return True, "not cached"

    if checksum:
        local_sum = sha256_file(dest)
        if local_sum != checksum:
            return True, "checksum mismatch"
        return False, "up-to-date"

    # If no checksum, trust mtime existence
    return False, "exists"


def download_one(item: Dict, session: requests.Session, timeout: int) -> Dict:
    url = item.get("url")
    filename = item.get("filename")
    checksum = item.get("checksum")

    result = {
        "filename": filename,
        "url": url,
        "status": "skipped",
        "reason": "",
        "bytes": 0
    }

    ok, reason = needs_download(item)
    if not ok:
        result["status"] = "ok"
        result["reason"] = reason
        return result

    if not url or not filename:
        result["status"] = "error"
        result["reason"] = "missing url or filename"
        return result

    dest = config.get_media_path(filename)
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with session.get(url, stream=True, timeout=timeout, verify=config.VERIFY_SSL) as r:
            r.raise_for_status()
            tmp_path = dest.with_suffix(dest.suffix + ".part")
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                        result["bytes"] += len(chunk)
            # Verify checksum if provided
            if checksum:
                downloaded_sum = sha256_file(tmp_path)
                if downloaded_sum != checksum:
                    tmp_path.unlink(missing_ok=True)
                    result["status"] = "error"
                    result["reason"] = "checksum verify failed"
                    return result
            tmp_path.replace(dest)
        result["status"] = "downloaded"
        result["reason"] = ""
        return result
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        result["status"] = "error"
        result["reason"] = str(e)
        return result


def download_playlist_items(playlist: Dict) -> Dict:
    """Download or verify all items in a playlist incrementally."""
    items: List[Dict] = playlist.get("items", [])
    results: List[Dict] = []

    # Allow nested paths in filenames
    for it in items:
        fname = it.get("filename")
        if fname:
            dest = config.get_media_path(fname)
            dest.parent.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_DOWNLOADS) as ex:
            futures = [ex.submit(download_one, it, session, config.DOWNLOAD_TIMEOUT) for it in items]
            for fut in as_completed(futures):
                results.append(fut.result())

    summary = {
        "total": len(items),
        "downloaded": sum(1 for r in results if r["status"] == "downloaded"),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": [r for r in results if r["status"] == "error"],
        "results": results,
    }

    # Optionally, prune cache files not in playlist
    cached_files = {p.relative_to(config.MEDIA_CACHE_DIR).as_posix() for p in config.MEDIA_CACHE_DIR.rglob('*') if p.is_file()}
    wanted_files = {it.get("filename") for it in items if it.get("filename")}
    unused = cached_files - wanted_files
    summary["unused_cached_files"] = sorted(unused)

    logger.info(json.dumps({"download_summary": summary}))
    return summary


# A simple global lock to prevent concurrent runs
_download_lock = threading.Lock()

def update_cache_for_playlist(playlist_path: Path) -> Dict:
    """Load playlist from file and download required media."""
    with _download_lock:
        try:
            data = json.loads(playlist_path.read_text())
            return download_playlist_items(data)
        except Exception as e:
            logger.exception(f"Failed to update cache: {e}")
            return {"error": str(e)}
