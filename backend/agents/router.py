from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

from backend.core.database import get_db
from backend.core.deps import get_current_user
from backend.auth.models import User
from backend.tickets.models import Ticket, Message, MessageRole, TicketStatus
from backend.agents.graph import get_graph
from backend.agents.nodes import summary_node, extract_kb_article

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    ticket_id: str
    message: str
    image_url: Optional[str] = None  # for vision support (Tier 2)


class ChatResponse(BaseModel):
    ticket_id: str
    bot_message: str
    detected_language: str
    sentiment_score: float
    urgency_score: int
    should_handoff: bool
    message_id: str


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load ticket
    ticket = db.query(Ticket).filter(Ticket.id == body.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status == TicketStatus.resolved:
        raise HTTPException(status_code=400, detail="Ticket is already resolved")

    # Save user message to DB
    user_msg = Message(
        ticket_id=ticket.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    db.flush()

    # Build conversation history for LangGraph state
    history = [
        {"role": m.role.value, "content": m.content}
        for m in ticket.messages
    ]

    # Build initial state
    initial_state = {
        "ticket_id": str(ticket.id),
        "user_id": str(current_user.id),
        "messages": history,
        "user_query": body.message,
        "bot_response": "",
        "detected_language": ticket.language,
        "sentiment_score": 0.0,
        "sentiment_emotion": "neutral",
        "consecutive_negative": 0,
        "should_handoff": False,
        "urgency_score": 3,
        "summary": None,
        "kb_context": None,
    }

    # Run LangGraph
    graph = get_graph()
    result = await graph.ainvoke(initial_state)

    # Update ticket with new insights
    ticket.language = result["detected_language"]
    ticket.sentiment_score = result["sentiment_score"]
    ticket.urgency_score = result["urgency_score"]

    if result.get("should_handoff"):
        ticket.status = TicketStatus.pending_agent
        ticket.is_frustrated = True

    # Save bot response to DB
    bot_msg = Message(
        ticket_id=ticket.id,
        role=MessageRole.bot,
        content=result["bot_response"],
        language=result["detected_language"],
        sentiment_score=result["sentiment_score"],
    )
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)

    return ChatResponse(
        ticket_id=str(ticket.id),
        bot_message=result["bot_response"],
        detected_language=result["detected_language"],
        sentiment_score=result["sentiment_score"],
        urgency_score=result["urgency_score"],
        should_handoff=result["should_handoff"],
        message_id=str(bot_msg.id),
    )


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve a ticket — generates summary and triggers KB extraction."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    history = [{"role": m.role.value, "content": m.content} for m in ticket.messages]

    # Generate summary via LangGraph node
    state = {"messages": history, "summary": None}
    result = summary_node(state)
    ticket.summary = result["summary"]
    ticket.status = TicketStatus.resolved
    ticket.resolved_at = datetime.utcnow()
    db.commit()

    return {"summary": ticket.summary, "resolved_at": ticket.resolved_at.isoformat()}


@router.post("/{ticket_id}/extract-kb")
async def extract_kb(
    ticket_id: str,
    csat_score: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract KB article from resolved ticket. Call after CSAT is submitted."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    history = [{"role": m.role.value, "content": m.content} for m in ticket.messages]
    article = extract_kb_article(history, csat_score)

    if not article:
        return {"extracted": False, "reason": "Conversation not suitable for KB"}

    # TODO: save to a "pending_kb" table for admin review before adding to ChromaDB
    return {"extracted": True, "article": article}