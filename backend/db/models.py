from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey
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

from sqlalchemy import Boolean  # add this to your existing imports

# ─── TABLE: CUSTOMER ──────────────────────────────────────
class Customer(Base):
    __tablename__ = 'customers'

    id          = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, unique=True, nullable=False)  # e.g. CUST001
    name        = Column(String, nullable=False)
    email       = Column(String, unique=True, nullable=False)
    phone_no    = Column(String, unique=True, nullable=True)
    password    = Column(String, nullable=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

# ─── TABLE: ADMIN ─────────────────────────────────────────
class Admin(Base):
    __tablename__ = 'admins'

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String, unique=True, nullable=False)
    password   = Column(String, nullable=False)
    email      = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ─── TABLE: AI_AGENT ──────────────────────────────────────
class AIAgent(Base):
    __tablename__ = 'ai_agents'

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String, nullable=False)
    model           = Column(String, nullable=False, default='llama3.2:1b')
    status          = Column(String, default='active')
    config_settings = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

# ─── TABLE: AGENT_RUN_LOG ─────────────────────────────────
class AgentRunLog(Base):
    __tablename__ = 'agent_run_logs'

    id          = Column(Integer, primary_key=True, index=True)
    ticket_id   = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    action      = Column(String, nullable=False)
    result      = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

# ─── TABLE: ESCALATION ────────────────────────────────────
class Escalation(Base):
    __tablename__ = 'escalations'

    id         = Column(Integer, primary_key=True, index=True)
    ticket_id  = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    reason     = Column(Text, nullable=False)
    status     = Column(String, default='open')
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# ─── TABLE: FEEDBACK ──────────────────────────────────────
class Feedback(Base):
    __tablename__ = 'feedback'

    id          = Column(Integer, primary_key=True, index=True)
    ticket_id   = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    customer_id = Column(String, nullable=False)
    rating      = Column(Integer, nullable=False)
    subject     = Column(String, nullable=True)
    message     = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

# ─── TABLE: NOTIFICATION ──────────────────────────────────
class Notification(Base):
    __tablename__ = 'notifications'

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(String, nullable=False)  # customer_id or 'admin'
    type       = Column(String, nullable=False)
    message    = Column(Text, nullable=False)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())