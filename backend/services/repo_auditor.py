"""Audit repos — read key files (README, CLAUDE.md, TODO) and store summaries."""

import asyncio
from pathlib import Path

from backend.db import postgres

# Files to look for, in priority order
AUDIT_FILES = {
    "readme": ["README.md", "readme.md", "README"],
    "claude_md": ["CLAUDE.md", ".claude/CLAUDE.md"],
    "todo_md": ["TODO.md", "TODO", "todo.md"],
}

MAX_EXCERPT = 2000  # chars


def _read_file_safe(path: Path, max_bytes: int = 8000) -> str | None:
    """Read a file, return None if missing/error."""
    try:
        if not path.exists() or not path.is_file():
            return None
        text = path.read_text(errors="replace")[:max_bytes]
        return text.strip() if text.strip() else None
    except Exception:
        return None


def _scan_key_files(repo_path: str) -> dict:
    """Scan for notable files in a repo and return {filename: first_line}."""
    root = Path(repo_path)
    key_files = {}

    notable = [
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "Makefile", "Dockerfile", "docker-compose.yml",
        ".env.example", "requirements.txt", "tsconfig.json",
    ]

    for name in notable:
        p = root / name
        if p.exists() and p.is_file():
            try:
                first_line = p.read_text(errors="replace").split("\n")[0][:200]
                key_files[name] = first_line
            except Exception:
                key_files[name] = "(exists)"

    return key_files


async def audit_project(project_id: int, repo_path: str) -> dict:
    """Audit a single project's repo. Returns the audit data."""
    root = Path(repo_path)
    if not root.exists():
        return {"error": f"repo not found: {repo_path}"}

    # Read key markdown files
    readme = None
    for name in AUDIT_FILES["readme"]:
        readme = _read_file_safe(root / name)
        if readme:
            break

    claude_md = None
    for name in AUDIT_FILES["claude_md"]:
        claude_md = _read_file_safe(root / name)
        if claude_md:
            break

    todo_md = None
    for name in AUDIT_FILES["todo_md"]:
        todo_md = _read_file_safe(root / name)
        if todo_md:
            break

    key_files = _scan_key_files(repo_path)

    # Upsert
    await postgres.execute(
        """INSERT INTO repo_audits (project_id, readme_excerpt, claude_md, todo_md, key_files, last_scanned_at)
           VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
           ON CONFLICT (project_id) DO UPDATE SET
               readme_excerpt = $2, claude_md = $3, todo_md = $4,
               key_files = $5::jsonb, last_scanned_at = NOW()""",
        project_id,
        readme[:MAX_EXCERPT] if readme else None,
        claude_md[:MAX_EXCERPT] if claude_md else None,
        todo_md[:MAX_EXCERPT] if todo_md else None,
        __import__("json").dumps(key_files),
    )

    return {
        "project_id": project_id,
        "has_readme": readme is not None,
        "has_claude_md": claude_md is not None,
        "has_todo": todo_md is not None,
        "key_file_count": len(key_files),
    }


async def audit_all_projects() -> list[dict]:
    """Audit all active projects with repo paths."""
    projects = await postgres.fetch(
        "SELECT id, repo_path FROM projects WHERE status = 'active' AND repo_path IS NOT NULL"
    )
    results = []
    for p in projects:
        r = await audit_project(p["id"], p["repo_path"])
        results.append(r)
    return results


async def get_audit(project_id: int) -> dict | None:
    """Get the latest audit for a project."""
    return await postgres.fetchrow(
        "SELECT * FROM repo_audits WHERE project_id = $1", project_id
    )
