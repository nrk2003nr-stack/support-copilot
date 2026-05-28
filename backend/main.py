from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import uuid, os
import time
from collections import defaultdict

# Internal modules
from database import engine, get_db, migrate_sqlite_schema, SessionLocal
import models
from auth import auth_router, get_current_user
from tickets import ticket_router
from handoff import handoff_router
from vision import vision_router
from analytics import analytics_router
from knowledge import knowledge_router
from channels import channels_router
from admin import admin_router
from voice import voice_router
from auth import hash_password

# ── CHANGED: import run_agent from chat.py instead of inline LLM code ──

# ── CHANGED: import schemas instead of defining them inline here ──
from schemas import ChatRequest, ChatResponse

# Create all tables
models.Base.metadata.create_all(bind=engine)
migrate_sqlite_schema()

def seed_demo_data():
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            users = [
                models.User(email="customer@example.com", username="customer", hashed_password=hash_password("password123"), role="customer"),
                models.User(email="agent@example.com", username="agent", hashed_password=hash_password("password123"), role="agent"),
                models.User(email="admin@example.com", username="admin", hashed_password=hash_password("password123"), role="admin"),
            ]
            db.add_all(users)
            db.commit()
        if db.query(models.KnowledgeEntry).count() == 0:
            db.add(models.KnowledgeEntry(
                question="How do I reset my password?",
                answer="Use the Forgot Password link on the login page, then follow the email instructions. If the email does not arrive within 10 minutes, check spam or open a ticket.",
                status="approved",
                product="account",
                topic="login",
                language="en",
                source="seed",
                added_to_chroma=False,
            ))
            db.commit()
    finally:
        db.close()

if os.getenv("SEED_DEMO_DATA", "true").lower() == "true":
    seed_demo_data()

app = FastAPI(title="Support Copilot API", version="2.0.0")
rate_buckets = defaultdict(list)

@app.middleware("http")
async def simple_rate_limit(request: Request, call_next):
    limited_prefixes = ("/auth/login", "/auth/register", "/chat", "/channels/")
    if request.url.path.startswith(limited_prefixes):
        key = f"{request.client.host if request.client else 'local'}:{request.url.path}"
        now = time.time()
        rate_buckets[key] = [ts for ts in rate_buckets[key] if now - ts < 60]
        limit = 30 if request.url.path.startswith("/chat") else 15
        if len(rate_buckets[key]) >= limit:
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        rate_buckets[key].append(now)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(ticket_router)
app.include_router(handoff_router)
app.include_router(vision_router)
app.include_router(analytics_router)
app.include_router(knowledge_router)
app.include_router(channels_router)
app.include_router(admin_router)
app.include_router(voice_router)

# ── REMOVED: llm, embeddings, vectorstore, mem0_memory setup ──
# These are now inside chat.py. main.py no longer needs them.

# ── REMOVED: the inline ChatRequest and ChatResponse class definitions ──
# They now live in schemas.py and are imported above.


# ────────────────────────────────────────────
# Chat endpoint
# ────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from chat import run_agent

    # 1. Session management
    session_id = req.session_id or str(uuid.uuid4())

    # 2. Get or create conversation
    conv = None
    if req.conversation_id:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == req.conversation_id
        ).first()

    if not conv:
        conv = models.Conversation(
            user_id=current_user.id,
            session_id=session_id,
            ticket_id=req.ticket_id,
            language=req.language or "en",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 3. Get recent sentiment scores for escalation check
    recent_scores = [
        m.sentiment_score for m in db.query(models.Message)
        .filter(
            models.Message.conversation_id == conv.id,
            models.Message.role == "user"
        )
        .order_by(models.Message.timestamp.desc()).limit(3).all()
        if m.sentiment_score is not None
    ]

    # ── CHANGED: replaced steps 3–12 with a single run_agent() call ──
    # chat.py handles: sentiment, RAG retrieval, mem0 memory,
    # LLM generation, DB persistence, auto-summarize, escalation.
    result = await run_agent(
        user_message=req.message,
        user_id=current_user.id,
        session_id=session_id,
        conversation_id=conv.id,
        db=db,
        sentiment_history=recent_scores,
        ticket_id=req.ticket_id or conv.ticket_id,
        language_override=req.language,
    )

    return ChatResponse(**result)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
