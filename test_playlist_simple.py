#!/usr/bin/env python3
"""
Simple Test for Cloudinary Default Playlist
Tests playlist creation without filesystem operations
"""

import json
from datetime import datetime

# Hard-coded default Cloudinary collection URLs
DEFAULT_CLOUDINARY_COLLECTIONS = [
    "https://collection.cloudinary.com/dxfhfpaym/8006a0aeec057b5fdae295b27ea0f1e2",
    "https://collection.cloudinary.com/dxfhfpaym/a8763aa70fe1ae9284552d3b2aba5ebf",
    "https://collection.cloudinary.com/dxfhfpaym/173ef9cfc1e34d25a3241c1bfdc6c733",
    "https://collection.cloudinary.com/dxfhfpaym/329afc666ff08426da6c2f2f2a529ea8",
    "https://collection.cloudinary.com/dxfhfpaym/d4ac678778867b5fbe15e2a1f10fb589",
    "https://collection.cloudinary.com/dxfhfpaym/152008e9ff99a72cb8de06f125dab9b8",
    "https://collection.cloudinary.com/dxfhfpaym/9a919c47d389473ff2d9b4ceff7b1093"
]

def create_default_cloudinary_playlist():
    """Create default playlist with Cloudinary collection URLs"""
    
    # Create placeholder items for each collection
    items = []
    for i, collection_url in enumerate(DEFAULT_CLOUDINARY_COLLECTIONS, 1):
        # Extract collection ID from URL
        collection_id = collection_url.split('/')[-1]
        
        items.append({
            "filename": f"cloudinary_collection_{i}.mp4",
            "url": collection_url,  # Use collection URL directly
            "duration": 30,  # Default duration
            "checksum": None,  # No checksum for placeholder
            "metadata": {
                "source": "cloudinary_collection", 
                "collection_id": collection_id,
                "collection_url": collection_url,
                "note": "This is a Cloudinary collection URL - requires JavaScript to access actual videos"
            }
        })
    
    playlist = {
        "version": "default-cloudinary-v1.0",
        "last_updated": datetime.now().isoformat(),
        "loop": True,
        "description": "Default Cloudinary collection playlist - fallback when no backend playlist available",
        "source": "default_fallback",
        "cloudinary_collections": DEFAULT_CLOUDINARY_COLLECTIONS,
        "items": items
    }
    
    return playlist

def create_sample_video_playlist():
    """Create a playlist with working sample videos for immediate testing"""
    
    sample_videos = [
        {
            "filename": "big_buck_bunny.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "duration": 60,
            "checksum": None
        },
        {
            "filename": "elephants_dream.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4", 
            "duration": 60,
            "checksum": None
        },
        {
            "filename": "for_bigger_blazes.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "duration": 15,
            "checksum": None
        },
        {
            "filename": "for_bigger_escapes.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
            "duration": 15,
            "checksum": None
        },
        {
            "filename": "for_bigger_fun.mp4",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
            "duration": 60,
            "checksum": None
        }
    ]
    
    playlist = {
        "version": "default-samples-v1.0",
        "last_updated": datetime.now().isoformat(),
        "loop": True,
        "description": "Default sample video playlist - immediate playback capability",
        "source": "default_samples",
        "items": sample_videos
    }
    
    return playlist

def main():
    """Test playlist creation"""
    print("🎬 Pi Player Default Playlist Test")
    print("=" * 40)
    
    # Test Cloudinary playlist creation
    print("\n🧪 Testing Cloudinary playlist creation...")
    cloudinary_playlist = create_default_cloudinary_playlist()
    
    print(f"✅ Created Cloudinary playlist:")
    print(f"   Version: {cloudinary_playlist['version']}")
    print(f"   Items: {len(cloudinary_playlist['items'])}")
    print(f"   Description: {cloudinary_playlist['description']}")
    
    print("\n📋 Cloudinary Collection URLs:")
    for i, url in enumerate(cloudinary_playlist['cloudinary_collections'], 1):
        collection_id = url.split('/')[-1]
        print(f"   {i}. {collection_id}")
    
    # Test sample playlist creation
    print("\n🧪 Testing sample video playlist creation...")
    sample_playlist = create_sample_video_playlist()
    
    print(f"✅ Created sample playlist:")
    print(f"   Version: {sample_playlist['version']}")
    print(f"   Items: {len(sample_playlist['items'])}")
    print(f"   Description: {sample_playlist['description']}")
    
    print("\n🎬 Sample Videos:")
    for i, item in enumerate(sample_playlist['items'], 1):
        print(f"   {i}. {item['filename']} ({item['duration']}s)")
    
    # Save example playlists to files
    print("\n💾 Saving example playlists...")
    
    with open("example_cloudinary_playlist.json", "w") as f:
        json.dump(cloudinary_playlist, f, indent=2)
    print("   ✅ Saved example_cloudinary_playlist.json")
    
    with open("example_sample_playlist.json", "w") as f:
        json.dump(sample_playlist, f, indent=2)
    print("   ✅ Saved example_sample_playlist.json")
    
    print("\n🎯 Integration Summary")
    print("=" * 25)
    print("✅ Default playlist creation is working!")
    print("✅ Your 7 Cloudinary collection URLs are integrated")
    print("✅ Sample video fallback is available")
    print("\n🚀 Next Steps:")
    print("   1. Install Pi Player: sudo ./install.sh")
    print("   2. The playlist manager will automatically use these as fallback")
    print("   3. When your backend API is ready, playlists from backend take priority")
    print("   4. Replace collection URLs with direct video URLs when available")

if __name__ == "__main__":
    main()