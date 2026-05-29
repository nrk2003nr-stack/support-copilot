"""Initial tables — users, tickets, messages

Revision ID: 001_initial
Revises:
Create Date: 2026-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "agent", "user", name="userrole"), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("preferred_language", sa.String(10), server_default="en"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.Enum("open","pending_agent","in_progress","resolved","closed", name="ticketstatus"), server_default="open"),
        sa.Column("priority", sa.Enum("low","medium","high","urgent", name="ticketpriority"), server_default="medium"),
        sa.Column("channel", sa.Enum("web","email","whatsapp","slack", name="channeltype"), server_default="web"),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("urgency_score", sa.Integer, server_default="3"),
        sa.Column("csat_score", sa.Integer, nullable=True),
        sa.Column("is_frustrated", sa.Boolean, server_default="false"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("role", sa.Enum("user","bot","agent","system", name="messagerole"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("feedback", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_messages_ticket_id", "messages", ["ticket_id"])


def downgrade():
    op.drop_table("messages")
    op.drop_table("tickets")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS channeltype")
    op.execute("DROP TYPE IF EXISTS ticketpriority")
    op.execute("DROP TYPE IF EXISTS ticketstatus")
    op.execute("DROP TYPE IF EXISTS userrole")