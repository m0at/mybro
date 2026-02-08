"""TPM reporter — generates status updates and date shift proposals."""

import json
from datetime import datetime

import httpx

MYBRO_API = "http://127.0.0.1:9000"


async def _api_post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{MYBRO_API}{path}", json=data)
        return r.json()


async def generate_report(collected: dict, fix_results: list) -> dict:
    """Generate the TPM report and post status updates."""
    tickets = collected["tickets"]
    git = collected["git_status"]
    system = collected["system"]

    # Build summary
    parts = []
    parts.append(f"Tickets: {tickets['total']} total, {tickets['by_status']}")

    if tickets["overdue"]:
        names = [f"#{t['id']} {t['title']}" for t in tickets["overdue"][:5]]
        parts.append(f"Overdue: {', '.join(names)}")

    if tickets["stale_in_progress"]:
        names = [f"#{t['id']} {t['title']}" for t in tickets["stale_in_progress"][:5]]
        parts.append(f"Stale (>2d in_progress): {', '.join(names)}")

    if git:
        uncommitted = [f"{g['project']} ({g['uncommitted_files']} files)" for g in git[:5]]
        parts.append(f"Uncommitted changes: {', '.join(uncommitted)}")

    servers = system.get("servers", [])
    droplets = system.get("droplets", [])
    parts.append(f"Running: {len(servers)} servers, {len(droplets)} droplets")

    if fix_results:
        fixed = [r for r in fix_results if r.fixed]
        failed = [r for r in fix_results if not r.fixed]
        if fixed:
            parts.append(f"Auto-fixed: {', '.join(r.project + ': ' + r.issue for r in fixed)}")
        if failed:
            parts.append(f"Needs attention: {', '.join(r.project + ': ' + r.issue for r in failed)}")

    summary = " | ".join(parts)

    # Post to status feed
    update_type = "blocker" if tickets["overdue"] or tickets["stale_in_progress"] else "progress"
    await _api_post("/api/feed", {
        "content": summary,
        "author": "tpm",
        "update_type": update_type,
    })

    # Store full report
    report = {
        "timestamp": collected["timestamp"],
        "summary": summary,
        "tickets": tickets,
        "git_status": git,
        "system_servers": len(servers),
        "system_droplets": len(droplets),
        "fixes_attempted": len(fix_results),
        "fixes_succeeded": len([r for r in fix_results if r.fixed]),
    }

    # Save to tpm_reports table
    reminders = {}
    if tickets["overdue"]:
        reminders["overdue_tickets"] = [
            {"id": t["id"], "title": t["title"], "due_date": str(t.get("due_date"))}
            for t in tickets["overdue"]
        ]
    if tickets["stale_in_progress"]:
        reminders["stale_tickets"] = [
            {"id": t["id"], "title": t["title"]}
            for t in tickets["stale_in_progress"]
        ]

    await _api_post("/api/feed", {
        "content": f"TPM hourly report: {summary}",
        "author": "tpm",
        "update_type": "reminder" if reminders else "progress",
    })

    return {
        "report": report,
        "reminders": reminders,
        "issues_found": len(tickets.get("overdue", [])) + len(tickets.get("stale_in_progress", [])) + len(git),
        "issues_fixed": len([r for r in fix_results if r.fixed]),
    }
