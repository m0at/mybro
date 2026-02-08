"""In-process background scheduler for periodic data collection."""

import asyncio
import logging
from datetime import datetime

from backend.services import session_scanner, repo_auditor, health_scorer, loc_counter

log = logging.getLogger("mybro.scheduler")

_task: asyncio.Task | None = None


async def _run_job(name: str, coro):
    """Run a job with logging and error handling."""
    start = datetime.now()
    try:
        result = await coro
        elapsed = (datetime.now() - start).total_seconds()
        log.info(f"[scheduler] {name} completed in {elapsed:.1f}s: {result}")
        return result
    except Exception as e:
        log.error(f"[scheduler] {name} failed: {e}")
        return None


async def _loop():
    """Main scheduler loop. Runs different jobs at different intervals."""
    # Wait for app startup to finish
    await asyncio.sleep(5)
    log.info("[scheduler] started")

    tick = 0
    while True:
        try:
            # Every 5 minutes: ingest new sessions + update health scores
            if tick % 300 == 0:
                await _run_job("session_scan", session_scanner.scan_all_sessions())
                await _run_job("health_scores", health_scorer.score_all_projects())

            # Every 30 minutes: repo audits
            if tick % 1800 == 0:
                await _run_job("repo_audit", repo_auditor.audit_all_projects())

            # Every 6 hours: LOC snapshots
            if tick % 21600 == 0 and tick > 0:
                await _run_job("loc_snapshot", loc_counter.snapshot_all_projects())

        except Exception as e:
            log.error(f"[scheduler] tick error: {e}")

        await asyncio.sleep(60)
        tick += 60


def start():
    """Start the scheduler as a background task."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        log.info("[scheduler] background task created")


def stop():
    """Cancel the scheduler task."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        log.info("[scheduler] stopped")
