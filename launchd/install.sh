#!/bin/bash
set -e

MYBRO_DIR="/Users/andy/mybro"
DATA_DIR="/Users/andy/.mybro"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "=== mybro install ==="

# Create data directories
mkdir -p "$DATA_DIR/logs" "$DATA_DIR/screenshots"

# Create PostgreSQL database if needed
if ! /opt/homebrew/opt/postgresql@16/bin/psql -U andy -d mybro -c "SELECT 1" &>/dev/null; then
    echo "Creating mybro database..."
    /opt/homebrew/opt/postgresql@16/bin/createdb -U andy mybro
    /opt/homebrew/opt/postgresql@16/bin/psql -U andy -d mybro -f "$MYBRO_DIR/backend/db/migrations/001_initial.sql"
    echo "Database created."
else
    echo "Database exists."
fi

# Initialize SQLite tracking DB
"$MYBRO_DIR/.venv/bin/python" -c "
import asyncio, aiosqlite
async def init():
    db = await aiosqlite.connect('$DATA_DIR/tracking.db')
    await db.executescript(open('$MYBRO_DIR/backend/db/sqlite.py').read().split(\"SCHEMA = \\\"\\\"\\\"\")[1].split(\"\\\"\\\"\\\"\")[0])
    await db.commit()
    await db.close()
    print('SQLite tracking DB initialized.')
asyncio.run(init())
"

# Unload existing agents
for plist in com.mybro.server com.mybro.tracker com.mybro.tpm; do
    launchctl unload "$LAUNCH_AGENTS/$plist.plist" 2>/dev/null || true
done

# Symlink plists
for plist in com.mybro.server com.mybro.tracker com.mybro.tpm; do
    ln -sf "$MYBRO_DIR/launchd/$plist.plist" "$LAUNCH_AGENTS/$plist.plist"
    echo "Linked $plist"
done

# Load agents
for plist in com.mybro.server com.mybro.tracker com.mybro.tpm; do
    launchctl load "$LAUNCH_AGENTS/$plist.plist"
    echo "Loaded $plist"
done

echo ""
echo "=== mybro installed ==="
echo "Server:  http://127.0.0.1:9000"
echo "Logs:    $DATA_DIR/logs/"
echo ""
echo "To check status:"
echo "  launchctl list | grep mybro"
echo ""
echo "To stop:"
echo "  launchctl unload ~/Library/LaunchAgents/com.mybro.*.plist"
