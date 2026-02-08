"""Ingest Claude Code session data from ~/.claude/projects/ into PG."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from backend.db import postgres

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _dir_to_project_path(dirname: str) -> str:
    """Convert claude's dir naming back to a path. '-Users-andy-foo' → '/Users/andy/foo'."""
    # Leading dash represents root /
    if dirname.startswith("-"):
        return "/" + dirname[1:].replace("-", "/")
    return dirname.replace("-", "/")


def _parse_jsonl_quick(filepath: Path) -> dict:
    """Parse first and last lines of a JSONL transcript for metadata."""
    result = {
        "first_prompt": None,
        "message_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "model": None,
        "git_branch": None,
        "started_at": None,
        "ended_at": None,
    }

    try:
        size = filepath.stat().st_size
        if size == 0:
            return result

        lines = []
        with open(filepath, "r", errors="replace") as f:
            # Read first 20 lines to find first user prompt and metadata
            for i, line in enumerate(f):
                if i >= 20:
                    break
                line = line.strip()
                if line:
                    lines.append(line)

        # Read last few lines for end timestamp
        last_lines = []
        with open(filepath, "rb") as f:
            # Seek to near end
            seek_pos = max(0, size - 50000)
            f.seek(seek_pos)
            tail = f.read().decode("utf-8", errors="replace")
            for line in tail.strip().split("\n"):
                line = line.strip()
                if line:
                    last_lines.append(line)
            last_lines = last_lines[-5:]

        msg_count = 0
        total_input = 0
        total_output = 0
        total_cache = 0

        # Parse opening lines
        for line in lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_count += 1

            ts = rec.get("timestamp")
            if ts and not result["started_at"]:
                result["started_at"] = ts

            if not result["git_branch"] and rec.get("gitBranch"):
                result["git_branch"] = rec["gitBranch"]

            # First user message content = first prompt
            if rec.get("type") == "user" and not result["first_prompt"]:
                msg = rec.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    result["first_prompt"] = content[:500]
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            result["first_prompt"] = block["text"][:500]
                            break

            # Token usage from assistant messages
            if rec.get("type") == "assistant":
                msg = rec.get("message", {})
                if not result["model"] and msg.get("model"):
                    result["model"] = msg["model"]
                usage = msg.get("usage", {})
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                total_cache += usage.get("cache_read_input_tokens", 0)

        # Parse last lines for end timestamp + more tokens
        for line in last_lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = rec.get("timestamp")
            if ts:
                result["ended_at"] = ts
            if rec.get("type") == "assistant":
                msg = rec.get("message", {})
                usage = msg.get("usage", {})
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                total_cache += usage.get("cache_read_input_tokens", 0)

        # For accurate message count, count lines in file (fast for most files)
        if size < 10_000_000:  # < 10MB, count all lines
            with open(filepath, "r", errors="replace") as f:
                msg_count = sum(1 for line in f if line.strip())

        result["message_count"] = msg_count
        result["input_tokens"] = total_input
        result["output_tokens"] = total_output
        result["cache_read_tokens"] = total_cache

    except Exception:
        pass

    return result


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


