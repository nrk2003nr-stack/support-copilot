"""WhatsApp channel via Twilio."""
import httpx
from .base import BaseChannel
from ..tickets.models import Channel, Ticket
from ..core.config import settings


class WhatsAppChannel(BaseChannel):
    channel_name = Channel.whatsapp

    async def send_message(self, ticket: Ticket, content: str) -> None:
        if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_NUMBER]):
            print("[WhatsApp] Twilio not configured — skipping")
            return

        meta = ticket.channel_metadata or {}
        to_number = meta.get("from_number", "")
        if not to_number:
            return

        async with httpx.AsyncClient(auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)) as client:
            await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
                data={
                    "From": f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                    "To": f"whatsapp:{to_number}",
                    "Body": content,
                },
            )


whatsapp_channel = WhatsAppChannel()