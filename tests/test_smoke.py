import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_support.db"
os.environ["SEED_DEMO_DATA"] = "false"

db_file = ROOT / "test_support.db"
if db_file.exists():
    db_file.unlink()

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402


def register(client: TestClient, email: str, role: str = "user") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "full_name": email.split("@")[0].replace("-", " ").title(),
            "password": "password123",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


def test_auth_register_login_refresh_and_me():
    with TestClient(app) as client:
        created = register(client, "smoke-customer@example.com")
        headers = auth_headers(created)

        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json()["email"] == "smoke-customer@example.com"

        login = client.post(
            "/api/auth/login",
            json={"email": "smoke-customer@example.com", "password": "password123"},
        )
        assert login.status_code == 200, login.text
        assert login.json()["user"]["role"] == "user"

        refreshed = client.post("/api/auth/refresh", json={"refresh_token": created["refresh_token"]})
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["access_token"]


def test_ticket_lifecycle_and_agent_actions():
    with TestClient(app) as client:
        customer = register(client, "ticket-customer@example.com")
        customer_headers = auth_headers(customer)

        created = client.post(
            "/api/tickets",
            headers=customer_headers,
            json={
                "title": "Cannot complete checkout",
                "initial_message": "Checkout fails and I need help from support",
                "priority": "urgent",
            },
        )
        assert created.status_code == 201, created.text
        ticket = created.json()
        assert ticket["status"] == "open"
        assert ticket["priority"] == "urgent"
        assert len(ticket["messages"]) == 1

        listed = client.get("/api/tickets", headers=customer_headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()[0]["id"] == ticket["id"]

        agent = register(client, "ticket-agent@example.com", "agent")
        agent_headers = auth_headers(agent)

        assigned = client.post(f"/api/tickets/{ticket['id']}/assign", headers=agent_headers)
        assert assigned.status_code == 200, assigned.text

        updated = client.patch(
            f"/api/tickets/{ticket['id']}",
            headers=agent_headers,
            json={"status": "resolved", "priority": "high"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == "resolved"
        assert updated.json()["priority"] == "high"

        csat = client.post(
            f"/api/tickets/{ticket['id']}/csat",
            headers=customer_headers,
            json={"score": 5, "comment": "Quick and helpful"},
        )
        assert csat.status_code == 200, csat.text


def test_analytics_requires_agent_or_admin_and_returns_dashboard():
    with TestClient(app) as client:
        customer = register(client, "analytics-customer@example.com")
        denied = client.get("/api/analytics/dashboard", headers=auth_headers(customer))
        assert denied.status_code == 403

        admin = register(client, "analytics-admin@example.com", "admin")
        dashboard = client.get("/api/analytics/dashboard", headers=auth_headers(admin))
        assert dashboard.status_code == 200, dashboard.text
        body = dashboard.json()
        assert "total_tickets" in body
        assert "resolution_rate" in body
