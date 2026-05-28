"""
schemas.py — Pydantic models for all API request bodies and responses.
Fixed for Pydantic V2 — zero deprecation warnings.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    customer = "customer"
    agent    = "agent"
    admin    = "admin"


class TicketStatus(str, Enum):
    open        = "open"
    in_progress = "in_progress"
    resolved    = "resolved"
    closed      = "closed"
    reopened    = "reopened"


class TicketPriority(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"
    urgent = "urgent"


# ── Auth Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    email:    str = Field(..., min_length=5,  max_length=255)
    username: str = Field(..., min_length=3,  max_length=50)
    password: str = Field(..., min_length=6)
    role:     UserRole = UserRole.customer

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "email":    "user@example.com",
                "username": "john_doe",
                "password": "securepassword",
                "role":     "customer",
            }
        }
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email":    "user@example.com",
                "password": "securepassword",
            }
        }
    )

    email:    str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    email:      str
    username:   str
    role:       str
    is_active:  bool
    created_at: datetime


# ── Chat Schemas ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message":         "My order hasn't arrived yet.",
                "session_id":      None,
                "conversation_id": None,
            }
        }
    )

    message:         str = Field(..., min_length=1, max_length=4000)
    session_id:      Optional[str] = None
    conversation_id: Optional[int] = None
    ticket_id:       Optional[int] = None
    language:        Optional[str] = None


class SentimentOut(BaseModel):
    label:      str    # "POSITIVE" | "NEGATIVE"
    score:      float  # raw model confidence 0–1
    normalized: float  # -1 (very negative) to +1 (very positive)
    is_negative:bool   # True if normalized < -0.3


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reply:                  str
    session_id:             str
    conversation_id:        int
    ticket_id:              Optional[int] = None
    language:               str = "en"
    confidence:             float = 0.0
    sentiment:              SentimentOut
    escalation_recommended: bool
    sources:                List[str]


# ── Conversation Schemas ───────────────────────────────────────────────────

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    role:            str
    content:         str
    sentiment_score: Optional[float]
    timestamp:       datetime
    has_image:       bool


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    session_id:      str
    started_at:      datetime
    ended_at:        Optional[datetime]
    summary:         Optional[str]
    sentiment_score: float
    escalated:       bool
    messages:        List[MessageOut] = []


# ── Ticket Schemas ─────────────────────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "title":           "Cannot login to my account",
                "description":     "I keep getting 'invalid credentials' even after reset.",
                "priority":        "medium",
                "conversation_id": None,
            }
        }
    )

    title:           str = Field(..., min_length=5, max_length=200)
    description:     str = Field(..., min_length=10)
    priority:        TicketPriority = TicketPriority.medium
    conversation_id: Optional[int] = None
    tags:            Optional[str] = ""
    channel:         Optional[str] = "web"
    language:        Optional[str] = "en"


class UpdateTicketRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status:               Optional[TicketStatus]  = None
    priority:             Optional[TicketPriority] = None
    assigned_agent_id:    Optional[int]            = None
    resolution_note:      Optional[str]            = None
    add_to_knowledge_base:Optional[bool]           = False
    tags:                 Optional[str]            = None
    language:             Optional[str]            = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                   int
    title:                str
    description:          str
    status:               str
    priority:             str
    sla_due_at:           Optional[datetime] = None
    tags:                 Optional[str] = ""
    channel:              Optional[str] = "web"
    language:             Optional[str] = "en"
    sentiment:            float = 0.0
    user_id:              int
    assigned_agent_id:    Optional[int]
    conversation_id:      Optional[int]
    created_at:           datetime
    resolved_at:          Optional[datetime]
    resolution_note:      Optional[str]
    add_to_knowledge_base:bool


class TicketCommentRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class TicketCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    body: str
    created_at: datetime


class TicketEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    actor_id: Optional[int]
    event_type: str
    payload: Optional[str]
    created_at: datetime


# ── Feedback Schemas ───────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating":    4,
                "thumbs_up": True,
                "comment":   "Very helpful response!",
            }
        }
    )

    rating:    int  = Field(..., ge=1, le=5)
    thumbs_up: bool
    comment:   Optional[str] = Field(None, max_length=500)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    ticket_id:  int
    rating:     int
    thumbs_up:  bool
    comment:    Optional[str]
    created_at: datetime


# ── Knowledge Base Schemas ─────────────────────────────────────────────────

class KnowledgeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    question:         str
    answer:           str
    source_ticket_id: Optional[int]
    added_to_chroma:  bool
    created_at:       datetime


# ── Analytics Schemas ──────────────────────────────────────────────────────

class OverviewStats(BaseModel):
    total_tickets:           int
    open_tickets:            int
    resolved_tickets:        int
    resolution_rate:         float
    total_conversations:     int
    escalated_conversations: int
    escalation_rate:         float
    avg_sentiment_score:     float
    avg_csat_rating:         float


class CountByLabel(BaseModel):
    label: str
    count: int


class FeedbackSummary(BaseModel):
    thumbs_up:   int
    thumbs_down: int


# ── Vision / Handoff Schemas ───────────────────────────────────────────────

class VisionResponse(BaseModel):
    answer:   str
    filename: str


class EscalateResponse(BaseModel):
    message:   str
    ticket_id: int


# Resolve forward reference
TokenResponse.model_rebuild()
