#!/bin/bash
set -euo pipefail

# Create Default Assets for Pi Player
# Generates default screen images for different resolutions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/default_assets"

echo "Creating Pi Player default screen assets..."

# Create assets directory
mkdir -p "$ASSETS_DIR"

# Try to use Python with PIL if available
if python3 -c "from PIL import Image" 2>/dev/null; then
    echo "PIL available, creating high-quality default screens..."
    cd "$SCRIPT_DIR"
    
    # Create the image generator if it doesn't exist
    if [[ ! -f "default_assets/create_default_image.py" ]]; then
        echo "Image generator not found, creating simple default..."
    else
        python3 default_assets/create_default_image.py --all || {
            echo "Python generation failed, creating simple alternatives..."
        }
    fi
else
    echo "PIL not available, creating simple default screens with ImageMagick..."
    
    # Try ImageMagick
    if command -v convert >/dev/null 2>&1; then
        create_with_imagemagick() {
            local width=$1
            local height=$2
            local output="$3"
            
            convert -size "${width}x${height}" \
                    -background '#1a1a2e' \
                    -fill white \
                    -gravity center \
                    -pointsize $((height/20)) \
                    -font Arial \
                    label:'Pi Player\nReady for Content' \
                    "$output"
        }
        
        cd "$ASSETS_DIR"
        create_with_imagemagick 1920 1080 "default_screen_1080p.png"
        create_with_imagemagick 1280 720 "default_screen_720p.png"
        create_with_imagemagick 1024 768 "default_screen_1024.png"
        create_with_imagemagick 800 600 "default_screen_800.png"
        
        # Create main default screen (1080p)
        cp default_screen_1080p.png default_screen.png
        
        echo "Created default screens with ImageMagick"
    else
        echo "Neither PIL nor ImageMagick available, creating minimal text screens..."
        
        # Create simple text-based defaults
        cd "$ASSETS_DIR"
        
        create_text_screen() {
            local resolution=$1
            local filename=$2
            
            cat > "$filename.txt" << EOF
Pi Player - Default Screen
========================

Resolution: $resolution
Status: Waiting for playlist...
System: $(uname -n)
Time: $(date)

Ready for content!
EOF
            # Try to convert text to image using any available tool
            if command -v convert >/dev/null 2>&1; then
                convert -background '#1a1a2e' -fill white -pointsize 24 -size 800x600 \
                        caption:@"$filename.txt" "${filename}.png" 2>/dev/null || true
                rm -f "$filename.txt"
            fi
        }
        
        create_text_screen "1920x1080" "default_screen_1080p"
        create_text_screen "1280x720" "default_screen_720p" 
        create_text_screen "1024x768" "default_screen_1024"
        create_text_screen "800x600" "default_screen_800"
        
        # Create main default
        if [[ -f "default_screen_1080p.png" ]]; then
            cp default_screen_1080p.png default_screen.png
        else
            # Absolute fallback - create a simple colored rectangle
            if command -v convert >/dev/null 2>&1; then
                convert -size 1920x1080 -background '#1a1a2e' \
                        -fill white -gravity center -pointsize 48 \
                        -annotate +0+0 'Pi Player\nReady for Content' \
                        default_screen.png
            fi
        fi
    fi
fi

# Verify we created at least the main default screen
if [[ -f "$ASSETS_DIR/default_screen.png" ]]; then
    echo "✓ Default screen created successfully"
    echo "  Location: $ASSETS_DIR/default_screen.png"
    
    # List all created files
    echo "Created assets:"
    ls -la "$ASSETS_DIR"/*.png 2>/dev/null | sed 's/^/  /' || echo "  (no PNG files found)"
else
    echo "⚠ Could not create default screen image"
    echo "  The media player will attempt to create one at runtime"
    
    # Create a placeholder file
    mkdir -p "$ASSETS_DIR"
    echo "Pi Player Default Screen - Created at Runtime" > "$ASSETS_DIR/README.txt"
fi

echo "Default assets setup complete!"