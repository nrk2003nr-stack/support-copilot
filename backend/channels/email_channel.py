"""Email channel via SendGrid."""
import httpx
from .base import BaseChannel
from ..tickets.models import Channel, Ticket
from ..core.config import settings


class EmailChannel(BaseChannel):
    channel_name = Channel.email

    async def send_message(self, ticket: Ticket, content: str) -> None:
        if not settings.SENDGRID_API_KEY:
            print("[Email] SENDGRID_API_KEY not set — skipping send")
            return

        meta = ticket.channel_metadata or {}
        to_email = meta.get("from_email", "")
        if not to_email:
            return

        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": settings.FROM_EMAIL, "name": "Support Copilot"},
                    "subject": f"Re: {ticket.title} [Ticket #{ticket.id}]",
                    "content": [{"type": "text/plain", "value": content}],
                },
            )


email_channel = EmailChannel()