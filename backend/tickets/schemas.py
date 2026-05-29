from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .models import TicketStatus, TicketPriority, Channel, MessageRole


class MessageOut(BaseModel):
    id: int
    ticket_id: int
    role: MessageRole
    content: str
    language: str
    sentiment_score: Optional[float]
    feedback: Optional[int]
    sources: Optional[list]
    attachment_url: Optional[str]
    attachment_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: Optional[str] = "Support Request"
    description: Optional[str] = None
    priority: TicketPriority = TicketPriority.medium
    channel: Channel = Channel.web
    initial_message: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    agent_id: Optional[int] = None
    title: Optional[str] = None


class TicketOut(BaseModel):
    id: int
    user_id: int
    agent_id: Optional[int]
    title: str
    status: TicketStatus
    priority: TicketPriority
    channel: Channel
    sentiment_score: Optional[float]
    urgency_score: Optional[int]
    detected_language: str
    summary: Optional[str]
    category: Optional[str]
    sla_deadline: Optional[datetime]
    sla_breached: bool
    csat_score: Optional[int]
    csat_comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    first_response_at: Optional[datetime]
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True


class TicketListOut(BaseModel):
    id: int
    title: str
    status: TicketStatus
    priority: TicketPriority
    channel: Channel
    sentiment_score: Optional[float]
    urgency_score: Optional[int]
    detected_language: str
    csat_score: Optional[int]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    content: str
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None


class FeedbackRequest(BaseModel):
    rating: int   # 1 or -1


class CSATRequest(BaseModel):
    score: int    # 1-5
    comment: Optional[str] = None
