"""Detect running servers, scripts, and background processes. Adapted from cch syswatch.py."""

import asyncio
import re
from pathlib import Path

HOME = str(Path.home())


async def _run(cmd: str, timeout: int = 10) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return stdout.decode("utf-8", errors="replace")


def _project_from_path(path: str) -> str | None:
    """Extract project name from a path under HOME."""
    if path.startswith(HOME):
        rel = path[len(HOME):].strip("/")
        return rel.split("/")[0] if rel else None
    return None


async def _get_cwd_map(pids: list[str]) -> dict[str, str]:
    """Batch-fetch working directories for a list of PIDs using a single lsof call."""
    if not pids:
        return {}
    pid_str = ",".join(pids)
    try:
        output = await _run(f"lsof -a -d cwd -Fpn -p {pid_str} 2>/dev/null", timeout=5)
    except Exception:
        return {}

    cwd_map = {}
    current_pid = None
    for line in output.strip().split("\n"):
        if line.startswith("p"):
            current_pid = line[1:]
        elif line.startswith("n") and current_pid:
            cwd_map[current_pid] = line[1:]
    return cwd_map


async def get_listening_servers() -> list[dict]:
    """Find processes listening on TCP ports, mapped to project dirs."""
    try:
        output = await _run("lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null")
    except Exception:
        return []

    # First pass: collect unique ports and their PIDs
    port_info = {}
    for line in output.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) < 9:
            continue
        command = parts[0]
        pid = parts[1]
        name_col = parts[8]

        port_match = re.search(r":(\d+)$", name_col)
        if not port_match:
            continue
        port = int(port_match.group(1))
        if port in port_info:
            continue
        port_info[port] = {"command": command, "pid": pid}

    # Batch-fetch CWDs for all PIDs
    all_pids = list({v["pid"] for v in port_info.values()})
    cwd_map = await _get_cwd_map(all_pids)

    servers = []
    for port, info in sorted(port_info.items()):
        pid = info["pid"]
        command = info["command"]
        cwd = cwd_map.get(pid, "")
        project = _project_from_path(cwd)

        stype = "unknown"
        if command in ("node", "npm", "npx", "next-server"):
            stype = "frontend" if port in (3000, 3001, 5173, 5174, 9001) else "backend"
        elif command in ("python", "python3", "uvicorn", "gunicorn", "Python"):
            stype = "backend"

        servers.append({
            "pid": int(pid),
            "command": command,
            "port": port,
            "project": project,
            "type": stype,
        })

    return servers


async def get_running_scripts() -> list[dict]:
    """Find running Python/Node scripts and simulations."""
    try:
        output = await _run(
            "ps aux | grep -E '(python|node|cargo run)' | grep -v grep | grep -v 'uvicorn backend'"
        )
    except Exception:
        return []

    scripts = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        pid = parts[1]
        cpu = parts[2]
        mem = parts[3]
        cmd = parts[10]

        if HOME not in cmd and not cmd.startswith("python") and not cmd.startswith("node"):
            continue

        project = None
        for token in cmd.split():
            if token.startswith(HOME):
                project = _project_from_path(token)
                break

        scripts.append({
            "pid": int(pid),
            "command": cmd[:120],
            "cpu_percent": float(cpu),
            "mem_percent": float(mem),
            "project": project,
        })

    return scripts


async def get_claude_processes() -> list[dict]:
    """Find running Claude Code instances, mapped to project directories."""
    try:
        output = await _run("ps aux | grep '[c]laude' | grep -v grep")
    except Exception:
        return []

    procs = []
    pids = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        pid = parts[1]
        pids.append(pid)
        procs.append({
            "pid": int(pid),
            "cpu_percent": float(parts[2]),
            "command": parts[10][:120],
            "project": None,
        })

    # Batch-fetch CWDs and map to projects
    cwd_map = await _get_cwd_map(pids)
    for p in procs:
        cwd = cwd_map.get(str(p["pid"]), "")
        p["project"] = _project_from_path(cwd)

    return procs
