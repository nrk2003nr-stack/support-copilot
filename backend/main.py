from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.db.database import engine
from backend.db import models
from backend.routers import tickets, agent, knowledge, memory

# Create all SQLite tables on startup
models.Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Support Copilot API starting up...")
    yield
    print("🛑 Support Copilot API shutting down...")


app = FastAPI(
    title="AI Customer Support Copilot API",
    description="RAG + Mem0 + LangGraph powered support automation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
app.include_router(agent.router)
app.include_router(knowledge.router)
app.include_router(memory.router)


@app.get("/")
def root():
    return {
        "status":  "ok",
        "message": "AI Customer Support Copilot API",
        "docs":    "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}