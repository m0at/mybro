"""Lines-of-code tracking across git repos. Adapted from ~/tense/loc.py exclusion sets."""

import asyncio
import subprocess
from datetime import date, timedelta
from pathlib import Path

from backend.db import postgres

# Directories/files to exclude from LOC counts (from tense/loc.py)
EXCLUDED_DIRS = {
    "node_modules", ".next", ".turbo", ".vercel", "dist", "build", "out", "coverage",
    "venv", ".venv", "__pycache__", "site-packages", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".eggs", "target", ".git", ".hg", ".svn", ".idea",
    ".vscode", ".cache", ".gradle", ".terraform", ".direnv", "vendor", "deps",
    "Pods", "DerivedData",
}

EXCLUDED_EXTS = {".json", ".lock", ".sum", ".mod", ".min.js", ".min.css"}
EXCLUDED_FILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Cargo.lock", "poetry.lock", "Pipfile.lock",
}
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip", ".gz", ".tar"}


def _is_real_code(filepath: str) -> bool:
    """Check if a file path represents real code (not packages/generated)."""
    parts = Path(filepath).parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return False
    name = Path(filepath).name
    if name in EXCLUDED_FILES:
        return False
    ext = Path(filepath).suffix.lower()
    if ext in EXCLUDED_EXTS or ext in BINARY_EXTS:
        return False
    return True


async def get_git_stats(repo_path: str, days: int = 1) -> dict:
    """Get lines added/removed in a git repo over the last N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", repo_path, "log",
            f"--since={since}", "--numstat", "--diff-filter=ACDMR",
            "--format=", "--no-merges",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode("utf-8", errors="replace")
    except Exception:
        return {"added": 0, "removed": 0, "commits": 0}

    added = 0
    removed = 0
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add_str, rem_str, filepath = parts
        if add_str == "-" or rem_str == "-":
            continue  # binary
        if not _is_real_code(filepath):
            continue
        added += int(add_str)
        removed += int(rem_str)

    # Get commit count
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", repo_path, "rev-list",
            f"--since={since}", "--count", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        commits = int(stdout.decode().strip())
    except Exception:
        commits = 0

    return {"added": added, "removed": removed, "commits": commits}


async def snapshot_all_projects():
    """Take a LOC snapshot for all active projects for today."""
    projects = await postgres.fetch(
        "SELECT id, repo_path FROM projects WHERE status = 'active' AND repo_path IS NOT NULL"
    )
    today = date.today()
    results = []

    for p in projects:
        stats = await get_git_stats(p["repo_path"], days=1)
        await postgres.execute(
            """INSERT INTO loc_snapshots (project_id, date, lines_added, lines_removed, commit_count)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (project_id, date)
               DO UPDATE SET lines_added = $3, lines_removed = $4, commit_count = $5""",
            p["id"], today, stats["added"], stats["removed"], stats["commits"],
        )
        results.append({"project_id": p["id"], **stats})

    return results


async def get_loc_chart_data(project_id: int, days: int = 3) -> list[dict]:
    """Get LOC data for the last N days for sparkline chart."""
    rows = await postgres.fetch(
        """SELECT date, lines_added, lines_removed, commit_count
           FROM loc_snapshots
           WHERE project_id = $1 AND date >= CURRENT_DATE - $2::int
           ORDER BY date""",
        project_id, days,
    )
    return [dict(r) for r in rows]
