from backend.db.models import AgentRunLog
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import threading

from backend.db.database import get_db
from backend.db.models import Ticket
from backend.db.schemas import AIGenerateResponse
from backend.core.agent_graph import run_agent
from backend.core.memory_engine import save_interaction_memory

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/generate/{ticket_id}", response_model=AIGenerateResponse)
def generate_ai_response(ticket_id: int, db: Session = Depends(get_db)):
    """Run the full LangGraph agent pipeline and save the draft to the ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = run_agent(
        customer_id=ticket.customer_id,
        customer_name=ticket.customer_name,
        ticket_subject=ticket.subject,
        ticket_description=ticket.description,
    )

    # Log the agent run
    log = AgentRunLog(
        ticket_id=ticket_id,
        action='generate_draft_response',
        result=f'KB sources: {result["kb_sources"]}. Memory used: {result["memory_context"][:150]}',
        duration_ms=None
    )
    db.add(log)
    db.commit()

    ticket.ai_draft_response   = result["draft_response"]
    ticket.kb_sources_used     = json.dumps(result["kb_sources"])
    ticket.memory_context_used = result["memory_context"]
    db.commit()

    return AIGenerateResponse(
        ticket_id=ticket_id,
        draft_response=result["draft_response"],
        kb_sources=result["kb_sources"],
        memory_context=result["memory_context"],
        crm_data=result["crm_data"],
        billing_data=result["billing_data"],
    )


def _save_memory_thread(
    customer_id: str,
    subject: str,
    description: str,
    final_response: str,
):
    """Runs in a daemon thread — survives independently of the HTTP request."""
    try:
        save_interaction_memory(
            customer_id=customer_id,
            ticket_subject=subject,
            customer_message=description,
            agent_response=final_response,
        )
    except Exception as e:
        print(f"Thread memory save failed for {customer_id}: {e}")


@router.post("/resolve/{ticket_id}")
def resolve_and_save_memory(ticket_id: int, db: Session = Depends(get_db)):
    """
    Mark ticket resolved instantly, save memory in a daemon thread.
    Returns immediately — no timeout possible.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    final_response = ticket.agent_final_response or ticket.ai_draft_response
    if not final_response:
        raise HTTPException(
            status_code=400,
            detail="No response to save. Generate or approve a response first.",
        )

    # Mark resolved immediately
    ticket.status = "resolved"
    db.commit()

    # Save memory in a separate daemon thread (not tied to request lifecycle)
    t = threading.Thread(
        target=_save_memory_thread,
        args=(
            ticket.customer_id,
            ticket.subject,
            ticket.description,
            final_response,
        ),
        daemon=True,
    )
    t.start()

    return {
        "message": "Ticket resolved! Memory is being saved in the background.",
        "ticket_id": ticket_id,
        "status": "resolved",
    }