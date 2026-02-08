"""Time tracking API — query activity data from SQLite."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Query

from backend.db import sqlite

router = APIRouter(tags=["time"])


@router.get("/time/today")
async def get_today():
    """Get today's activity summary."""
    db = await sqlite.get_db()
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0).timestamp()

    # Activity windows
    cursor = await db.execute(
        "SELECT * FROM activity_windows WHERE started_at >= ? ORDER BY started_at",
        (start_of_day,),
    )
    windows = [dict(r) for r in await cursor.fetchall()]

    # Input activity
    start_minute = int(start_of_day // 60 * 60)
    cursor = await db.execute(
        "SELECT * FROM input_activity WHERE minute >= ? ORDER BY minute",
        (start_minute,),
    )
    input_data = [dict(r) for r in await cursor.fetchall()]

    # AFK periods
    cursor = await db.execute(
        "SELECT * FROM afk_periods WHERE started_at >= ? ORDER BY started_at",
        (start_of_day,),
    )
    afk = [dict(r) for r in await cursor.fetchall()]

    # Aggregate time per project
    project_time = {}
    for w in windows:
        proj = w.get("project") or "unknown"
        duration = (w.get("ended_at") or now.timestamp()) - w["started_at"]
        project_time[proj] = project_time.get(proj, 0) + duration

    total_afk = sum(p.get("duration_s", 0) or 0 for p in afk)
    total_active = sum(project_time.values())

    return {
        "date": now.strftime("%Y-%m-%d"),
        "activity_windows": windows,
        "input_activity": input_data,
        "afk_periods": afk,
        "project_time": project_time,
        "total_active_s": total_active,
        "total_afk_s": total_afk,
    }


@router.get("/time/range")
async def get_range(
    days: int = Query(7, le=30),
):
    """Get activity summary for the last N days."""
    db = await sqlite.get_db()
    start = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0).timestamp()

    cursor = await db.execute(
        "SELECT * FROM activity_windows WHERE started_at >= ? ORDER BY started_at",
        (start,),
    )
    windows = [dict(r) for r in await cursor.fetchall()]

    cursor = await db.execute(
        "SELECT * FROM afk_periods WHERE started_at >= ? ORDER BY started_at",
        (start,),
    )
    afk = [dict(r) for r in await cursor.fetchall()]

    # Group by day and project
    daily = {}
    for w in windows:
        day = datetime.fromtimestamp(w["started_at"]).strftime("%Y-%m-%d")
        proj = w.get("project") or "unknown"
        duration = (w.get("ended_at") or datetime.now().timestamp()) - w["started_at"]
        if day not in daily:
            daily[day] = {}
        daily[day][proj] = daily[day].get(proj, 0) + duration

    return {
        "days": days,
        "daily_breakdown": daily,
        "afk_periods": len(afk),
        "total_windows": len(windows),
    }
