from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    agent = "agent"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    preferred_language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tickets_created = relationship("Ticket", foreign_keys="Ticket.user_id", back_populates="user")
    tickets_assigned = relationship("Ticket", foreign_keys="Ticket.agent_id", back_populates="agent")
    messages = relationship("Message", back_populates="user")