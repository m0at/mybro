"""Project management API — CRUD + auto-discover git repos."""

import os
import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import postgres

router = APIRouter(tags=["projects"])

HOME = Path.home()

# Directories to skip when scanning for repos
SKIP_DIRS = {
    ".Trash", "Library", "Applications", "Movies", "Music", "Pictures",
    "Public", "Downloads", ".local", ".cache", ".npm", ".cargo",
    "node_modules", ".venv", "venv", ".git",
}


class ProjectCreate(BaseModel):
    name: str
    repo_path: str | None = None
    github_url: str | None = None
    description: str | None = None
    color: str = "#3b82f6"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    color: str | None = None
    github_url: str | None = None


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _get_github_url(repo_path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Convert SSH URL to HTTPS
            if url.startswith("git@github.com:"):
                url = url.replace("git@github.com:", "https://github.com/")
            if url.endswith(".git"):
                url = url[:-4]
            return url
    except Exception:
        pass
    return None


@router.get("/projects")
async def list_projects():
    rows = await postgres.fetch(
        "SELECT * FROM projects ORDER BY status, name"
    )
    return {"projects": rows, "count": len(rows)}


@router.get("/projects/{project_id}")
async def get_project(project_id: int):
    row = await postgres.fetchrow("SELECT * FROM projects WHERE id = $1", project_id)
    if not row:
        raise HTTPException(404, "Project not found")
    return row


@router.post("/projects")
async def create_project(body: ProjectCreate):
    slug = _slugify(body.name)
    row = await postgres.fetchrow(
        """INSERT INTO projects (name, slug, repo_path, github_url, description, color)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
        body.name, slug, body.repo_path, body.github_url, body.description, body.color,
    )
    return row


@router.put("/projects/{project_id}")
async def update_project(project_id: int, body: ProjectUpdate):
    existing = await postgres.fetchrow("SELECT * FROM projects WHERE id = $1", project_id)
    if not existing:
        raise HTTPException(404, "Project not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return existing

    set_parts = [f"{k} = ${i+2}" for i, k in enumerate(updates)]
    set_parts.append(f"updated_at = NOW()")
    query = f"UPDATE projects SET {', '.join(set_parts)} WHERE id = $1 RETURNING *"
    row = await postgres.fetchrow(query, project_id, *updates.values())
    return row


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    result = await postgres.execute("DELETE FROM projects WHERE id = $1", project_id)
    if result == "DELETE 0":
        raise HTTPException(404, "Project not found")
    return {"deleted": project_id}


@router.post("/projects/discover")
async def discover_repos():
    """Scan home directory for git repos and register any new ones."""
    discovered = []
    for entry in sorted(HOME.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        git_dir = entry / ".git"
        if git_dir.is_dir():
            name = entry.name
            slug = _slugify(name)
            repo_path = str(entry)
            github_url = _get_github_url(repo_path)

            existing = await postgres.fetchrow(
                "SELECT id FROM projects WHERE slug = $1", slug
            )
            if existing:
                continue

            row = await postgres.fetchrow(
                """INSERT INTO projects (name, slug, repo_path, github_url, status)
                   VALUES ($1, $2, $3, $4, 'active') RETURNING *""",
                name, slug, repo_path, github_url,
            )
            discovered.append(row)

    return {"discovered": discovered, "count": len(discovered)}
