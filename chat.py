#!/usr/bin/env python3
"""
mybro chat — interactive terminal chat with a Claude Code instance.
Points claude at /Users/andy/cch as a resource for proven patterns.
Can create/update tickets via the mybro API.
"""

import json
import subprocess
import sys

import httpx

MYBRO_API = "http://127.0.0.1:9000"
CCH_PATH = "/Users/andy/cch"

SYSTEM_CONTEXT = f"""You are mybro's assistant, a project manager for Andy's development work.
You have access to the codebase reference at {CCH_PATH} which contains production-tested
templates and patterns for Apple Silicon Mac development.

When Andy asks you to create a ticket, call the mybro API:
  POST {MYBRO_API}/api/tickets
  Body: {{"project_id": <int>, "title": "<title>", "description": "<desc>", "priority": "<low|medium|high|urgent>", "created_by": "agent"}}

When Andy asks about projects, query:
  GET {MYBRO_API}/api/projects

When Andy asks about existing tickets:
  GET {MYBRO_API}/api/tickets

Always reference {CCH_PATH} for established patterns when suggesting implementations.
You can read files from {CCH_PATH} to find proven code patterns.
"""


def ensure_server():
    """Check if mybro backend is running."""
    try:
        r = httpx.get(f"{MYBRO_API}/", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def get_projects_summary() -> str:
    """Fetch projects for context."""
    try:
        r = httpx.get(f"{MYBRO_API}/api/projects", timeout=5)
        data = r.json()
        lines = []
        for p in data.get("projects", []):
            lines.append(f"  [{p['id']}] {p['name']} ({p['status']}) — {p['repo_path']}")
        return "\n".join(lines) if lines else "  No projects found."
    except Exception:
        return "  (could not reach mybro API)"


def get_tickets_summary() -> str:
    """Fetch open tickets for context."""
    try:
        r = httpx.get(f"{MYBRO_API}/api/tickets?limit=20", timeout=5)
        data = r.json()
        lines = []
        for t in data.get("tickets", []):
            lines.append(
                f"  [{t['id']}] [{t['status']}] [{t['priority']}] "
                f"{t['title']} (project: {t.get('project_name', '?')})"
            )
        return "\n".join(lines) if lines else "  No open tickets."
    except Exception:
        return "  (could not reach mybro API)"


def build_prompt(user_input: str) -> str:
    """Build the full prompt with mybro context."""
    projects = get_projects_summary()
    tickets = get_tickets_summary()

    return f"""{SYSTEM_CONTEXT}

Current projects:
{projects}

Current tickets:
{tickets}

User request: {user_input}"""


def run_claude(prompt: str):
    """Run claude CLI with the given prompt, streaming output."""
    args = [
        "claude",
        "-p", prompt,
        "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch",
    ]

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=CCH_PATH,
        env={
            **__import__("os").environ,
            "TERM": "dumb",
            "NO_COLOR": "1",
        },
    )

    output_lines = []
    for line in proc.stdout:
        print(line, end="")
        output_lines.append(line)

    proc.wait()
    return "".join(output_lines), proc.returncode


def main():
    print("=" * 60)
    print("  mybro chat")
    print("  Claude Code instance pointed at /cch")
    print("  Type 'quit' to exit, 'projects' to list projects,")
    print("  'tickets' to list tickets")
    print("=" * 60)

    server_ok = ensure_server()
    if server_ok:
        print("\n  mybro API: connected (localhost:9000)")
    else:
        print("\n  mybro API: offline — start with:")
        print("    cd ~/mybro && source .venv/bin/activate")
        print("    python -m uvicorn backend.main:app --port 9000")

    print()

    while True:
        try:
            user_input = input("\033[1;36mmybro>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("bye")
            break

        if user_input.lower() == "projects":
            print(get_projects_summary())
            continue

        if user_input.lower() == "tickets":
            print(get_tickets_summary())
            continue

        # Quick ticket creation shortcut
        if user_input.lower().startswith("ticket:"):
            parts = user_input[7:].strip()
            if not server_ok:
                print("  mybro API is offline, can't create ticket")
                continue
            # Parse "ticket: project_name | title | priority"
            segs = [s.strip() for s in parts.split("|")]
            if len(segs) < 2:
                print("  Usage: ticket: project_name | title | priority")
                continue
            project_name = segs[0]
            title = segs[1]
            priority = segs[2] if len(segs) > 2 else "medium"

            # Find project ID
            try:
                r = httpx.get(f"{MYBRO_API}/api/projects", timeout=5)
                projects = r.json().get("projects", [])
                match = next((p for p in projects if p["name"].lower() == project_name.lower()), None)
                if not match:
                    print(f"  Project '{project_name}' not found")
                    continue
                r = httpx.post(
                    f"{MYBRO_API}/api/tickets",
                    json={
                        "project_id": match["id"],
                        "title": title,
                        "priority": priority,
                        "created_by": "user",
                    },
                    timeout=5,
                )
                t = r.json()
                print(f"  Created ticket #{t['id']}: {t['title']} [{t['priority']}]")
            except Exception as e:
                print(f"  Error: {e}")
            continue

        # Send to Claude Code
        prompt = build_prompt(user_input)
        print("\n--- claude ---")
        output, code = run_claude(prompt)
        print("--- end ---\n")


if __name__ == "__main__":
    main()
