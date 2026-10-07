from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Corporate IT Ticket API")


class Ticket(BaseModel):
    category: str
    priority: str
    support_team: str
    description: str
    similar_incidents: list[str] = []


@app.post("/api/incidents")
def create_incident(ticket: Ticket):
    ticket_id = f"INC-AUTO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    return {
        "ticket_id": ticket_id,
        "status": "Created",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ticket": ticket.model_dump(),
    }