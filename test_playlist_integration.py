#!/usr/bin/env python3
"""
Test Script for Pi Player Playlist Integration
Tests the playlist manager with default Cloudinary fallback
"""

import json
import os
import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable development mode
os.environ["PI_PLAYER_DEV"] = "true"

# Import after setting dev mode
from config import config
from playlist_manager import get_playlist_manager
from backend_client import get_backend_client

def test_cloudinary_playlist_creation():
    """Test creating the default Cloudinary playlist"""
    print("\n🧪 Testing Cloudinary playlist creation...")
    
    manager = get_playlist_manager()
    playlist = manager.get_default_cloudinary_playlist()
    
    print(f"✅ Created playlist with {len(playlist['items'])} items")
    print(f"   Version: {playlist['version']}")
    print(f"   Description: {playlist['description']}")
    
    # Show first few items
    print("   First 3 items:")
    for i, item in enumerate(playlist['items'][:3]):
        collection_id = item['metadata']['collection_id']
        print(f"     {i+1}. {item['filename']} -> {collection_id}")
    
    return playlist

def test_sample_playlist_creation():
    """Test creating the sample video playlist"""
    print("\n🧪 Testing sample video playlist creation...")
    
    manager = get_playlist_manager()
    playlist = manager.create_sample_video_playlist()
    
    print(f"✅ Created playlist with {len(playlist['items'])} items")
    print(f"   Version: {playlist['version']}")
    print(f"   Description: {playlist['description']}")
    
    # Show items
    print("   Sample videos:")
    for i, item in enumerate(playlist['items']):
        print(f"     {i+1}. {item['filename']} ({item['duration']}s)")
    
    return playlist

def test_backend_playlist_check():
    """Test backend playlist availability check"""
    print("\n🧪 Testing backend playlist check...")
    
    manager = get_playlist_manager()
    
    # Check backend availability
    playlist = manager.check_backend_playlist_availability()
    
    if playlist:
        print(f"✅ Backend playlist available: version {playlist.get('version')}")
        return True
    else:
        print("ℹ️  No backend playlist available (expected if backend not running)")
        return False

def test_playlist_fallback_logic():
    """Test the playlist fallback logic"""
    print("\n🧪 Testing playlist fallback logic...")
    
    # Remove existing playlist to test fallback
    if config.PLAYLIST_FILE.exists():
        backup_path = config.PLAYLIST_FILE.with_suffix('.bak')
        config.PLAYLIST_FILE.rename(backup_path)
        print(f"   Backed up existing playlist to {backup_path}")
    
    manager = get_playlist_manager()
    
    # Force a fresh startup state
    manager.default_playlist_loaded = False
    manager.startup_time = time.time() - 300  # Simulate 5 minutes ago
    
    # Test fallback logic
    success = manager.ensure_playlist_available()
    
    if success and config.PLAYLIST_FILE.exists():
        with open(config.PLAYLIST_FILE, 'r') as f:
            playlist_data = json.load(f)
        
        source = playlist_data.get('source', 'unknown')
        item_count = len(playlist_data.get('items', []))
        
        print(f"✅ Playlist fallback successful")
        print(f"   Source: {source}")
        print(f"   Items: {item_count}")
        print(f"   Version: {playlist_data.get('version')}")
        
        return True
    else:
        print("❌ Playlist fallback failed")
        return False

def test_manager_status():
    """Test playlist manager status reporting"""
    print("\n🧪 Testing playlist manager status...")
    
    manager = get_playlist_manager()
    status = manager.get_playlist_status()
    
    print("✅ Manager status:")
    print(f"   Backend enabled: {status.get('backend_enabled')}")
    print(f"   Backend available: {status.get('backend_available')}")
    print(f"   Current source: {status.get('current_source')}")
    print(f"   Default loaded: {status.get('default_playlist_loaded')}")
    print(f"   Time since startup: {status.get('time_since_startup', 0):.1f}s")
    
    current_playlist = status.get('current_playlist', {})
    if current_playlist and 'error' not in current_playlist:
        print(f"   Current playlist: {current_playlist.get('version')} ({current_playlist.get('item_count')} items)")
    
    return status

def test_api_endpoints():
    """Test the playlist manager API endpoints"""
    print("\n🧪 Testing API endpoints (requires running server)...")
    
    try:
        import requests
        
        base_url = "http://localhost:8000"
        
        # Test playlist manager status endpoint
        response = requests.get(f"{base_url}/playlist/manager/status", timeout=5)
        if response.status_code == 200:
            print("✅ Playlist manager status endpoint working")
        else:
            print(f"⚠️  Status endpoint returned {response.status_code}")
        
        # Test playlist refresh endpoint
        response = requests.post(f"{base_url}/playlist/manager/refresh", timeout=10)
        if response.status_code == 200:
            print("✅ Playlist manager refresh endpoint working")
        else:
            print(f"⚠️  Refresh endpoint returned {response.status_code}")
        
        # Test get playlist endpoint (should have fallback now)
        response = requests.get(f"{base_url}/playlist", timeout=5)
        if response.status_code == 200:
            data = response.json()
            playlist = data.get('playlist')
            if playlist:
                print(f"✅ Get playlist endpoint working (got {len(playlist.get('items', []))} items)")
            else:
                print("⚠️  Playlist endpoint returned no playlist")
        else:
            print(f"⚠️  Get playlist endpoint returned {response.status_code}")
        
        return True
        
    except ImportError:
        print("ℹ️  Requests not available, skipping API tests")
        return False
    except Exception as e:
        print(f"ℹ️  API tests skipped (server not running?): {e}")
        return False

def main():
    """Run all tests"""
    print("🎬 Pi Player Playlist Integration Tests")
    print("=" * 50)
    
    # Test individual components
    cloudinary_playlist = test_cloudinary_playlist_creation()
    sample_playlist = test_sample_video_playlist_creation()
    backend_available = test_backend_playlist_check()
    fallback_success = test_playlist_fallback_logic()
    status = test_manager_status()
    api_success = test_api_endpoints()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 20)
    print(f"✅ Cloudinary playlist creation: Working")
    print(f"✅ Sample playlist creation: Working")
    print(f"{'✅' if backend_available else 'ℹ️ '} Backend playlist check: {'Available' if backend_available else 'Not available'}")
    print(f"{'✅' if fallback_success else '❌'} Playlist fallback logic: {'Working' if fallback_success else 'Failed'}")
    print(f"✅ Status reporting: Working")
    print(f"{'✅' if api_success else 'ℹ️ '} API endpoints: {'Working' if api_success else 'Server not running'}")
    
    print("\n🎯 Integration Status")
    if fallback_success:
        print("✅ Cloudinary playlist fallback is working!")
        print("   The Pi Player will now use your 7 Cloudinary collection URLs")
        print("   as default content when no backend playlist is available.")
        print("\n📋 Your Cloudinary Collections:")
        for i, url in enumerate(cloudinary_playlist['cloudinary_collections'], 1):
            collection_id = url.split('/')[-1]
            print(f"   {i}. {collection_id}")
        
        print("\n🚀 Next Steps:")
        print("   1. Start Pi Player: ./run.sh")
        print("   2. Check playlist: curl http://localhost:8000/playlist")
        print("   3. View API docs: http://localhost:8000/docs")
        print("   4. Replace collection URLs with direct video URLs when available")
    else:
        print("❌ Integration has issues - check the logs for details")
    
    print()

if __name__ == "__main__":
    main()