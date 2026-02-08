"""Status feed API — blog-style project updates."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.db import postgres

router = APIRouter(tags=["feed"])


class StatusUpdateCreate(BaseModel):
    project_id: int | None = None
    ticket_id: int | None = None
    content: str
    author: str = "user"
    update_type: str = "progress"


@router.get("/feed")
async def get_feed(
    project_id: int | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    conditions = ["1=1"]
    params = []
    idx = 1

    if project_id is not None:
        conditions.append(f"s.project_id = ${idx}")
        params.append(project_id)
        idx += 1

    where = " AND ".join(conditions)
    rows = await postgres.fetch(
        f"""SELECT s.*, p.name as project_name, p.color as project_color
            FROM status_updates s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE {where}
            ORDER BY s.created_at DESC
            LIMIT ${idx} OFFSET ${idx+1}""",
        *params, limit, offset,
    )
    return {"updates": rows, "count": len(rows)}


@router.post("/feed")
async def create_update(body: StatusUpdateCreate):
    row = await postgres.fetchrow(
        """INSERT INTO status_updates (project_id, ticket_id, content, author, update_type)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        body.project_id, body.ticket_id, body.content, body.author, body.update_type,
    )
    return row
