#!/bin/bash

# Build mybro.app for macOS
# Creates a standalone .app bundle that launches backend + frontend

echo "Building mybro.app for macOS"
echo ""

# Set up paths
MYBRO_DIR="/Users/andy/mybro"
APP_NAME="mybro"
APP_DIR="$MYBRO_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# Clean up old build
rm -rf "$APP_DIR"

# Create app structure
echo "Creating app bundle structure..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Create the main executable launcher
echo "Creating launcher..."
cat > "$MACOS_DIR/mybro" << 'LAUNCHER'
#!/bin/bash

# mybro App Launcher
# Inherit full shell environment (.app bundles don't get PATH)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

MYBRO_DIR="/Users/andy/mybro"
LOG_DIR="$HOME/.mybro/logs"
mkdir -p "$LOG_DIR"

# Kill any existing instances on our ports
lsof -ti:9000 | xargs kill -9 2>/dev/null
lsof -ti:9001 | xargs kill -9 2>/dev/null

# Start FastAPI backend
cd "$MYBRO_DIR"
source .venv/bin/activate

uvicorn backend.main:app --host 127.0.0.1 --port 9000 \
    >> "$LOG_DIR/server.log" 2>&1 &
BACKEND_PID=$!

# Start Vite frontend (direct binary, no npx)
cd "$MYBRO_DIR/frontend"
"$MYBRO_DIR/frontend/node_modules/.bin/vite" --port 9001 \
    >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

# Open browser immediately — vite is fast enough
sleep 2
open http://localhost:9001

# Cleanup on exit
cleanup() {
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT INT TERM

# Keep running until both processes exit
wait $BACKEND_PID $FRONTEND_PID
LAUNCHER

chmod +x "$MACOS_DIR/mybro"

# Create Info.plist
echo "Creating Info.plist..."
cat > "$CONTENTS_DIR/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>mybro</string>
    <key>CFBundleDisplayName</key>
    <string>mybro</string>
    <key>CFBundleIdentifier</key>
    <string>com.andy.mybro</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>mybro</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.10</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>
EOF

# Generate icon
echo "Generating icon..."
python3 << 'PYTHON'
from PIL import Image, ImageDraw, ImageFont

size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Black background with white glare gradient (top to bottom, white->transparent)
for y in range(size):
    glare = int(80 * (1 - y / size))  # white opacity fades from top to bottom
    r = glare
    g = glare
    b = glare
    draw.rectangle([0, y, size, y + 1], fill=(r, g, b, 255))

# Rounded rect mask (macOS icon shape)
mask = Image.new('L', (size, size), 0)
mask_draw = ImageDraw.Draw(mask)
mask_draw.rounded_rectangle([0, 0, size, size], radius=100, fill=255)
img.putalpha(mask)

# Draw emoji - render at supported size then composite scaled
# Apple Color Emoji only supports specific sizes (160 is the largest)
emoji_font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 160)
emoji_img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
emoji_draw = ImageDraw.Draw(emoji_img)
bbox = emoji_draw.textbbox((0, 0), "\U0001f60e", font=emoji_font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
ex = (256 - tw) // 2 - bbox[0]
ey = (256 - th) // 2 - bbox[1]
emoji_draw.text((ex, ey), "\U0001f60e", font=emoji_font, embedded_color=True)
# Scale up to fill most of the icon
emoji_scaled = emoji_img.resize((400, 400), Image.LANCZOS)
# Paste centered on the background
offset = (size - 400) // 2
img.paste(emoji_scaled, (offset, offset), emoji_scaled)

img.save('/Users/andy/mybro/icon.png')
import os
os.system('sips -s format icns /Users/andy/mybro/icon.png --out /Users/andy/mybro/icon.icns 2>/dev/null')
print("Icon generated")
PYTHON

# Move icon to Resources
mv icon.icns "$RESOURCES_DIR/" 2>/dev/null || true
mv icon.png "$RESOURCES_DIR/" 2>/dev/null || true

echo ""
echo "mybro.app built successfully!"
echo ""
echo "Location: $APP_DIR"
echo ""
echo "To launch:"
echo "  open $APP_DIR"
echo "  -- or drag to Dock --"
echo ""
echo "The app will:"
echo "  - Start FastAPI backend on http://localhost:9000"
echo "  - Start Vite frontend on http://localhost:9001"
echo "  - Open your browser to the dashboard"
