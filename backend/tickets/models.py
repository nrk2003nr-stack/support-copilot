from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..core.database import Base


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    pending_bot = "pending_bot"
    pending_agent = "pending_agent"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class Channel(str, enum.Enum):
    web = "web"
    email = "email"
    whatsapp = "whatsapp"
    slack = "slack"


class MessageRole(str, enum.Enum):
    user = "user"
    agent = "agent"
    bot = "bot"
    system = "system"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String, nullable=False, default="Support Request")
    status = Column(Enum(TicketStatus), default=TicketStatus.open, index=True)
    priority = Column(Enum(TicketPriority), default=TicketPriority.medium)
    channel = Column(Enum(Channel), default=Channel.web)

    # AI Features
    sentiment_score = Column(Float, nullable=True)      # -1.0 to 1.0
    urgency_score = Column(Integer, nullable=True)       # 1-5
    detected_language = Column(String, default="en")
    summary = Column(Text, nullable=True)                # AI summary post-resolution
    category = Column(String, nullable=True)             # auto-categorized

    # External channel refs
    channel_message_id = Column(String, nullable=True)   # email thread id, slack ts, etc.
    channel_metadata = Column(JSON, nullable=True)

    # SLA
    sla_deadline = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)

    # CSAT
    csat_score = Column(Integer, nullable=True)          # 1-5
    csat_comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    first_response_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="tickets_created")
    agent = relationship("User", foreign_keys=[agent_id], back_populates="tickets_assigned")
    messages = relationship("Message", back_populates="ticket", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    language = Column(String, default="en")

    # AI metadata
    sentiment_score = Column(Float, nullable=True)
    feedback = Column(Integer, nullable=True)            # 1 = thumbs up, -1 = thumbs down
    sources = Column(JSON, nullable=True)                # RAG sources used

    # For image/voice messages
    attachment_url = Column(String, nullable=True)
    attachment_type = Column(String, nullable=True)      # "image", "audio"

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    user = relationship("User", back_populates="messages")
