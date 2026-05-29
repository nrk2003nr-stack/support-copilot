from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, require_role
from backend.auth import models as auth_models
from backend.tickets import models as ticket_models
import json
from datetime import datetime

handoff_router = APIRouter(prefix="/handoff", tags=["handoff"])

# In-memory connection registry (use Redis for multi-instance)
active_connections: dict[str, WebSocket] = {}

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, session_id: str):
        await ws.accept()
        self.connections[session_id] = ws

    def disconnect(self, session_id: str):
        self.connections.pop(session_id, None)

    async def send_to(self, session_id: str, data: dict):
        ws = self.connections.get(session_id)
        if ws:
            await ws.send_json(data)

    async def broadcast_to_agents(self, data: dict):
        for sid, ws in list(self.connections.items()):
            if sid.startswith("agent_"):
                try:
                    await ws.send_json(data)
                except Exception:
                    self.disconnect(sid)

manager = ConnectionManager()

def _role(user) -> str:
    return user.role.value if hasattr(user.role, "value") else user.role

@handoff_router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "agent_message":
                # Agent sends message to customer
                customer_session = data.get("customer_session")
                await manager.send_to(customer_session, {
                    "type": "agent_message",
                    "content": data.get("content"),
                    "agent_name": data.get("agent_name"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif msg_type == "customer_message":
                # Customer sends message, forward to assigned agent
                await manager.broadcast_to_agents({
                    "type": "customer_message",
                    "session_id": session_id,
                    "content": data.get("content"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif msg_type == "request_handoff":
                # Notify all agents of escalation
                await manager.broadcast_to_agents({
                    "type": "escalation_request",
                    "session_id": session_id,
                    "reason": data.get("reason", "Customer requested human agent"),
                    "sentiment_score": data.get("sentiment_score"),
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@handoff_router.post("/escalate/{conversation_id}")
def escalate_conversation(conversation_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Mark a conversation as escalated (creates a high-priority ticket automatically)"""
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if _role(current_user) == "customer" and conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    conv.escalated = True
    conv.human_active = True
    # Auto-create urgent ticket
    ticket = models.Ticket(
        title=f"Escalated conversation #{conversation_id}",
        description=conv.summary or "Customer requested human support",
        priority="urgent",
        status="open",
        user_id=conv.user_id,
        conversation_id=conversation_id
    )
    db.add(ticket)
    db.flush()
    db.add(models.TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="handoff.escalated", payload="{}"))
    db.commit()
    return {"message": "Escalated", "ticket_id": ticket.id}

@handoff_router.post("/tickets/{ticket_id}/takeover")
def take_over(ticket_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("agent", "admin"))):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.assigned_agent_id = current_user.id
    ticket.status = "in_progress"
    if ticket.conversation:
        ticket.conversation.human_active = True
        ticket.conversation.escalated = True
    db.add(models.TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="handoff.takeover", payload="{}"))
    db.commit()
    return {"message": "Human handoff active", "ticket_id": ticket.id}

@handoff_router.post("/tickets/{ticket_id}/resume-bot")
def resume_bot(ticket_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("agent", "admin"))):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.conversation:
        ticket.conversation.human_active = False
    db.add(models.TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="handoff.resume_bot", payload="{}"))
    db.commit()
    return {"message": "Bot automation resumed", "ticket_id": ticket.id}
