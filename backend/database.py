from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./support.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def _sqlite_columns(table_name: str) -> set[str]:
    if not DATABASE_URL.startswith("sqlite"):
        return set()
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}

def _add_sqlite_column(table_name: str, column_name: str, ddl: str) -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    if column_name in _sqlite_columns(table_name):
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))

def migrate_sqlite_schema() -> None:
    """Small local-dev migration shim for existing SQLite databases.

    Alembic can be introduced later for production migrations; this keeps old
    demo DBs from crashing after adding nullable production fields.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    for table, columns in {
        "conversations": {
            "ticket_id": "INTEGER",
            "channel": "VARCHAR DEFAULT 'web'",
            "language": "VARCHAR DEFAULT 'en'",
            "human_active": "BOOLEAN DEFAULT 0",
        },
        "messages": {
            "channel": "VARCHAR DEFAULT 'web'",
            "language": "VARCHAR DEFAULT 'en'",
        },
        "tickets": {
            "sla_due_at": "DATETIME",
            "tags": "VARCHAR DEFAULT ''",
            "channel": "VARCHAR DEFAULT 'web'",
            "language": "VARCHAR DEFAULT 'en'",
            "sentiment": "FLOAT DEFAULT 0.0",
        },
        "knowledge_entries": {
            "product": "VARCHAR DEFAULT 'general'",
            "topic": "VARCHAR DEFAULT 'support'",
            "language": "VARCHAR DEFAULT 'en'",
            "source": "VARCHAR DEFAULT 'agent_resolution'",
            "status": "VARCHAR DEFAULT 'draft'",
        },
    }.items():
        for column, ddl in columns.items():
            _add_sqlite_column(table, column, ddl)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
