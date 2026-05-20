from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base
import enum

class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    escalated = "escalated"

class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class Ticket(Base):
    __tablename__ = "tickets"

    id                  = Column(Integer, primary_key=True, index=True)
    customer_id         = Column(String, nullable=False, index=True)
    customer_email      = Column(String, nullable=False)
    customer_name       = Column(String, nullable=False)
    subject             = Column(String, nullable=False)
    description         = Column(Text, nullable=False)
    status              = Column(Enum(TicketStatus), default=TicketStatus.open)
    priority            = Column(Enum(TicketPriority), default=TicketPriority.medium)
    category            = Column(String, default="general")
    ai_draft_response   = Column(Text, nullable=True)
    agent_final_response = Column(Text, nullable=True)
    kb_sources_used     = Column(Text, nullable=True)   # stored as JSON string
    memory_context_used = Column(Text, nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id          = Column(Integer, primary_key=True, index=True)
    filename    = Column(String, nullable=False)
    file_type   = Column(String, nullable=False)
    chunk_count = Column(Integer, default=0)
    status      = Column(String, default="indexed")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())