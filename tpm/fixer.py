"""TPM auto-fixer — attempts to fix detected issues via Claude Code CLI."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.config import config


@dataclass
class FixResult:
    project: str
    issue: str
    fixed: bool
    output: str
    duration_s: float
    md_path: str | None = None


async def attempt_fix(project_name: str, project_path: str, issue: str) -> FixResult:
    """Try to fix an issue using Claude Code CLI. Write .md on failure."""
    start = time.perf_counter()

    try:
        proc = await asyncio.create_subprocess_exec(
            config.tpm.claude_cli_path,
            "--dangerously-skip-permissions",
            "-p", f"Fix this issue in the project: {issue}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=project_path,
            env={
                **__import__("os").environ,
                "TERM": "dumb",
                "NO_COLOR": "1",
            },
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), timeout=config.tpm.max_fix_timeout_s
        )
        output = stdout.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0

        duration = time.perf_counter() - start

        if exit_code == 0:
            return FixResult(
                project=project_name, issue=issue, fixed=True,
                output=output[-2000:], duration_s=duration,
            )
    except asyncio.TimeoutError:
        output = "[TIMEOUT]"
        duration = time.perf_counter() - start
    except Exception as e:
        output = f"[ERROR: {e}]"
        duration = time.perf_counter() - start

    # Write .md with the problem description
    md_path = _write_issue_md(project_path, project_name, issue, output)

    return FixResult(
        project=project_name, issue=issue, fixed=False,
        output=output[-2000:], duration_s=duration, md_path=md_path,
    )


def _write_issue_md(project_path: str, project_name: str, issue: str, output: str) -> str:
    """Write an .md file documenting an unfixed issue."""
    issues_dir = Path(project_path) / ".mybro-issues"
    issues_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"issue-{timestamp}.md"
    filepath = issues_dir / filename

    content = f"""# Issue: {issue}

**Project:** {project_name}
**Detected:** {datetime.now().isoformat()}
**Auto-fix:** Failed

## TPM Output

```
{output[-3000:]}
```

## Next Steps

- [ ] Review this issue manually
- [ ] Fix and close
"""
    filepath.write_text(content)
    return str(filepath)
