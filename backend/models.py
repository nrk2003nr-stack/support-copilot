from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    customer = "customer"
    agent = "agent"
    admin = "admin"

class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.customer)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    tickets = relationship("Ticket", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, unique=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, default=0.0)   # -1 (negative) to 1 (positive)
    escalated = Column(Boolean, default=False)
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    ticket = relationship("Ticket", back_populates="conversation", uselist=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String)          # "user" | "assistant" | "agent"
    content = Column(Text)
    sentiment_score = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    has_image = Column(Boolean, default=False)
    conversation = relationship("Conversation", back_populates="messages")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.open)
    priority = Column(Enum(TicketPriority), default=TicketPriority.medium)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    add_to_knowledge_base = Column(Boolean, default=False)
    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])
    conversation = relationship("Conversation", back_populates="ticket")
    feedback = relationship("Feedback", back_populates="ticket", uselist=False)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    rating = Column(Integer)       # 1-5
    thumbs_up = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ticket = relationship("Ticket", back_populates="feedback")

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source_ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    added_to_chroma = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)