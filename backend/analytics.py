from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from database import get_db
from auth import require_role
import models

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

@analytics_router.get("/overview")
def overview(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    total_tickets = db.query(models.Ticket).count()
    open_tickets = db.query(models.Ticket).filter(models.Ticket.status == "open").count()
    resolved_tickets = db.query(models.Ticket).filter(models.Ticket.status == "resolved").count()
    total_conversations = db.query(models.Conversation).count()
    escalated = db.query(models.Conversation).filter(models.Conversation.escalated == True).count()
    avg_sentiment = db.query(func.avg(models.Conversation.sentiment_score)).scalar() or 0.0
    avg_rating = db.query(func.avg(models.Feedback.rating)).scalar() or 0.0
    reopened_tickets = db.query(models.Ticket).filter(models.Ticket.status == "reopened").count()
    sla_breaches = db.query(models.Ticket).filter(
        models.Ticket.sla_due_at != None,
        models.Ticket.sla_due_at < datetime.utcnow(),
        models.Ticket.status.in_(["open", "in_progress", "reopened"])
    ).count()
    agent_load = db.query(models.Ticket.assigned_agent_id, func.count(models.Ticket.id)).filter(
        models.Ticket.assigned_agent_id != None,
        models.Ticket.status.in_(["open", "in_progress", "reopened"])
    ).group_by(models.Ticket.assigned_agent_id).all()

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
        "agent_load": [{"agent_id": row[0], "open_tickets": row[1]} for row in agent_load],
    }

@analytics_router.get("/tickets/by-priority")
def tickets_by_priority(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    results = db.query(models.Ticket.priority, func.count(models.Ticket.id)).group_by(models.Ticket.priority).all()
    return [{"priority": r[0], "count": r[1]} for r in results]

@analytics_router.get("/tickets/by-status")
def tickets_by_status(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    results = db.query(models.Ticket.status, func.count(models.Ticket.id)).group_by(models.Ticket.status).all()
    return [{"status": r[0], "count": r[1]} for r in results]

@analytics_router.get("/feedback/summary")
def feedback_summary(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    thumbs_up = db.query(models.Feedback).filter(models.Feedback.thumbs_up == True).count()
    thumbs_down = db.query(models.Feedback).filter(models.Feedback.thumbs_up == False).count()
    return {"thumbs_up": thumbs_up, "thumbs_down": thumbs_down}

@analytics_router.get("/channels/mix")
def channel_mix(db: Session = Depends(get_db), _=Depends(require_role("admin", "agent"))):
    results = db.query(models.Ticket.channel, func.count(models.Ticket.id)).group_by(models.Ticket.channel).all()
    return [{"channel": r[0] or "web", "count": r[1]} for r in results]
