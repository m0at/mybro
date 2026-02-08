"""SQLite connection for local tracking data using aiosqlite."""

import aiosqlite
from backend.config import config

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_windows (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT,
    window_title TEXT,
    app_name    TEXT,
    confidence  REAL,
    started_at  REAL NOT NULL,
    ended_at    REAL
);

CREATE TABLE IF NOT EXISTS screenshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath    TEXT NOT NULL,
    project     TEXT,
    timestamp   REAL NOT NULL,
    region_x    INTEGER,
    region_y    INTEGER,
    region_w    INTEGER,
    region_h    INTEGER
);

CREATE TABLE IF NOT EXISTS input_activity (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    minute          INTEGER NOT NULL UNIQUE,
    keystrokes      INTEGER DEFAULT 0,
    mouse_moves     INTEGER DEFAULT 0,
    mouse_clicks    INTEGER DEFAULT 0,
    scroll_events   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS afk_periods (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      REAL NOT NULL,
    ended_at        REAL,
    duration_s      REAL,
    claude_active   BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS claude_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT,
    command     TEXT,
    started_at  REAL NOT NULL,
    ended_at    REAL,
    exit_code   INTEGER,
    during_afk  BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_activity_windows_started ON activity_windows(started_at);
CREATE INDEX IF NOT EXISTS idx_input_activity_minute ON input_activity(minute);
CREATE INDEX IF NOT EXISTS idx_afk_periods_started ON afk_periods(started_at);
CREATE INDEX IF NOT EXISTS idx_screenshots_timestamp ON screenshots(timestamp);
"""


async def init_db():
    global _db
    _db = await aiosqlite.connect(str(config.db.sqlite_path))
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA)
    await _db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def get_db() -> aiosqlite.Connection:
    if _db is None:
        await init_db()
    return _db
