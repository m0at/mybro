"""Compute per-project health scores from commit velocity, sessions, tickets, processes."""

import json
from datetime import datetime, timezone

from backend.db import postgres
from backend.services import session_scanner, git_info, process_scanner


async def score_all_projects() -> list[dict]:
    """Compute and store health scores for all active projects."""
    projects = await postgres.fetch(
        "SELECT id, name, repo_path FROM projects WHERE status = 'active'"
    )
    project_ids = [p["id"] for p in projects]

    # Gather data in parallel-ish batches
    session_stats = await session_scanner.get_session_stats()

    # Commit velocity: LOC snapshots last 7 days
    loc_rows = await postgres.fetch(
        """SELECT project_id, SUM(commit_count) as commits_7d
           FROM loc_snapshots
           WHERE project_id = ANY($1) AND date >= CURRENT_DATE - 7
           GROUP BY project_id""",
        project_ids,
    )
    commit_velocity = {r["project_id"]: r["commits_7d"] or 0 for r in loc_rows}

    # Open tickets per project
    ticket_rows = await postgres.fetch(
        """SELECT project_id, COUNT(*) as open_count
           FROM tickets
           WHERE project_id = ANY($1) AND status NOT IN ('done', 'cancelled')
           GROUP BY project_id""",
        project_ids,
    )
    open_tickets = {r["project_id"]: r["open_count"] for r in ticket_rows}

    # Git info for last commit timestamps
    git_map = await git_info.get_all_git_info(projects)

    # Running processes
    servers = await process_scanner.get_listening_servers()
    claude_procs = await process_scanner.get_claude_processes()
    server_projects = {s["project"] for s in servers if s.get("project")}
    claude_projects = {c["project"] for c in claude_procs if c.get("project")}

    results = []
    now = datetime.now(timezone.utc)

    for p in projects:
        pid = p["id"]
        name = p["name"]

        git = git_map.get(pid, {})
        sess = session_stats.get(pid, {})
        commits_7d = commit_velocity.get(pid, 0)
        tickets = open_tickets.get(pid, 0)
        has_server = name in server_projects
        has_claude = name in claude_projects

        last_commit_ts = git.get("commit_ts")
        last_session_at = sess.get("last_session_at")
        sessions_7d = sess.get("sessions_7d", 0)

        # Scoring (0-100)
        score = 0

        # Commit recency (0-30 pts)
        if last_commit_ts:
            age_hours = (now.timestamp() - last_commit_ts) / 3600
            if age_hours < 1:
                score += 30
            elif age_hours < 24:
                score += 25
            elif age_hours < 72:
                score += 15
            elif age_hours < 168:
                score += 8
            else:
                score += 2

        # Commit velocity (0-20 pts)
        if commits_7d >= 20:
            score += 20
        elif commits_7d >= 10:
            score += 15
        elif commits_7d >= 3:
            score += 10
        elif commits_7d >= 1:
            score += 5

        # Session activity (0-20 pts)
        if sessions_7d >= 5:
            score += 20
        elif sessions_7d >= 3:
            score += 15
        elif sessions_7d >= 1:
            score += 10

        # Running infra (0-15 pts)
        if has_server:
            score += 10
        if has_claude:
            score += 5

        # Tickets signal work (0-15 pts)
        if tickets >= 5:
            score += 15
        elif tickets >= 2:
            score += 10
        elif tickets >= 1:
            score += 5

        # Label
        if score >= 60:
            label = "hot"
        elif score >= 35:
            label = "active"
        elif score >= 15:
            label = "stale"
        else:
            label = "dead"

        last_commit_at = None
        if last_commit_ts:
            last_commit_at = datetime.fromtimestamp(last_commit_ts, tz=timezone.utc)

        await postgres.execute(
            """INSERT INTO project_health
               (project_id, score, label, commit_velocity_7d, session_count_7d,
                last_session_at, last_commit_at, open_tickets, has_server, has_claude,
                details, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,NOW())
               ON CONFLICT (project_id) DO UPDATE SET
                   score=$2, label=$3, commit_velocity_7d=$4, session_count_7d=$5,
                   last_session_at=$6, last_commit_at=$7, open_tickets=$8,
                   has_server=$9, has_claude=$10, details=$11::jsonb, updated_at=NOW()""",
            pid, score, label, commits_7d, sessions_7d,
            last_session_at, last_commit_at, tickets, has_server, has_claude,
            json.dumps({
                "total_sessions": sess.get("total_sessions", 0),
                "total_tokens": (sess.get("total_input_tokens", 0) or 0) + (sess.get("total_output_tokens", 0) or 0),
                "uncommitted_files": git.get("uncommitted", 0),
            }),
        )

        results.append({
            "project_id": pid,
            "name": name,
            "score": score,
            "label": label,
        })

    return sorted(results, key=lambda r: r["score"], reverse=True)


async def get_all_health() -> dict[int, dict]:
    """Get current health scores for all projects."""
    rows = await postgres.fetch(
        "SELECT * FROM project_health ORDER BY score DESC"
    )
    return {r["project_id"]: dict(r) for r in rows}
