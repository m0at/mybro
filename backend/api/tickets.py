"""Ticketing API — Linear-like CRUD with events."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.db import postgres

router = APIRouter(tags=["tickets"])


class TicketCreate(BaseModel):
    project_id: int
    title: str
    description: str | None = None
    status: str = "backlog"
    priority: str = "medium"
    labels: list[str] = []
    assignee: str = "andy"
    due_date: str | None = None
    estimated_hours: float | None = None
    parent_id: int | None = None
    created_by: str = "user"


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    assignee: str | None = None
    due_date: str | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None
    sort_order: int | None = None


class EventCreate(BaseModel):
    content: str
    author: str = "user"


@router.get("/tickets")
async def list_tickets(
    project_id: int | None = None,
    status: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    conditions = ["1=1"]
    params = []
    idx = 1

    if project_id is not None:
        conditions.append(f"t.project_id = ${idx}")
        params.append(project_id)
        idx += 1
    if status:
        conditions.append(f"t.status = ${idx}")
        params.append(status)
        idx += 1
    if assignee:
        conditions.append(f"t.assignee = ${idx}")
        params.append(assignee)
        idx += 1
    if priority:
        conditions.append(f"t.priority = ${idx}")
        params.append(priority)
        idx += 1

    where = " AND ".join(conditions)
    query = f"""
        SELECT t.*, p.name as project_name, p.color as project_color
        FROM tickets t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE {where}
        ORDER BY t.sort_order, t.created_at DESC
        LIMIT ${idx} OFFSET ${idx+1}
    """
    params.extend([limit, offset])

    rows = await postgres.fetch(query, *params)
    total = await postgres.fetchval(
        f"SELECT COUNT(*) FROM tickets t WHERE {where}", *params[:-2]
    )
    return {"tickets": rows, "total": total}


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    row = await postgres.fetchrow(
        """SELECT t.*, p.name as project_name, p.color as project_color
           FROM tickets t
           LEFT JOIN projects p ON t.project_id = p.id
           WHERE t.id = $1""",
        ticket_id,
    )
    if not row:
        raise HTTPException(404, "Ticket not found")

    events = await postgres.fetch(
        "SELECT * FROM ticket_events WHERE ticket_id = $1 ORDER BY created_at",
        ticket_id,
    )
    return {**row, "events": events}


@router.post("/tickets")
async def create_ticket(body: TicketCreate):
    row = await postgres.fetchrow(
        """INSERT INTO tickets
           (project_id, title, description, status, priority, labels,
            assignee, due_date, estimated_hours, parent_id, created_by)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8::date,$9,$10,$11) RETURNING *""",
        body.project_id, body.title, body.description, body.status,
        body.priority, body.labels, body.assignee,
        body.due_date, body.estimated_hours, body.parent_id, body.created_by,
    )

    # Log creation event
    await postgres.execute(
        """INSERT INTO ticket_events (ticket_id, event_type, content, author)
           VALUES ($1, 'created', $2, $3)""",
        row["id"], f"Ticket created: {body.title}", body.created_by,
    )
    return row


@router.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, body: TicketUpdate):
    existing = await postgres.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
    if not existing:
        raise HTTPException(404, "Ticket not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return existing

    # Track status changes
    if "status" in updates and updates["status"] != existing["status"]:
        await postgres.execute(
            """INSERT INTO ticket_events (ticket_id, event_type, content, author)
               VALUES ($1, 'status_change', $2, 'system')""",
            ticket_id, f"{existing['status']} → {updates['status']}",
        )

    set_parts = [f"{k} = ${i+2}" for i, k in enumerate(updates)]
    set_parts.append("updated_at = NOW()")
    query = f"UPDATE tickets SET {', '.join(set_parts)} WHERE id = $1 RETURNING *"
    row = await postgres.fetchrow(query, ticket_id, *updates.values())
    return row


@router.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int):
    result = await postgres.execute("DELETE FROM tickets WHERE id = $1", ticket_id)
    if result == "DELETE 0":
        raise HTTPException(404, "Ticket not found")
    return {"deleted": ticket_id}


@router.post("/tickets/{ticket_id}/events")
async def add_event(ticket_id: int, body: EventCreate):
    existing = await postgres.fetchrow("SELECT id FROM tickets WHERE id = $1", ticket_id)
    if not existing:
        raise HTTPException(404, "Ticket not found")

    row = await postgres.fetchrow(
        """INSERT INTO ticket_events (ticket_id, event_type, content, author)
           VALUES ($1, 'comment', $2, $3) RETURNING *""",
        ticket_id, body.content, body.author,
    )
    return row
