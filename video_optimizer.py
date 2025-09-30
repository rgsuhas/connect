#!/usr/bin/env python3
"""
Video Optimizer for Pi Player
Downscales high-resolution videos for better Pi performance
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

def get_video_info(video_path: Path) -> Optional[Dict[str, Any]]:
    """Get video resolution and codec info using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        import json
        data = json.loads(result.stdout)
        
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                return {
                    "width": stream.get("width", 0),
                    "height": stream.get("height", 0),
                    "codec": stream.get("codec_name", "unknown"),
                    "duration": float(stream.get("duration", 0))
                }
        
        return None
        
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def needs_optimization(video_info: Dict[str, Any]) -> bool:
    """Check if video needs optimization for Pi"""
    if not video_info:
        return False
    
    width = video_info.get("width", 0)
    height = video_info.get("height", 0)
    
    # Optimize if resolution is higher than 1080p
    return height > 1080 or width > 1920

def optimize_video_for_pi(input_path: Path, output_path: Path) -> bool:
    """
    Optimize video for Raspberry Pi playback
    - Downscale to 1080p max
    - Use Pi-friendly codec settings
    - Optimize for smooth playback
    """
    try:
        print(f"🎬 Optimizing video for Pi: {input_path.name}")
        
        # Get original video info
        video_info = get_video_info(input_path)
        if not video_info:
            print("❌ Could not get video information")
            return False
        
        width = video_info.get("width", 0)
        height = video_info.get("height", 0)
        
        print(f"   Original: {width}x{height} ({video_info.get('codec')})")
        
        # Determine target resolution (maintain aspect ratio)
        if height > 1080:
            # Scale down to 1080p
            target_height = 1080
            target_width = int((width * target_height) / height)
            # Make sure width is even (required for h264)
            target_width = target_width - (target_width % 2)
        else:
            target_width = width
            target_height = height
        
        print(f"   Target: {target_width}x{target_height}")
        
        # FFmpeg command optimized for Pi hardware
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-vf", f"scale={target_width}:{target_height}",
            "-c:v", "libx264",  # H.264 codec
            "-preset", "fast",  # Fast encoding
            "-crf", "28",  # Good quality/size balance  
            "-profile:v", "main",  # Main profile (Pi-friendly)
            "-level", "4.0",  # Level 4.0 (Pi compatible)
            "-pix_fmt", "yuv420p",  # Pi-friendly pixel format
            "-movflags", "+faststart",  # Progressive download
            "-an",  # Remove audio to save space/CPU
            "-y",  # Overwrite output
            str(output_path)
        ]
        
        print("   🔄 Transcoding... (this may take a while)")
        
        # Run ffmpeg with progress
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True
        )
        
        # Monitor progress
        duration = video_info.get("duration", 0)
        for line in process.stdout:
            if "time=" in line:
                # Extract time progress
                try:
                    time_str = line.split("time=")[1].split()[0]
                    h, m, s = time_str.split(":")
                    current_time = int(h) * 3600 + int(m) * 60 + float(s)
                    if duration > 0:
                        progress = (current_time / duration) * 100
                        print(f"   ⏳ Progress: {progress:.1f}%", end="\r")
                except:
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            # Check output file
            if output_path.exists() and output_path.stat().st_size > 0:
                optimized_info = get_video_info(output_path)
                if optimized_info:
                    orig_size = input_path.stat().st_size / (1024 * 1024)
                    opt_size = output_path.stat().st_size / (1024 * 1024)
                    print(f"\n   ✅ Optimization complete!")
                    print(f"   📦 Size: {orig_size:.1f} MB → {opt_size:.1f} MB")
                    print(f"   🎥 Resolution: {width}x{height} → {optimized_info['width']}x{optimized_info['height']}")
                    return True
            
        print(f"\n❌ Optimization failed (ffmpeg exit code: {process.returncode})")
        return False
        
    except Exception as e:
        print(f"❌ Optimization error: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python3 video_optimizer.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)
    
    success = optimize_video_for_pi(input_file, output_file)
    sys.exit(0 if success else 1)
