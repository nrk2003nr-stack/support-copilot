from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from auth import get_current_user, require_role
import models
from pydantic import BaseModel
from typing import Optional
from knowledge import add_to_knowledge_base

ticket_router = APIRouter(prefix="/tickets", tags=["tickets"])

class CreateTicketRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    conversation_id: Optional[int] = None

class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent_id: Optional[int] = None
    resolution_note: Optional[str] = None
    add_to_knowledge_base: Optional[bool] = False

@ticket_router.post("/")
def create_ticket(req: CreateTicketRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = models.Ticket(
        title=req.title,
        description=req.description,
        priority=req.priority,
        user_id=current_user.id,
        conversation_id=req.conversation_id
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

@ticket_router.get("/")
def list_tickets(status: Optional[str] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.Ticket)
    if current_user.role == "customer":
        query = query.filter(models.Ticket.user_id == current_user.id)
    elif current_user.role == "agent":
        query = query.filter(
            (models.Ticket.assigned_agent_id == current_user.id) |
            (models.Ticket.assigned_agent_id == None)
        )
    if status:
        query = query.filter(models.Ticket.status == status)
    return query.order_by(models.Ticket.created_at.desc()).all()

@ticket_router.get("/{ticket_id}")
def get_ticket(ticket_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == "customer" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ticket

@ticket_router.patch("/{ticket_id}")
def update_ticket(ticket_id: int, req: UpdateTicketRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if req.status:
        ticket.status = req.status
        if req.status == "resolved":
            ticket.resolved_at = datetime.utcnow()
    if req.priority:
        ticket.priority = req.priority
    if req.assigned_agent_id:
        ticket.assigned_agent_id = req.assigned_agent_id
        ticket.status = "in_progress"
    if req.resolution_note:
        ticket.resolution_note = req.resolution_note

    # Auto-add resolved answer to knowledge base
    if req.add_to_knowledge_base and req.resolution_note and ticket.description:
        add_to_knowledge_base(
            question=ticket.description,
            answer=req.resolution_note,
            source_ticket_id=ticket.id,
            approved_by=current_user.id,
            db=db
        )

    db.commit()
    db.refresh(ticket)
    return ticket

@ticket_router.post("/{ticket_id}/assign")
def auto_assign_ticket(ticket_id: int, current_user=Depends(require_role("agent", "admin")), db: Session = Depends(get_db)):
    """Agent claims an unassigned ticket"""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.assigned_agent_id = current_user.id
    ticket.status = "in_progress"
    db.commit()
    return {"message": "Ticket assigned", "ticket_id": ticket_id}

class FeedbackRequest(BaseModel):
    rating: int       # 1-5
    thumbs_up: bool
    comment: Optional[str] = None

@ticket_router.post("/{ticket_id}/feedback")
def submit_feedback(ticket_id: int, req: FeedbackRequest, db: Session = Depends(get_db)):
    existing = db.query(models.Feedback).filter(models.Feedback.ticket_id == ticket_id).first()
    if existing:
        existing.rating = req.rating
        existing.thumbs_up = req.thumbs_up
        existing.comment = req.comment
    else:
        feedback = models.Feedback(
            ticket_id=ticket_id,
            rating=req.rating,
            thumbs_up=req.thumbs_up,
            comment=req.comment
        )
        db.add(feedback)
    db.commit()
    return {"message": "Feedback recorded. Thank you!"}