#!/usr/bin/env python3
"""
Create Default Screen Image for Pi Player
Generates a branded default screen when no playlist is active
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_default_screen(width=1920, height=1080, output_path="default_screen.png"):
    """Create a default Pi Player screen image"""
    
    # Create image with dark gradient background
    image = Image.new('RGB', (width, height), color='#1a1a2e')
    draw = ImageDraw.Draw(image)
    
    # Create gradient background
    for y in range(height):
        # Gradient from dark blue to darker blue
        ratio = y / height
        r = int(26 + (16 - 26) * ratio)  # 1a to 10
        g = int(26 + (16 - 26) * ratio)  # 1a to 10  
        b = int(46 + (30 - 46) * ratio)  # 2e to 1e
        
        for x in range(width):
            draw.point((x, y), fill=(r, g, b))
    
    # Try to load a font, fallback to default if not available
    try:
        # Try to find a nice font
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
            '/System/Library/Fonts/Arial.ttf',  # macOS
            'C:\\Windows\\Fonts\\arial.ttf',     # Windows
        ]
        
        title_font = None
        subtitle_font = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    title_font = ImageFont.truetype(font_path, 120)
                    subtitle_font = ImageFont.truetype(font_path, 48)
                    break
                except:
                    continue
        
        # Fallback to default font
        if title_font is None:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Text content
    main_title = "Pi Player"
    subtitle = "Ready for Content"
    status_text = "Waiting for playlist..."
    
    # Calculate text positions (centered)
    title_bbox = draw.textbbox((0, 0), main_title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    
    status_bbox = draw.textbbox((0, 0), status_text, font=subtitle_font)
    status_width = status_bbox[2] - status_bbox[0]
    
    # Draw main title
    title_x = (width - title_width) // 2
    title_y = height // 2 - 150
    draw.text((title_x, title_y), main_title, fill='#ffffff', font=title_font)
    
    # Draw subtitle
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + title_height + 30
    draw.text((subtitle_x, subtitle_y), subtitle, fill='#cccccc', font=subtitle_font)
    
    # Draw status
    status_x = (width - status_width) // 2
    status_y = subtitle_y + 80
    draw.text((status_x, status_y), status_text, fill='#888888', font=subtitle_font)
    
    # Add some decorative elements
    # Draw a subtle border
    border_color = '#333366'
    draw.rectangle([(20, 20), (width-20, height-20)], outline=border_color, width=4)
    
    # Add Pi symbol (if we can draw it)
    try:
        pi_symbol = "π"
        pi_font = ImageFont.truetype(font_paths[0], 80) if font_paths and os.path.exists(font_paths[0]) else title_font
        pi_bbox = draw.textbbox((0, 0), pi_symbol, font=pi_font)
        pi_width = pi_bbox[2] - pi_bbox[0]
        pi_x = title_x - pi_width - 20
        pi_y = title_y + 10
        draw.text((pi_x, pi_y), pi_symbol, fill='#4CAF50', font=pi_font)
    except:
        pass
    
    # Add corner info
    info_font = subtitle_font
    info_text = f"Resolution: {width}x{height}"
    info_bbox = draw.textbbox((0, 0), info_text, font=info_font)
    info_x = width - (info_bbox[2] - info_bbox[0]) - 40
    info_y = height - (info_bbox[3] - info_bbox[1]) - 40
    draw.text((info_x, info_y), info_text, fill='#555555', font=info_font)
    
    # Save image
    image.save(output_path, 'PNG', quality=95)
    print(f"Default screen image created: {output_path}")
    print(f"Size: {width}x{height}")
    
    return output_path

def create_multiple_resolutions():
    """Create default images for common resolutions"""
    resolutions = [
        (1920, 1080, "default_screen_1080p.png"),
        (1280, 720, "default_screen_720p.png"), 
        (1024, 768, "default_screen_1024.png"),
        (800, 600, "default_screen_800.png"),
    ]
    
    created_files = []
    for width, height, filename in resolutions:
        try:
            path = create_default_screen(width, height, filename)
            created_files.append(path)
        except Exception as e:
            print(f"Failed to create {filename}: {e}")
    
    return created_files

if __name__ == "__main__":
    import sys
    
    # Create output directory
    output_dir = Path("default_assets")
    output_dir.mkdir(exist_ok=True)
    os.chdir(output_dir)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            created = create_multiple_resolutions()
            print(f"Created {len(created)} default screen images")
        else:
            try:
                width, height = map(int, sys.argv[1].split('x'))
                create_default_screen(width, height)
            except:
                print("Usage: python3 create_default_image.py [WIDTHxHEIGHT] or [--all]")
                print("Example: python3 create_default_image.py 1920x1080")
    else:
        # Create default 1080p image
        create_default_screen()