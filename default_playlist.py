#!/usr/bin/env python3
"""
Default Playlist Configuration for Pi Player
Contains predefined video collections from Cloudinary for testing
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from config import config

logger = logging.getLogger("default_playlist")

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = "dxfhfpaym"
CLOUDINARY_BASE_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}"

# Collection IDs from your URLs
COLLECTION_IDS = [
    "8006a0aeec057b5fdae295b27ea0f1e2",
    "a8763aa70fe1ae9284552d3b2aba5ebf", 
    "173ef9cfc1e34d25a3241c1bfdc6c733",
    "329afc666ff08426da6c2f2f2a529ea8",
    "d4ac678778867b5fbe15e2a1f10fb589",
    "152008e9ff99a72cb8de06f125dab9b8",
    "9a919c47d389473ff2d9b4ceff7b1093"
]

def create_default_playlist_with_sample_videos() -> Dict[str, Any]:
    """Create a default playlist with sample videos for testing"""
    
    # For now, use sample videos since we can't access collection content directly
    # These are publicly available sample videos for testing
    sample_videos = [
        {
            "filename": "sample_video_1.mp4",
            "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
            "duration": 30,
            "checksum": None,
            "collection_id": COLLECTION_IDS[0]
        },
        {
            "filename": "sample_video_2.mp4", 
            "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
            "duration": 30,
            "checksum": None,
            "collection_id": COLLECTION_IDS[1]
        },
        {
            "filename": "big_buck_bunny.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "duration": 60,
            "checksum": None,
            "collection_id": COLLECTION_IDS[2]
        },
        {
            "filename": "elephants_dream.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4", 
            "duration": 60,
            "checksum": None,
            "collection_id": COLLECTION_IDS[3]
        },
        {
            "filename": "for_bigger_blazes.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "duration": 15,
            "checksum": None,
            "collection_id": COLLECTION_IDS[4]
        },
        {
            "filename": "for_bigger_escape.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
            "duration": 15,
            "checksum": None,
            "collection_id": COLLECTION_IDS[5]
        },
        {
            "filename": "for_bigger_fun.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
            "duration": 60,
            "checksum": None,
            "collection_id": COLLECTION_IDS[6]
        }
    ]
    
    playlist = {
        "version": "default-v1.0",
        "last_updated": datetime.now().isoformat(),
        "loop": True,
        "description": "Default testing playlist with sample videos",
        "cloudinary_collections": COLLECTION_IDS,
        "items": sample_videos
    }
    
    return playlist

def create_cloudinary_playlist_template() -> Dict[str, Any]:
    """Create a template playlist structure for Cloudinary collections"""
    
    # Template for when we have actual Cloudinary video URLs
    # This shows the structure we'll use once we can fetch the real videos
    template_items = []
    
    for i, collection_id in enumerate(COLLECTION_IDS, 1):
        template_items.append({
            "filename": f"cloudinary_video_{i}.mp4",
            "url": f"{CLOUDINARY_BASE_URL}/video/upload/v1234567890/collection_{collection_id}/video.mp4",
            "duration": 30,  # Default duration, will be updated when we get real data
            "checksum": None,  # Will be calculated when downloaded
            "collection_id": collection_id,
            "cloudinary_public_id": f"collection_{collection_id}/video",
            "metadata": {
                "source": "cloudinary_collection",
                "collection_url": f"https://collection.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/{collection_id}"
            }
        })
    
    playlist = {
        "version": "cloudinary-template-v1.0",
        "last_updated": datetime.now().isoformat(),
        "loop": True,
        "description": "Template playlist for Cloudinary video collections",
        "cloudinary_cloud_name": CLOUDINARY_CLOUD_NAME,
        "cloudinary_collections": COLLECTION_IDS,
        "items": template_items
    }
    
    return playlist

def save_default_playlist(use_sample_videos: bool = True) -> Path:
    """Save the default playlist to file"""
    
    if use_sample_videos:
        playlist = create_default_playlist_with_sample_videos()
        filename = "default_playlist_samples.json"
    else:
        playlist = create_cloudinary_playlist_template()
        filename = "default_playlist_cloudinary.json"
    
    playlist_path = config.BASE_DIR / filename
    
    try:
        with open(playlist_path, 'w') as f:
            json.dump(playlist, f, indent=2)
        
        logger.info(f"Default playlist saved to {playlist_path}")
        return playlist_path
        
    except Exception as e:
        logger.error(f"Failed to save default playlist: {e}")
        raise

def load_default_playlist() -> None:
    """Load the default playlist into the Pi Player system"""
    
    try:
        # Create and save the default playlist
        playlist_path = save_default_playlist(use_sample_videos=True)
        
        # Copy to the active playlist location
        active_playlist_path = config.PLAYLIST_FILE
        
        with open(playlist_path, 'r') as src:
            playlist_data = json.load(src)
        
        with open(active_playlist_path, 'w') as dst:
            json.dump(playlist_data, dst, indent=2)
        
        logger.info(f"Default playlist loaded as active playlist")
        print(f"✅ Default playlist loaded with {len(playlist_data['items'])} videos")
        
        # Show playlist details
        print("\n📋 Playlist Details:")
        print(f"   Version: {playlist_data['version']}")
        print(f"   Loop: {playlist_data['loop']}")
        print(f"   Total videos: {len(playlist_data['items'])}")
        print(f"   Description: {playlist_data['description']}")
        
        print("\n🎬 Videos in playlist:")
        for i, item in enumerate(playlist_data['items'], 1):
            print(f"   {i}. {item['filename']} ({item['duration']}s)")
        
        return playlist_data
        
    except Exception as e:
        logger.error(f"Failed to load default playlist: {e}")
        raise

def create_cloudinary_fetcher_script():
    """Create a script to fetch actual Cloudinary video URLs"""
    
    script_content = '''#!/usr/bin/env python3
"""
Cloudinary Collection Fetcher
Fetches actual video URLs from Cloudinary collections
"""

import requests
import json
from typing import List, Dict, Any

CLOUDINARY_CLOUD_NAME = "dxfhfpaym"
COLLECTION_IDS = [
    "8006a0aeec057b5fdae295b27ea0f1e2",
    "a8763aa70fe1ae9284552d3b2aba5ebf", 
    "173ef9cfc1e34d25a3241c1bfdc6c733",
    "329afc666ff08426da6c2f2f2a529ea8",
    "d4ac678778867b5fbe15e2a1f10fb589",
    "152008e9ff99a72cb8de06f125dab9b8",
    "9a919c47d389473ff2d9b4ceff7b1093"
]

def fetch_collection_videos(collection_id: str) -> List[Dict[str, Any]]:
    """
    Fetch videos from a Cloudinary collection
    Note: This requires Cloudinary API credentials
    """
    
    # This is a placeholder - you'll need to implement actual Cloudinary API calls
    # or provide the direct video URLs manually
    
    print(f"📋 Collection: {collection_id}")
    print(f"   URL: https://collection.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/{collection_id}")
    print("   ⚠️  Manual intervention required - please provide direct video URLs")
    
    return []

if __name__ == "__main__":
    print("🔍 Cloudinary Collection Fetcher")
    print("=" * 50)
    
    for collection_id in COLLECTION_IDS:
        videos = fetch_collection_videos(collection_id)
    
    print("\\n💡 To use your Cloudinary videos:")
    print("1. Extract direct video URLs from each collection")
    print("2. Update the default_playlist.py with actual URLs")
    print("3. Or use the Cloudinary API with proper credentials")
'''
    
    script_path = config.BASE_DIR / "fetch_cloudinary_videos.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    script_path.chmod(0o755)
    print(f"📝 Created Cloudinary fetcher script: {script_path}")

if __name__ == "__main__":
    import sys
    
    print("🎬 Pi Player Default Playlist Generator")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--cloudinary":
        # Create Cloudinary template
        playlist = create_cloudinary_playlist_template()
        save_path = save_default_playlist(use_sample_videos=False)
        print(f"📋 Cloudinary template playlist created: {save_path}")
    else:
        # Load default sample playlist
        load_default_playlist()
    
    # Always create the fetcher script
    create_cloudinary_fetcher_script()
    
    print(f"\\n🚀 Ready to test Pi Player with default playlist!")
    print(f"   Start Pi Player: ./run.sh")
    print(f"   Check status: curl http://localhost:8000/playlist")
'''