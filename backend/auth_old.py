from datetime import datetime, timedelta
from typing import Optional
import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import models
from database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
auth_router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: models.UserRole = models.UserRole.customer


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: dict


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _user_payload(user: models.User) -> dict:
    role = user.role.value if hasattr(user.role, "value") else user.role
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": role,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


def audit(db: Session, event_type: str, user_id: Optional[int] = None, details: Optional[dict] = None) -> None:
    db.add(models.AuditEvent(
        event_type=event_type,
        user_id=user_id,
        details=json.dumps(details or {}),
    ))


def create_access_token(user: models.User, db: Session, request: Optional[Request] = None) -> tuple[str, datetime]:
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    session = models.AuthSession(
        jti=jti,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(session)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "jti": jti,
            "exp": expires_at,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token, expires_at


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        if not jti:
            raise credentials_exception
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    session = db.query(models.AuthSession).filter(models.AuthSession.jti == jti).first()
    if not session or session.revoked_at or session.expires_at <= datetime.utcnow():
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_session(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return db.query(models.AuthSession).filter(models.AuthSession.jti == payload.get("jti")).first()
    except JWTError:
        return None


def require_role(*roles: str):
    async def role_checker(current_user=Depends(get_current_user)):
        user_role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker


@auth_router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if req.role != models.UserRole.customer:
        existing_admin = db.query(models.User).filter(models.User.role == models.UserRole.admin).first()
        if existing_admin:
            raise HTTPException(status_code=403, detail="Only admins can create privileged users")
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    user = models.User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    db.flush()
    token, expires_at = create_access_token(user, db, request)
    audit(db, "auth.register", user.id)
    db.commit()
    db.refresh(user)
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": _user_payload(user)}


@auth_router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        audit(db, "auth.login_failed", details={"email": req.email})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_at = create_access_token(user, db, request)
    audit(db, "auth.login", user.id)
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": _user_payload(user)}


@auth_router.post("/logout")
def logout(session=Depends(get_current_session), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if session and not session.revoked_at:
        session.revoked_at = datetime.utcnow()
    audit(db, "auth.logout", current_user.id)
    db.commit()
    return {"message": "Logged out"}


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, session=Depends(get_current_session), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if session and not session.revoked_at:
        session.revoked_at = datetime.utcnow()
    token, expires_at = create_access_token(current_user, db, request)
    audit(db, "auth.refresh", current_user.id)
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": _user_payload(current_user)}


@auth_router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return _user_payload(current_user)
