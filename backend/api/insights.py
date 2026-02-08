"""Insights API — sessions, audits, health scores, and manual triggers."""

from fastapi import APIRouter

from backend.services import session_scanner, repo_auditor, health_scorer

router = APIRouter(tags=["insights"])


@router.get("/insights/sessions/{project_id}")
async def get_sessions(project_id: int, limit: int = 20):
    """Get Claude sessions for a project."""
    sessions = await session_scanner.get_project_sessions(project_id, limit)
    return {"sessions": sessions}


@router.get("/insights/audit/{project_id}")
async def get_audit(project_id: int):
    """Get repo audit for a project."""
    audit = await repo_auditor.get_audit(project_id)
    return {"audit": audit}


@router.get("/insights/health")
async def get_health():
    """Get health scores for all projects."""
    health = await health_scorer.get_all_health()
    return {"health": health}


@router.post("/insights/scan-sessions")
async def trigger_session_scan():
    """Manually trigger a session scan."""
    stats = await session_scanner.scan_all_sessions()
    return stats


@router.post("/insights/audit-all")
async def trigger_audit():
    """Manually trigger repo audits for all projects."""
    results = await repo_auditor.audit_all_projects()
    return {"audited": len(results), "results": results}


@router.post("/insights/score-all")
async def trigger_scoring():
    """Manually trigger health scoring."""
    results = await health_scorer.score_all_projects()
    return {"scored": len(results), "results": results}
