"""Base channel interface — all channels implement this."""
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from ..tickets.models import Ticket, Message, TicketStatus, MessageRole, Channel
from datetime import datetime


class BaseChannel(ABC):
    channel_name: Channel

    def create_ticket_from_message(
        self,
        db: Session,
        user_id: int,
        content: str,
        channel_message_id: str = None,
        channel_metadata: dict = None,
    ) -> tuple[Ticket, Message]:
        ticket = Ticket(
            user_id=user_id,
            title=content[:80] if content else "Support Request",
            channel=self.channel_name,
            status=TicketStatus.open,
            channel_message_id=channel_message_id,
            channel_metadata=channel_metadata,
        )
        db.add(ticket)
        db.flush()

        msg = Message(
            ticket_id=ticket.id,
            user_id=user_id,
            role=MessageRole.user,
            content=content,
        )
        db.add(msg)
        db.commit()
        db.refresh(ticket)
        return ticket, msg

    @abstractmethod
    async def send_message(self, ticket: Ticket, content: str) -> None:
        pass