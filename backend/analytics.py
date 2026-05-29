from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

# Use package-relative imports to match the rest of the codebase
from .core.database import get_db
from .core.security import require_role
from .tickets import models as ticket_models

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


def _overview_payload(db: Session):
    total_tickets = db.query(ticket_models.Ticket).count()
    open_tickets = db.query(ticket_models.Ticket).filter(ticket_models.Ticket.status == "open").count()
    resolved_tickets = db.query(ticket_models.Ticket).filter(ticket_models.Ticket.status == "resolved").count()
    # Some ticket-related models may not exist in fresh DBs; guard against that
    try:
        total_conversations = db.query(ticket_models.Conversation).count()
    except Exception:
        total_conversations = 0
    try:
        escalated = db.query(ticket_models.Conversation).filter(ticket_models.Conversation.escalated == True).count()
    except Exception:
        escalated = 0
    try:
        avg_sentiment = db.query(func.avg(ticket_models.Conversation.sentiment_score)).scalar() or 0.0
    except Exception:
        avg_sentiment = 0.0
    try:
        avg_rating = db.query(func.avg(ticket_models.Feedback.rating)).scalar() or 0.0
    except Exception:
        avg_rating = 0.0
    reopened_tickets = db.query(ticket_models.Ticket).filter(ticket_models.Ticket.status == "reopened").count() if total_tickets else 0
    sla_breaches = 0
    try:
        sla_breaches = db.query(ticket_models.Ticket).filter(
            ticket_models.Ticket.sla_due_at != None,
            ticket_models.Ticket.sla_due_at < datetime.utcnow(),
            ticket_models.Ticket.status.in_(["open", "in_progress", "reopened"]),
        ).count()
    except Exception:
        sla_breaches = 0
    agent_load = []
    try:
        agent_load = db.query(ticket_models.Ticket.assigned_agent_id, func.count(ticket_models.Ticket.id)).filter(
            ticket_models.Ticket.assigned_agent_id != None,
            ticket_models.Ticket.status.in_(["open", "in_progress", "reopened"]),
        ).group_by(ticket_models.Ticket.assigned_agent_id).all()
    except Exception:
        agent_load = []

    resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets else 0

    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets,
        "resolution_rate": round(resolution_rate, 1),
        "total_conversations": total_conversations,
        "escalated_conversations": escalated,
        "escalation_rate": round((escalated / total_conversations * 100) if total_conversations else 0, 1),
        "avg_sentiment_score": round(avg_sentiment, 3),
        "avg_csat_rating": round(avg_rating, 2),
        "reopen_rate": round((reopened_tickets / total_tickets * 100) if total_tickets else 0, 1),
        "sla_breaches": sla_breaches,
        "agent_load": [{"agent_id": row[0], "open_tickets": row[1]} for row in (agent_load or [])],
    }


@analytics_router.get("/overview")
def overview(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    return _overview_payload(db)


@analytics_router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    # Backwards-compatible alias used by frontend
    return _overview_payload(db)
