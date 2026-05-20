from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TicketCreate(BaseModel):
    customer_id:    str
    customer_email: str
    customer_name:  str
    subject:        str
    description:    str
    priority:       str = "medium"
    category:       str = "general"

class TicketUpdate(BaseModel):
    status:               Optional[str] = None
    priority:             Optional[str] = None
    agent_final_response: Optional[str] = None

class TicketResponse(BaseModel):
    id:                   int
    customer_id:          str
    customer_email:       str
    customer_name:        str
    subject:              str
    description:          str
    status:               str
    priority:             str
    category:             str
    ai_draft_response:    Optional[str]
    agent_final_response: Optional[str]
    kb_sources_used:      Optional[str]
    memory_context_used:  Optional[str]
    created_at:           datetime

    class Config:
        from_attributes = True

class AIGenerateResponse(BaseModel):
    ticket_id:      int
    draft_response: str
    kb_sources:     List[str]
    memory_context: str
    crm_data:       dict
    billing_data:   dict