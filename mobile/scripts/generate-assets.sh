#!/usr/bin/env bash
# Generate placeholder PNG assets for Expo build.
# Requires: Python 3 with Pillow (pip install Pillow)
# Run once before first EAS build: bash mobile/scripts/generate-assets.sh

set -euo pipefail

ASSETS_DIR="$(dirname "$0")/../assets"
mkdir -p "$ASSETS_DIR"

python3 - << 'EOF'
from PIL import Image, ImageDraw
import os

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

BG = (15, 23, 42)       # #0f172a
FG = (99, 102, 241)     # #6366f1

def draw_hex(draw, cx, cy, r, fill):
    import math
    pts = [(cx + r * math.cos(math.radians(60*i - 30)),
            cy + r * math.sin(math.radians(60*i - 30))) for i in range(6)]
    draw.polygon(pts, fill=fill)

def make_icon(size, path):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    draw_hex(d, size//2, size//2, int(size * 0.38), FG)
    img.save(path)
    print(f"  ✓ {path} ({size}x{size})")

def make_splash(w, h, path):
    img = Image.new("RGBA", (w, h), BG)
    d = ImageDraw.Draw(img)
    draw_hex(d, w//2, h//2, min(w, h)//5, FG)
    img.save(path)
    print(f"  ✓ {path} ({w}x{h})")

def make_notification_icon(size, path):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_hex(d, size//2, size//2, int(size * 0.45), (255, 255, 255, 255))
    img.save(path)
    print(f"  ✓ {path} ({size}x{size})")

print("Generating Expo assets...")
make_icon(1024, os.path.join(ASSETS, "icon.png"))
make_icon(1024, os.path.join(ASSETS, "adaptive-icon.png"))
make_splash(1284, 2778, os.path.join(ASSETS, "splash.png"))
make_notification_icon(96, os.path.join(ASSETS, "notification-icon.png"))
print("Done. Commit the assets/ directory.")
EOF
