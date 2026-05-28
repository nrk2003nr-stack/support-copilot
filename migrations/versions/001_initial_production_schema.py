"""initial production schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        return
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="customer"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
    )


def downgrade():
    op.drop_table("users")
