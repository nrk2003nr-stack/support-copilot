from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from .models import User
from .schemas import UserCreate, UserLogin, UserOut, TokenResponse, RefreshRequest, PasswordChange
from ..tickets import models as ticket_models  # noqa: F401 - registers SQLAlchemy relationships

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        access_token = create_access_token({"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )
    except Exception as e:
        # Temporary: write exception to a local file for debugging
        try:
            with open('tmp_register_error.log', 'a', encoding='utf-8') as f:
                import traceback

                f.write('\n--- Exception during register ---\n')
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.patch("/me/language")
def update_language(
    language: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.preferred_language = language
    db.commit()
    return {"message": f"Language set to {language}"}
