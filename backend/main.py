from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid, json, os

# Internal modules
from database import engine, get_db
import models
from auth import auth_router, get_current_user
from tickets import ticket_router
from handoff import handoff_router
from vision import vision_router
from analytics import analytics_router
from sentiment import analyze_sentiment, should_escalate
from knowledge import search_knowledge_base

# LangChain / LangGraph
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from mem0 import Memory

# Create all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Support Copilot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production to your domain
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

# Core LLM setup
llm = ChatOpenAI(model="gpt-4o", streaming=True)
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
mem0_memory = Memory()

# ────────────────────────────────────────────
# Chat endpoint
# ────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    conversation_id: int
    sentiment: dict
    escalation_recommended: bool
    sources: list[str]

@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
            session_id=session_id
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 3. Sentiment analysis
    sentiment = analyze_sentiment(req.message)

    # 4. Save user message
    user_msg = models.Message(
        conversation_id=conv.id,
        role="user",
        content=req.message,
        sentiment_score=sentiment["normalized"]
    )
    db.add(user_msg)
    db.commit()

    # 5. Check if escalation is needed
    recent_scores = [
        m.sentiment_score for m in db.query(models.Message)
        .filter(models.Message.conversation_id == conv.id, models.Message.role == "user")
        .order_by(models.Message.timestamp.desc()).limit(3).all()
        if m.sentiment_score is not None
    ]
    escalation_needed = should_escalate(recent_scores)

    # 6. Retrieve context from ChromaDB (RAG)
    kb_results = search_knowledge_base(req.message)
    vector_results = vectorstore.similarity_search(req.message, k=3)
    context_docs = kb_results + [doc.page_content for doc in vector_results]
    context_text = "\n\n".join(context_docs[:4]) if context_docs else "No relevant documents found."

    # 7. Retrieve user memory from mem0
    memories = mem0_memory.search(req.message, user_id=str(current_user.id))
    memory_text = "\n".join([m["memory"] for m in memories[:3]]) if memories else ""

    # 8. Build LangChain messages
    system_prompt = f"""You are a helpful, empathetic support copilot.
Use the following context from the knowledge base to answer accurately:

KNOWLEDGE BASE CONTEXT:
{context_text}

USER MEMORY (past interactions):
{memory_text}

Rules:
- Be concise, helpful, and friendly.
- If you cannot resolve the issue, say so clearly and offer to create a support ticket.
- If the user seems upset, acknowledge their frustration before answering.
- If escalation is needed, mention that a human agent can help.
"""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=req.message)]
    response = await llm.ainvoke(messages)
    reply = response.content

    # 9. Save assistant reply
    assistant_msg = models.Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply
    )
    db.add(assistant_msg)

    # 10. Store in mem0 memory
    mem0_memory.add(req.message, user_id=str(current_user.id))

    # 11. Auto-summarize every 10 messages
    msg_count = db.query(models.Message).filter(
        models.Message.conversation_id == conv.id
    ).count()
    if msg_count % 10 == 0:
        summary_resp = await llm.ainvoke([
            SystemMessage(content="Summarize this support conversation in 2-3 sentences."),
            HumanMessage(content=f"Conversation so far:\n{req.message}\n\nAssistant:\n{reply}")
        ])
        conv.summary = summary_resp.content

    # 12. Update conversation sentiment avg
    conv.sentiment_score = (conv.sentiment_score + sentiment["normalized"]) / 2
    if escalation_needed:
        conv.escalated = True

    db.commit()

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        conversation_id=conv.id,
        sentiment=sentiment,
        escalation_recommended=escalation_needed,
        sources=[doc.metadata.get("source", "KB") for doc in vector_results[:2]]
    )

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}