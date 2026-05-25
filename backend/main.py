from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.db.database import engine
from backend.db import models
from backend.routers import tickets, agent, knowledge, memory
from backend.routers.auth import router as auth_router
from backend.routers.escalation import router as escalation_router
from backend.routers.feedback import router as feedback_router
from backend.routers.notifications import router as notifications_router
from backend.routers.admin_router import router as admin_router

# Create all 10 SQLite tables on startup
models.Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Support Copilot API starting up...")
    print("📊 All 10 database tables initialized")
    yield
    print("🛑 Support Copilot API shutting down...")


app = FastAPI(
    title="AI Customer Support Copilot API",
    description="RAG + ChromaDB + Mem0 + LangGraph powered support automation",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Original routers
app.include_router(tickets.router)
app.include_router(agent.router)
app.include_router(knowledge.router)
app.include_router(memory.router)

# New routers (Phase 2 upgrade)
app.include_router(auth_router)
app.include_router(escalation_router)
app.include_router(feedback_router)
app.include_router(notifications_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "status": "online",
        "version": "2.0.0",
        "modules": [
            "Tickets", "AI Agent", "Knowledge Base", "Memory",
            "Auth", "Escalations", "Feedback", "Notifications", "Admin"
        ],
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}