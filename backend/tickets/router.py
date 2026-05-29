from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..auth.models import User, UserRole
from .models import Ticket, Message, TicketStatus, TicketPriority, MessageRole, Channel
from .schemas import (
    TicketCreate, TicketUpdate, TicketOut, TicketListOut,
    SendMessageRequest, FeedbackRequest, CSATRequest, MessageOut
)
try:
    from ..agents.graph import run_support_agent
except Exception:
    # Optional agent functionality unavailable; provide a noop fallback.
    async def run_support_agent(ticket_id: int, user_id: int, message: str, history: list, db) -> dict:
        return {
            "response": "AI agent is currently unavailable.",
            "language": "en",
            "sentiment_score": 0.0,
            "urgency_score": 2,
            "sources": [],
            "needs_handoff": False,
        }
import json

router = APIRouter(prefix="/tickets", tags=["tickets"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, ticket_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(ticket_id, []).append(ws)

    def disconnect(self, ticket_id: int, ws: WebSocket):
        if ticket_id in self.active:
            self.active[ticket_id].remove(ws)

    async def broadcast(self, ticket_id: int, data: dict):
        for ws in self.active.get(ticket_id, []):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

manager = ConnectionManager()


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = Ticket(
        user_id=current_user.id,
        title=data.title,
        priority=data.priority,
        channel=data.channel,
        status=TicketStatus.open,
    )
    db.add(ticket)
    db.flush()

    initial_message = data.initial_message or data.description
    if initial_message:
        msg = Message(
            ticket_id=ticket.id,
            user_id=current_user.id,
            role=MessageRole.user,
            content=initial_message,
        )
        db.add(msg)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=List[TicketListOut])
def list_tickets(
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    channel: Optional[Channel] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Ticket)

    # Non-admins/agents only see their own tickets
    if current_user.role == UserRole.user:
        query = query.filter(Ticket.user_id == current_user.id)
    elif current_user.role == UserRole.agent:
        query = query.filter(
            (Ticket.agent_id == current_user.id) | (Ticket.agent_id == None)
        )

    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if channel:
        query = query.filter(Ticket.channel == channel)

    tickets = query.order_by(Ticket.updated_at.desc()).offset(skip).limit(limit).all()

    result = []
    for t in tickets:
        t_dict = {
            "id": t.id, "title": t.title, "status": t.status,
            "priority": t.priority, "channel": t.channel,
            "sentiment_score": t.sentiment_score, "urgency_score": t.urgency_score,
            "detected_language": t.detected_language, "csat_score": t.csat_score,
            "created_at": t.created_at, "updated_at": t.updated_at,
            "message_count": len(t.messages),
        }
        result.append(t_dict)
    return result


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.user and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if data.status:
        ticket.status = data.status
        if data.status == TicketStatus.resolved:
            ticket.resolved_at = datetime.utcnow()
    if data.priority:
        ticket.priority = data.priority
    if data.agent_id is not None:
        ticket.agent_id = data.agent_id
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()
    if data.title:
        ticket.title = data.title

    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/messages", response_model=MessageOut)
async def send_message(
    ticket_id: int,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Determine role
    if current_user.role == UserRole.agent or current_user.role == UserRole.admin:
        role = MessageRole.agent
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()
    else:
        role = MessageRole.user

    user_msg = Message(
        ticket_id=ticket_id,
        user_id=current_user.id,
        role=role,
        content=data.content,
        attachment_url=data.attachment_url,
        attachment_type=data.attachment_type,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Broadcast user message via WebSocket
    await manager.broadcast(ticket_id, {
        "type": "message",
        "data": {
            "id": user_msg.id, "role": role,
            "content": data.content, "created_at": str(user_msg.created_at)
        }
    })

    # If user message → run AI agent
    if role == MessageRole.user and ticket.status != TicketStatus.pending_agent:
        history = [{"role": m.role, "content": m.content} for m in ticket.messages]
        result = await run_support_agent(
            ticket_id=ticket_id,
            user_id=current_user.id,
            message=data.content,
            history=history,
            db=db,
        )

        # Save bot response
        bot_msg = Message(
            ticket_id=ticket_id,
            role=MessageRole.bot,
            content=result["response"],
            language=result.get("language", "en"),
            sentiment_score=result.get("sentiment_score"),
            sources=result.get("sources"),
        )
        db.add(bot_msg)

        # Update ticket with AI insights
        ticket.sentiment_score = result.get("sentiment_score")
        ticket.urgency_score = result.get("urgency_score")
        ticket.detected_language = result.get("language", "en")

        # Handle handoff
        if result.get("needs_handoff"):
            ticket.status = TicketStatus.pending_agent

        db.commit()
        db.refresh(bot_msg)

        await manager.broadcast(ticket_id, {
            "type": "message",
            "data": {
                "id": bot_msg.id, "role": "bot",
                "content": result["response"],
                "sources": result.get("sources"),
                "created_at": str(bot_msg.created_at),
            },
        })
        if result.get("needs_handoff"):
            await manager.broadcast(ticket_id, {"type": "handoff", "data": {"ticket_id": ticket_id}})

    return user_msg




@router.post("/{ticket_id}/assign")
def assign_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.agent_id = current_user.id
    if not ticket.first_response_at:
        ticket.first_response_at = datetime.utcnow()
    ticket.status = TicketStatus.in_progress
    db.commit()
    db.refresh(ticket)
    return {"message": "Assigned"}


@router.post("/{ticket_id}/csat")
def submit_csat(
    ticket_id: int,
    data: CSATRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket or ticket.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.csat_score = data.score
    ticket.csat_comment = data.comment
    db.commit()
    return {"message": "Thank you for your feedback!"}


@router.post("/{ticket_id}/messages/{message_id}/feedback")
def message_feedback(
    ticket_id: int,
    message_id: int,
    data: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(Message).filter(
        Message.id == message_id, Message.ticket_id == ticket_id
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.feedback = data.rating
    db.commit()
    return {"message": "Feedback recorded"}


@router.websocket("/{ticket_id}/ws")
async def ticket_websocket(ticket_id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(ticket_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ticket_id, websocket)
