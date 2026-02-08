"""TPM agent — hourly one-shot: collect, analyze, fix, report."""

import asyncio
import json
import sys
from datetime import datetime

import httpx

from tpm.collector import collect_all
from tpm.fixer import attempt_fix
from tpm.reporter import generate_report

MYBRO_API = "http://127.0.0.1:9000"


async def ensure_server():
    """Check if mybro backend is running."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{MYBRO_API}/")
            return r.status_code == 200
    except Exception:
        return False


async def store_report(report_data: dict):
    """Store the TPM report in the database."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Use a direct DB call would be better, but for simplicity we'll post to feed
            pass
    except Exception:
        pass


async def run_tpm():
    print(f"[TPM] Starting hourly run at {datetime.now().isoformat()}")

    # Check server is up
    if not await ensure_server():
        print("[TPM] mybro server not running, skipping this run")
        return

    # 1. Collect status from all sources
    print("[TPM] Collecting status...")
    collected = await collect_all()
    print(f"[TPM] Tickets: {collected['tickets']['total']}, "
          f"Uncommitted repos: {len(collected['git_status'])}, "
          f"Servers: {len(collected['system'].get('servers', []))}")

    # 2. Attempt fixes for stale tickets (optional, conservative)
    fix_results = []
    # Only auto-fix if there are stale in-progress tickets
    # For now, just report — auto-fixing requires more calibration
    stale = collected["tickets"].get("stale_in_progress", [])
    if stale:
        print(f"[TPM] Found {len(stale)} stale tickets, logging for review")
        # In future: attempt_fix for each, currently just report

    # 3. Generate and post report
    print("[TPM] Generating report...")
    report = await generate_report(collected, fix_results)
    print(f"[TPM] Report: {report['issues_found']} issues found, "
          f"{report['issues_fixed']} fixed")

    if report["reminders"]:
        print(f"[TPM] Reminders: {json.dumps(report['reminders'], indent=2)}")

    print(f"[TPM] Run complete at {datetime.now().isoformat()}")


def main():
    asyncio.run(run_tpm())


if __name__ == "__main__":
    main()
