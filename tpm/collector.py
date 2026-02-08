"""TPM status collector — gathers data from all sources."""

import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import httpx

MYBRO_API = "http://127.0.0.1:9000"
HOME = Path.home()


async def _api_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{MYBRO_API}{path}")
        return r.json()


async def collect_tickets() -> dict:
    """Get ticket status summary."""
    data = await _api_get("/api/tickets?limit=500")
    tickets = data.get("tickets", [])

    by_status = {}
    overdue = []
    stale = []
    now = datetime.now().astimezone()

    for t in tickets:
        status = t["status"]
        by_status[status] = by_status.get(status, 0) + 1

        if t.get("due_date") and t["status"] not in ("done", "cancelled"):
            due = datetime.fromisoformat(t["due_date"]).astimezone() if "T" in str(t["due_date"]) else datetime.strptime(str(t["due_date"]), "%Y-%m-%d").astimezone()
            if due < now:
                overdue.append(t)

        if t["status"] == "in_progress":
            updated = datetime.fromisoformat(t["updated_at"])
            if (now - updated).days > 2:
                stale.append(t)

    return {
        "total": len(tickets),
        "by_status": by_status,
        "overdue": overdue,
        "stale_in_progress": stale,
    }


async def collect_git_status() -> list[dict]:
    """Check git status across all repos."""
    data = await _api_get("/api/projects")
    projects = data.get("projects", [])
    results = []

    for p in projects:
        path = p.get("repo_path")
        if not path or not Path(path).exists():
            continue

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", path, "status", "--porcelain",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            changes = stdout.decode().strip()
            if changes:
                file_count = len(changes.split("\n"))
                results.append({
                    "project": p["name"],
                    "uncommitted_files": file_count,
                    "path": path,
                })
        except Exception:
            pass

    return results


async def collect_system_health() -> dict:
    """Get system overview from mybro API."""
    try:
        return await _api_get("/api/system/overview")
    except Exception:
        return {"servers": [], "scripts": [], "droplets": []}


async def collect_all() -> dict:
    """Gather everything for the TPM report."""
    tickets, git, system = await asyncio.gather(
        collect_tickets(),
        collect_git_status(),
        collect_system_health(),
    )

    return {
        "timestamp": datetime.now().isoformat(),
        "tickets": tickets,
        "git_status": git,
        "system": system,
    }