async def scan_all_sessions() -> dict:
    """Scan all Claude session data and ingest into PG. Returns stats."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return {"error": "~/.claude/projects/ not found"}

    # Load existing projects for mapping
    projects = await postgres.fetch("SELECT id, name, repo_path FROM projects")
    path_to_project: dict[str, int] = {}
    for p in projects:
        if p["repo_path"]:
            path_to_project[p["repo_path"]] = p["id"]

    # Get already-ingested session IDs
    existing = await postgres.fetch("SELECT session_id FROM claude_sessions")
    existing_ids = {r["session_id"] for r in existing}

    stats = {"scanned": 0, "new": 0, "skipped": 0, "errors": 0}

    for proj_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue

        project_path = _dir_to_project_path(proj_dir.name)
        project_id = path_to_project.get(project_path)

        # Try sessions-index.json first (fast path)
        index_file = proj_dir / "sessions-index.json"
        indexed_sessions = set()

        if index_file.exists():
            try:
                with open(index_file) as f:
                    index_data = json.load(f)
                for entry in index_data.get("entries", []):
                    sid = entry.get("sessionId", "")
                    if not sid or sid in existing_ids:
                        stats["skipped"] += 1
                        indexed_sessions.add(sid)
                        continue

                    stats["scanned"] += 1
                    indexed_sessions.add(sid)

                    started = _parse_iso(entry.get("created"))
                    ended = _parse_iso(entry.get("modified"))
                    duration = int((ended - started).total_seconds()) if started and ended else 0

                    # Get file size
                    jsonl_path = proj_dir / f"{sid}.jsonl"
                    file_size = jsonl_path.stat().st_size if jsonl_path.exists() else 0

                    # Parse JSONL for token data (index doesn't have it)
                    token_data = {}
                    if jsonl_path.exists():
                        token_data = _parse_jsonl_quick(jsonl_path)

                    await postgres.execute(
                        """INSERT INTO claude_sessions
                           (project_id, session_id, first_prompt, summary, message_count,
                            input_tokens, output_tokens, cache_read_tokens, model,
                            git_branch, started_at, ended_at, duration_s, file_size_bytes)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                           ON CONFLICT (session_id) DO NOTHING""",
                        project_id, sid,
                        entry.get("firstPrompt", token_data.get("first_prompt")),
                        entry.get("summary"),
                        entry.get("messageCount", token_data.get("message_count", 0)),
                        token_data.get("input_tokens", 0),
                        token_data.get("output_tokens", 0),
                        token_data.get("cache_read_tokens", 0),
                        token_data.get("model"),
                        entry.get("gitBranch", token_data.get("git_branch")),
                        started, ended, duration, file_size,
                    )
                    stats["new"] += 1

            except Exception:
                stats["errors"] += 1

        # Scan JSONL files not covered by index
        for jsonl_file in proj_dir.glob("*.jsonl"):
            sid = jsonl_file.stem
            if not UUID_RE.match(sid):
                continue  # Skip agent-*.jsonl files
            if sid in existing_ids or sid in indexed_sessions:
                stats["skipped"] += 1
                continue

            stats["scanned"] += 1
            try:
                meta = _parse_jsonl_quick(jsonl_file)
                started = _parse_iso(meta["started_at"])
                ended = _parse_iso(meta["ended_at"])
                duration = int((ended - started).total_seconds()) if started and ended else 0

                await postgres.execute(
                    """INSERT INTO claude_sessions
                       (project_id, session_id, first_prompt, summary, message_count,
                        input_tokens, output_tokens, cache_read_tokens, model,
                        git_branch, started_at, ended_at, duration_s, file_size_bytes)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                       ON CONFLICT (session_id) DO NOTHING""",
                    project_id, sid,
                    meta["first_prompt"], None,
                    meta["message_count"],
                    meta["input_tokens"], meta["output_tokens"], meta["cache_read_tokens"],
                    meta["model"], meta["git_branch"],
                    started, ended, duration,
                    jsonl_file.stat().st_size,
                )
                stats["new"] += 1
            except Exception:
                stats["errors"] += 1

    return stats


async def get_project_sessions(project_id: int, limit: int = 20) -> list[dict]:
    """Get recent sessions for a project."""
    return await postgres.fetch(
        """SELECT session_id, first_prompt, summary, message_count,
                  input_tokens, output_tokens, model, git_branch,
                  started_at, ended_at, duration_s, file_size_bytes
           FROM claude_sessions
           WHERE project_id = $1
           ORDER BY started_at DESC NULLS LAST
           LIMIT $2""",
        project_id, limit,
    )


async def get_session_stats() -> dict:
    """Get aggregate session stats for all projects."""
    rows = await postgres.fetch(
        """SELECT project_id,
                  COUNT(*) as total_sessions,
                  COUNT(*) FILTER (WHERE started_at > NOW() - INTERVAL '7 days') as sessions_7d,
                  COUNT(*) FILTER (WHERE started_at > NOW() - INTERVAL '1 day') as sessions_1d,
                  SUM(input_tokens) as total_input_tokens,
                  SUM(output_tokens) as total_output_tokens,
                  MAX(started_at) as last_session_at,
                  SUM(duration_s) as total_duration_s
           FROM claude_sessions
           WHERE project_id IS NOT NULL
           GROUP BY project_id"""
    )
    return {r["project_id"]: dict(r) for r in rows}
