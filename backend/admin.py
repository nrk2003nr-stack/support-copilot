from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from auth import hash_password, require_role
from database import get_db

admin_router = APIRouter(prefix="/admin", tags=["admin"])


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    role: str = "agent"


@admin_router.get("/users")
def list_users(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@admin_router.post("/users")
def create_user(req: UserCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = models.User(email=req.email, username=req.username, hashed_password=hash_password(req.password), role=req.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@admin_router.patch("/users/{user_id}")
def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    db.commit()
    db.refresh(user)
    return user


@admin_router.get("/config")
def config(_=Depends(require_role("admin"))):
    return {
        "features": {
            "openai": False,
            "mock_channels": True,
            "voice_upload": True,
            "vision_upload": True,
            "kb_review_required": True,
        },
        "sla_hours": {"urgent": 4, "high": 12, "medium": 24, "low": 72},
    }
