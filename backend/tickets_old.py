from datetime import datetime, timedelta
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from knowledge import add_to_knowledge_base
from backend.auth import models as auth_models
from backend.tickets import models as ticket_models
from schemas import CreateTicketRequest, FeedbackRequest, TicketCommentRequest, UpdateTicketRequest

ticket_router = APIRouter(prefix="/tickets", tags=["tickets"])


def _role(user) -> str:
    return user.role.value if hasattr(user.role, "value") else user.role


def _can_view(ticket: models.Ticket, user) -> bool:
    return _role(user) in {"agent", "admin"} or ticket.user_id == user.id


def _event(db: Session, ticket_id: int, actor_id: Optional[int], event_type: str, payload: Optional[dict] = None) -> None:
    db.add(models.TicketEvent(
        ticket_id=ticket_id,
        actor_id=actor_id,
        event_type=event_type,
        payload=json.dumps(payload or {}),
    ))


def _sla(priority: str) -> datetime:
    hours = {"urgent": 4, "high": 12, "medium": 24, "low": 72}.get(priority, 24)
    return datetime.utcnow() + timedelta(hours=hours)


@ticket_router.post("/")
def create_ticket(req: CreateTicketRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if req.conversation_id:
        conv = db.query(models.Conversation).filter(models.Conversation.id == req.conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if _role(current_user) == "customer" and conv.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    priority = req.priority.value if hasattr(req.priority, "value") else req.priority
    ticket = models.Ticket(
        title=req.title,
        description=req.description,
        priority=priority,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        sla_due_at=_sla(priority),
        tags=req.tags or "",
        channel=req.channel or "web",
        language=req.language or "en",
    )
    db.add(ticket)
    db.flush()
    _event(db, ticket.id, current_user.id, "ticket.created", {"priority": priority})
    db.commit()
    db.refresh(ticket)
    return ticket


@ticket_router.get("/")
def list_tickets(status: Optional[str] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.Ticket)
    role = _role(current_user)
    if role == "customer":
        query = query.filter(models.Ticket.user_id == current_user.id)
    elif role == "agent":
        query = query.filter((models.Ticket.assigned_agent_id == current_user.id) | (models.Ticket.assigned_agent_id == None))
    if status:
        query = query.filter(models.Ticket.status == status)
    return query.order_by(models.Ticket.sla_due_at.asc().nullslast(), models.Ticket.created_at.desc()).all()


@ticket_router.get("/{ticket_id}")
def get_ticket(ticket_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not _can_view(ticket, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    return ticket


@ticket_router.get("/{ticket_id}/timeline")
def ticket_timeline(ticket_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = get_ticket(ticket_id, current_user, db)
    comments = [
        {"type": "comment", "created_at": c.created_at, "author_id": c.author_id, "body": c.body}
        for c in ticket.comments
    ]
    events = [
        {"type": "event", "created_at": e.created_at, "actor_id": e.actor_id, "event_type": e.event_type, "payload": e.payload}
        for e in ticket.events
    ]
    messages = []
    if ticket.conversation_id:
        messages = [
            {"type": "message", "created_at": m.timestamp, "role": m.role, "body": m.content}
            for m in db.query(models.Message).filter(models.Message.conversation_id == ticket.conversation_id).all()
        ]
    return sorted([*comments, *events, *messages], key=lambda item: item["created_at"])


@ticket_router.patch("/{ticket_id}")
def update_ticket(ticket_id: int, req: UpdateTicketRequest, current_user=Depends(require_role("agent", "admin")), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updates = req.model_dump(exclude_unset=True)
    old_status = ticket.status.value if hasattr(ticket.status, "value") else ticket.status

    if req.status:
        ticket.status = req.status.value if hasattr(req.status, "value") else req.status
        if ticket.status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        if ticket.status == "reopened":
            ticket.resolved_at = None
    if req.priority:
        priority = req.priority.value if hasattr(req.priority, "value") else req.priority
        ticket.priority = priority
        ticket.sla_due_at = _sla(priority)
    if req.assigned_agent_id is not None:
        ticket.assigned_agent_id = req.assigned_agent_id
        ticket.status = models.TicketStatus.in_progress
    if req.resolution_note is not None:
        ticket.resolution_note = req.resolution_note
    if req.tags is not None:
        ticket.tags = req.tags
    if req.language is not None:
        ticket.language = req.language
    ticket.add_to_knowledge_base = bool(req.add_to_knowledge_base)

    if req.add_to_knowledge_base and req.resolution_note and ticket.description:
        add_to_knowledge_base(
            question=ticket.description,
            answer=req.resolution_note,
            source_ticket_id=ticket.id,
            approved_by=None,
            db=db,
            status="draft",
            language=ticket.language or "en",
        )
        _event(db, ticket.id, current_user.id, "kb.draft_created")

    _event(db, ticket.id, current_user.id, "ticket.updated", {"old_status": old_status, "updates": updates})
    db.commit()
    db.refresh(ticket)
    return ticket


@ticket_router.post("/{ticket_id}/assign")
def auto_assign_ticket(ticket_id: int, current_user=Depends(require_role("agent", "admin")), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.assigned_agent_id = current_user.id
    ticket.status = models.TicketStatus.in_progress
    _event(db, ticket.id, current_user.id, "ticket.assigned")
    db.commit()
    return {"message": "Ticket assigned", "ticket_id": ticket_id}


@ticket_router.post("/{ticket_id}/comments")
def add_comment(ticket_id: int, req: TicketCommentRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not _can_view(ticket, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    comment = models.TicketComment(ticket_id=ticket_id, author_id=current_user.id, body=req.body)
    db.add(comment)
    _event(db, ticket.id, current_user.id, "ticket.comment_added")
    db.commit()
    db.refresh(comment)
    return comment


@ticket_router.post("/{ticket_id}/feedback")
def submit_feedback(ticket_id: int, req: FeedbackRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not _can_view(ticket, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    existing = db.query(models.Feedback).filter(models.Feedback.ticket_id == ticket_id).first()
    if existing:
        existing.rating = req.rating
        existing.thumbs_up = req.thumbs_up
        existing.comment = req.comment
    else:
        db.add(models.Feedback(ticket_id=ticket_id, rating=req.rating, thumbs_up=req.thumbs_up, comment=req.comment))
    _event(db, ticket.id, current_user.id, "feedback.submitted", {"rating": req.rating, "thumbs_up": req.thumbs_up})
    db.commit()
    return {"message": "Feedback recorded. Thank you!"}
