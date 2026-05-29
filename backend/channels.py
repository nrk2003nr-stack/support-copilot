import hashlib
import hmac
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import models as auth_models
from backend.tickets import models as ticket_models
from auth import require_role
from database import get_db

channels_router = APIRouter(prefix="/channels", tags=["channels"])


class OutboundMessage(BaseModel):
    provider: str
    to: str
    body: str
    conversation_id: Optional[int] = None


def _enabled(provider: str) -> bool:
    return bool(os.getenv(f"{provider.upper()}_ENABLED", "false").lower() == "true")


def _verify_hmac(secret: str, body: bytes, signature: Optional[str]) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, digest)


def normalize_message(provider: str, payload: dict) -> dict:
    if provider == "slack":
        event = payload.get("event", payload)
        return {"external_id": event.get("ts"), "from": event.get("user"), "body": event.get("text", ""), "channel": "slack"}
    if provider in {"whatsapp", "twilio"}:
        return {"external_id": payload.get("MessageSid"), "from": payload.get("From"), "body": payload.get("Body", ""), "channel": "whatsapp"}
    if provider == "email":
        return {"external_id": payload.get("message_id"), "from": payload.get("from"), "body": payload.get("text", ""), "channel": "email"}
    return {"external_id": payload.get("id"), "from": payload.get("from"), "body": payload.get("body", ""), "channel": provider}


@channels_router.get("/status")
def channel_status(_=Depends(require_role("agent", "admin"))):
    providers = ["web", "email", "whatsapp", "slack", "hubspot", "salesforce"]
    return {
        provider: {
            "enabled": provider == "web" or _enabled(provider),
            "mode": "real" if _enabled(provider) else "mock",
        }
        for provider in providers
    }


@channels_router.post("/{provider}/webhook")
async def inbound_webhook(
    provider: str,
    request: Request,
    x_signature: Optional[str] = Header(None),
    x_slack_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    body = await request.body()
    secret = os.getenv(f"{provider.upper()}_WEBHOOK_SECRET", "")
    signature = x_signature or x_slack_signature
    if not _verify_hmac(secret, body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = await request.json()
    except Exception:
        form = await request.form()
        payload = dict(form)
    normalized = normalize_message(provider, payload)
    row = models.ChannelMessage(
        provider=provider,
        external_id=normalized.get("external_id"),
        direction="inbound",
        payload=json.dumps({"raw": payload, "normalized": normalized}),
        status="received",
    )
    db.add(row)
    db.commit()
    return {"ok": True, "mode": "real" if _enabled(provider) else "mock", "message": normalized}


@channels_router.post("/{provider}/send")
def send_message(provider: str, req: OutboundMessage, db: Session = Depends(get_db), _=Depends(require_role("agent", "admin"))):
    status = "sent" if _enabled(provider) else "mock_sent"
    row = models.ChannelMessage(
        provider=provider,
        direction="outbound",
        conversation_id=req.conversation_id,
        payload=req.model_dump_json(),
        status=status,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "status": status}
