import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_support.db"
os.environ["SEED_DEMO_DATA"] = "false"

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

db_file = BACKEND / "test_support.db"
if db_file.exists():
    db_file.unlink()

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


client = TestClient(app)


def auth(email: str, username: str, role: str = "customer") -> dict:
    response = client.post("/auth/register", json={
        "email": email,
        "username": username,
        "password": "password123",
        "role": role,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_login_chat_ticket_escalate_resolve_logout_smoke():
    customer = auth("smoke-customer@example.com", "smoke_customer")
    headers = {"Authorization": f"Bearer {customer['access_token']}"}

    chat = client.post("/chat", json={"message": "I am angry and need a human agent"}, headers=headers)
    assert chat.status_code == 200, chat.text
    chat_body = chat.json()
    assert chat_body["conversation_id"]
    assert chat_body["escalation_recommended"] is True

    ticket = client.post("/tickets/", json={
        "title": "Cannot complete checkout",
        "description": "Checkout fails and I need help from support",
        "priority": "urgent",
        "conversation_id": chat_body["conversation_id"],
    }, headers=headers)
    assert ticket.status_code == 200, ticket.text
    ticket_id = ticket.json()["id"]

    admin = auth("smoke-admin@example.com", "smoke_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    resolved = client.patch(f"/tickets/{ticket_id}", json={
        "status": "resolved",
        "resolution_note": "Payment profile was refreshed and checkout completed.",
        "add_to_knowledge_base": True,
    }, headers=admin_headers)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"

    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 200
    denied = client.get("/auth/me", headers=headers)
    assert denied.status_code == 401


def test_channel_webhook_mock_and_rbac():
    response = client.post("/auth/register", json={
        "email": "channel-admin@example.com",
        "username": "channel_admin",
        "password": "password123",
        "role": "admin",
    })
    if response.status_code != 200:
        response = client.post("/auth/login", json={"email": "smoke-admin@example.com", "password": "password123"})
    assert response.status_code == 200, response.text
    admin = response.json()
    headers = {"Authorization": f"Bearer {admin['access_token']}"}
    status = client.get("/channels/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["slack"]["mode"] == "mock"

    webhook = client.post("/channels/slack/webhook", json={"event": {"text": "hello", "user": "U1", "ts": "1"}})
    assert webhook.status_code == 200
    assert webhook.json()["message"]["body"] == "hello"
