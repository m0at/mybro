"""Live git queries per project — branch, last commit, uncommitted changes, remote URL."""

import asyncio
from datetime import datetime


async def _git(repo_path: str, *args: str, timeout: float = 3) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", repo_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


async def get_git_info(repo_path: str) -> dict:
    """Get git info for a single repo: branch, last commit, uncommitted count, remote URL."""
    log_out, branch_out, status_out, remote_out = await asyncio.gather(
        _git(repo_path, "log", "-1", "--format=%H%n%s%n%ct"),
        _git(repo_path, "branch", "--show-current"),
        _git(repo_path, "status", "--porcelain"),
        _git(repo_path, "remote", "get-url", "origin"),
    )

    # Parse log
    log_lines = log_out.split("\n") if log_out else []
    commit_hash = log_lines[0] if len(log_lines) > 0 else ""
    commit_message = log_lines[1] if len(log_lines) > 1 else ""
    commit_ts = None
    if len(log_lines) > 2 and log_lines[2].isdigit():
        commit_ts = int(log_lines[2])

    # Parse status
    uncommitted = len([l for l in status_out.split("\n") if l.strip()]) if status_out else 0

    # Parse remote — convert git@ to https
    github_url = remote_out or None
    if github_url and github_url.startswith("git@github.com:"):
        github_url = "https://github.com/" + github_url[15:].removesuffix(".git")
    elif github_url and github_url.endswith(".git"):
        github_url = github_url.removesuffix(".git")

    return {
        "branch": branch_out or "unknown",
        "commit_hash": commit_hash[:8],
        "commit_message": commit_message,
        "commit_ts": commit_ts,
        "uncommitted": uncommitted,
        "github_url": github_url,
    }


async def get_all_git_info(projects: list[dict]) -> dict[int, dict]:
    """Get git info for all projects in parallel. Returns {project_id: git_info}."""
    async def _fetch(p):
        if not p.get("repo_path"):
            return p["id"], {
                "branch": "", "commit_hash": "", "commit_message": "",
                "commit_ts": None, "uncommitted": 0, "github_url": None,
            }
        info = await get_git_info(p["repo_path"])
        return p["id"], info

    results = await asyncio.gather(*[_fetch(p) for p in projects])
    return dict(results)
