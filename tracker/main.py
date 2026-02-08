"""Activity tracker daemon — screenshots, input monitoring, AFK detection."""

import asyncio
import math
import signal
import sys
import time

import aiosqlite

from backend.config import config
from tracker.input_monitor import InputMonitor
from tracker.afk_detector import AFKDetector
from tracker.screenshot import capture_region, get_mouse_position, cleanup_old_screenshots
from tracker.classifier import classify, set_project_names


async def get_project_names(db: aiosqlite.Connection) -> list[str]:
    """Fetch project names from postgres via the API, or fallback to a simple list."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://127.0.0.1:9000/api/projects")
            data = r.json()
            return [p["name"] for p in data.get("projects", [])]
    except Exception:
        return []


async def run_tracker():
    # Init SQLite
    db = await aiosqlite.connect(str(config.db.sqlite_path))
    db.row_factory = aiosqlite.Row

    # Ensure tables exist
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS activity_windows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT, window_title TEXT, app_name TEXT,
            confidence REAL, started_at REAL NOT NULL, ended_at REAL
        );
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT NOT NULL, project TEXT, timestamp REAL NOT NULL,
            region_x INTEGER, region_y INTEGER, region_w INTEGER, region_h INTEGER
        );
        CREATE TABLE IF NOT EXISTS input_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            minute INTEGER NOT NULL UNIQUE,
            keystrokes INTEGER DEFAULT 0, mouse_moves INTEGER DEFAULT 0,
            mouse_clicks INTEGER DEFAULT 0, scroll_events INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS afk_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at REAL NOT NULL, ended_at REAL,
            duration_s REAL, claude_active BOOLEAN DEFAULT FALSE
        );
    """)
    await db.commit()

    # Load project names for classifier
    project_names = await get_project_names(db)
    set_project_names(project_names)
    print(f"Tracking {len(project_names)} projects")

    # Start input monitoring (runs on separate threads via pynput)
    monitor = InputMonitor()
    monitor.start()
    afk = AFKDetector(monitor)

    current_window = {"project": None, "started_at": time.time()}
    screenshot_interval = config.tracker.screenshot_interval_s
    input_interval = config.tracker.input_aggregate_interval_s

    last_screenshot = 0
    last_input_flush = 0

    print(f"Tracker running: screenshots every {screenshot_interval}s, "
          f"input flush every {input_interval}s, AFK threshold {config.tracker.afk_threshold_s}s")

    try:
        while True:
            now = time.time()

            # 1. Screenshot + classify (every 20s)
            if now - last_screenshot >= screenshot_interval:
                last_screenshot = now

                if not afk.is_afk:
                    x, y = get_mouse_position()
                    result = capture_region(x, y, config.tracker.screenshot_region_px)

                    if result:
                        filepath, meta = result
                        classification = classify(filepath)

                        # Store screenshot metadata
                        await db.execute(
                            """INSERT INTO screenshots (filepath, project, timestamp, region_x, region_y, region_w, region_h)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (filepath, classification["project"], meta["timestamp"],
                             meta["region_x"], meta["region_y"], meta["region_w"], meta["region_h"]),
                        )

                        # Track activity window changes
                        if classification["project"] != current_window["project"]:
                            if current_window["project"]:
                                await db.execute(
                                    """INSERT INTO activity_windows (project, window_title, app_name, confidence, started_at, ended_at)
                                       VALUES (?, ?, ?, ?, ?, ?)""",
                                    (current_window["project"], classification["window_title"],
                                     classification["app_name"], classification.get("confidence", 0),
                                     current_window["started_at"], now),
                                )
                            current_window = {
                                "project": classification["project"],
                                "started_at": now,
                            }

                        await db.commit()

            # 2. Flush input counts (every 60s)
            if now - last_input_flush >= input_interval:
                last_input_flush = now
                counts = monitor.flush()
                minute_ts = int(math.floor(now / 60) * 60)

                await db.execute(
                    """INSERT INTO input_activity (minute, keystrokes, mouse_moves, mouse_clicks, scroll_events)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(minute) DO UPDATE SET
                         keystrokes = keystrokes + excluded.keystrokes,
                         mouse_moves = mouse_moves + excluded.mouse_moves,
                         mouse_clicks = mouse_clicks + excluded.mouse_clicks,
                         scroll_events = scroll_events + excluded.scroll_events""",
                    (minute_ts, counts["keystrokes"], counts["mouse_moves"],
                     counts["mouse_clicks"], counts["scroll_events"]),
                )
                await db.commit()

            # 3. AFK detection (every 5s)
            afk_event = afk.check()
            if afk_event:
                if afk_event["event"] == "afk_start":
                    await db.execute(
                        "INSERT INTO afk_periods (started_at, claude_active) VALUES (?, ?)",
                        (afk_event["started_at"], afk_event["claude_active"]),
                    )
                    print(f"AFK started (claude active: {afk_event['claude_active']})")
                elif afk_event["event"] == "afk_end":
                    await db.execute(
                        """UPDATE afk_periods SET ended_at = ?, duration_s = ?, claude_active = ?
                           WHERE started_at = ?""",
                        (afk_event["ended_at"], afk_event["duration_s"],
                         afk_event["claude_active"], afk_event["started_at"]),
                    )
                    print(f"AFK ended: {afk_event['duration_s']:.0f}s")
                await db.commit()

            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Tracker shutting down...")
    finally:
        # Close current activity window
        if current_window["project"]:
            await db.execute(
                """INSERT INTO activity_windows (project, window_title, app_name, confidence, started_at, ended_at)
                   VALUES (?, '', '', 0, ?, ?)""",
                (current_window["project"], current_window["started_at"], time.time()),
            )
            await db.commit()

        monitor.stop()
        await db.close()
        # Cleanup old screenshots once per run
        cleanup_old_screenshots(7)
        print("Tracker stopped.")


def main():
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)
    try:
        loop.run_until_complete(run_tracker())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
