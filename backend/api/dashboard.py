"""Dashboard API — aggregated data for project cards."""

import asyncio
from datetime import datetime

from fastapi import APIRouter

from backend.db import postgres, sqlite
from backend.services import loc_counter, process_scanner, digitalocean, git_info, session_scanner, health_scorer

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard():
    """Get all data needed for the dashboard view (legacy)."""
    projects = await postgres.fetch(
        "SELECT * FROM projects WHERE status = 'active' ORDER BY name"
    )

    dashboard_data = []
    for p in projects:
        loc_data = await loc_counter.get_loc_chart_data(p["id"], days=3)
        dashboard_data.append({
            "project": dict(p),
            "loc": loc_data,
        })

    return {"projects": dashboard_data}


@router.post("/dashboard/snapshot")
async def take_snapshot():
    """Trigger a LOC snapshot for all projects."""
    results = await loc_counter.snapshot_all_projects()
    return {"snapshots": results, "count": len(results)}


@router.get("/dashboard/full")
async def get_full_dashboard():
    """Single aggregated call for the command-center dashboard."""

    # Phase 1: parallel fetch of independent data
    projects_task = postgres.fetch(
        "SELECT * FROM projects WHERE status = 'active' ORDER BY name"
    )
    servers_task = process_scanner.get_listening_servers()
    scripts_task = process_scanner.get_running_scripts()
    claude_task = process_scanner.get_claude_processes()
    droplets_task = digitalocean.get_droplets()

    projects, servers, scripts, claude_procs, droplets = await asyncio.gather(
        projects_task, servers_task, scripts_task, claude_task, droplets_task,
    )

    project_ids = [p["id"] for p in projects]

    # Phase 2: data that needs project list
    git_task = git_info.get_all_git_info(projects)
    loc_task = _batch_loc(project_ids)
    tickets_task = _batch_tickets(project_ids)
    feed_task = postgres.fetch(
        """SELECT su.*, p.name as project_name, p.color as project_color
           FROM status_updates su
           LEFT JOIN projects p ON su.project_id = p.id
           ORDER BY su.created_at DESC LIMIT 10"""
    )
    time_task = _get_time_summary()
    session_stats_task = session_scanner.get_session_stats()
    health_task = health_scorer.get_all_health()

    git_map, loc_map, tickets_map, feed, time_summary, session_stats, health_map = await asyncio.gather(
        git_task, loc_task, tickets_task, feed_task, time_task,
        session_stats_task, health_task,
    )

    # Build server/script/claude/droplet maps by project name
    server_map: dict[str, list] = {}
    unlinked_servers = []
    for s in servers:
        proj = s.get("project")
        if proj:
            server_map.setdefault(proj, []).append(s)
        else:
            unlinked_servers.append(s)

    script_map: dict[str, list] = {}
    unlinked_scripts = []
    for s in scripts:
        proj = s.get("project")
        if proj:
            script_map.setdefault(proj, []).append(s)
        else:
            unlinked_scripts.append(s)

    claude_map: dict[str, list] = {}
    for c in claude_procs:
        proj = c.get("project")
        if proj:
            claude_map.setdefault(proj, []).append(c)

    droplet_map: dict[str, list] = {}
    for d in droplets:
        # Match droplet name to project slug
        for p in projects:
            if p["slug"] in d["name"].lower():
                droplet_map.setdefault(p["name"], []).append(d)
                break

    # Assemble per-project data, sort by last_commit_ts descending
    project_rows = []
    for p in projects:
        pid = p["id"]
        name = p["name"]
        git = git_map.get(pid, {})
        health = health_map.get(pid, {})
        sess = session_stats.get(pid, {})
        project_rows.append({
            "project": p,
            "git": git,
            "loc": loc_map.get(pid, []),
            "tickets": tickets_map.get(pid, {}),
            "servers": server_map.get(name, []),
            "scripts": script_map.get(name, []),
            "claude": claude_map.get(name, []),
            "droplets": droplet_map.get(name, []),
            "health": {
                "score": health.get("score", 0),
                "label": health.get("label", "unknown"),
            } if health else {"score": 0, "label": "unknown"},
            "sessions": {
                "total": sess.get("total_sessions", 0),
                "last_7d": sess.get("sessions_7d", 0),
                "last_1d": sess.get("sessions_1d", 0),
                "last_at": str(sess["last_session_at"]) if sess.get("last_session_at") else None,
                "total_tokens": (sess.get("total_input_tokens", 0) or 0) + (sess.get("total_output_tokens", 0) or 0),
            } if sess else {"total": 0, "last_7d": 0, "last_1d": 0, "last_at": None, "total_tokens": 0},
        })

    # Sort by most recent commit first, projects without commits go last
    project_rows.sort(
        key=lambda r: r["git"].get("commit_ts") or 0,
        reverse=True,
    )

    return {
        "projects": project_rows,
        "system": {
            "server_count": len(servers),
            "script_count": len(scripts),
            "claude_count": len(claude_procs),
            "droplet_count": len(droplets),
            "unlinked_servers": unlinked_servers,
            "unlinked_scripts": unlinked_scripts,
        },
        "feed": feed,
        "time": time_summary,
        "refreshed_at": datetime.now().isoformat(),
    }


async def _batch_loc(project_ids: list[int]) -> dict[int, list]:
    """Batch-fetch LOC snapshots for the last 3 days."""
    if not project_ids:
        return {}
    rows = await postgres.fetch(
        """SELECT project_id, date, lines_added, lines_removed, commit_count
           FROM loc_snapshots
           WHERE project_id = ANY($1) AND date >= CURRENT_DATE - 3
           ORDER BY date""",
        project_ids,
    )
    result: dict[int, list] = {}
    for r in rows:
        result.setdefault(r["project_id"], []).append({
            "date": str(r["date"]),
            "lines_added": r["lines_added"],
            "lines_removed": r["lines_removed"],
            "commit_count": r["commit_count"],
        })
    return result


async def _batch_tickets(project_ids: list[int]) -> dict[int, dict]:
    """Batch-fetch open ticket counts grouped by status."""
    if not project_ids:
        return {}
    rows = await postgres.fetch(
        """SELECT project_id, status, COUNT(*)::int as count
           FROM tickets
           WHERE project_id = ANY($1) AND status != 'done'
           GROUP BY project_id, status""",
        project_ids,
    )
    result: dict[int, dict] = {}
    for r in rows:
        result.setdefault(r["project_id"], {})[r["status"]] = r["count"]
    return result


async def _get_time_summary() -> dict:
    """Get today's time summary from SQLite."""
    try:
        db = await sqlite.get_db()
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0).timestamp()

        cursor = await db.execute(
            "SELECT * FROM activity_windows WHERE started_at >= ? ORDER BY started_at",
            (start_of_day,),
        )
        windows = [dict(r) for r in await cursor.fetchall()]

        project_time: dict[str, float] = {}
        for w in windows:
            proj = w.get("project") or "unknown"
            duration = (w.get("ended_at") or now.timestamp()) - w["started_at"]
            project_time[proj] = project_time.get(proj, 0) + duration

        return {
            "total_active_s": sum(project_time.values()),
            "project_time": project_time,
        }
    except Exception:
        return {"total_active_s": 0, "project_time": {}}
