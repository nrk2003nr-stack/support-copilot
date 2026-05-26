from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models
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
        return {"error": "Conversation not found"}
    conv.escalated = True
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
    db.commit()
    return {"message": "Escalated", "ticket_id": ticket.id}