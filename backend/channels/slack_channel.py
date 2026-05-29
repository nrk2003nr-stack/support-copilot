"""Slack channel via Slack Web API."""
import httpx
from .base import BaseChannel
from ..tickets.models import Channel, Ticket
from ..core.config import settings


class SlackChannel(BaseChannel):
    channel_name = Channel.slack

    async def send_message(self, ticket: Ticket, content: str) -> None:
        if not settings.SLACK_BOT_TOKEN:
            print("[Slack] SLACK_BOT_TOKEN not set — skipping")
            return

        meta = ticket.channel_metadata or {}
        channel_id = meta.get("channel", "")
        thread_ts = meta.get("thread_ts")

        payload = {"channel": channel_id, "text": content}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with httpx.AsyncClient() as client:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
                json=payload,
            )


slack_channel = SlackChannel()