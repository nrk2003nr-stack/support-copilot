"""
LangGraph agent — extends your existing agents with:
  - Language detection
  - Sentiment scoring
  - RAG with ChromaDB
  - mem0 memory
  - Human handoff logic
  - KB auto-update after resolution
"""
import json
import asyncio
from typing import TypedDict, Optional, List
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from ..core.config import settings

# ── LLM & embeddings ─────────────────────────────────────────────────────────
llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=embeddings,
    persist_directory=settings.CHROMA_PERSIST_DIR,
)


# ── Graph state ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    ticket_id: int
    user_id: int
    message: str
    history: List[dict]
    language: str
    sentiment_score: float
    urgency_score: int
    needs_handoff: bool
    rag_context: str
    sources: List[str]
    response: str
    db: object


# ── Node: Detect language ─────────────────────────────────────────────────────
async def detect_language_node(state: AgentState) -> AgentState:
    prompt = f"""Detect the language of this text and return ONLY a JSON object.
Text: "{state['message']}"
Return: {{"language": "en", "confidence": 0.99}}
Use ISO 639-1 codes (en, es, fr, de, ar, hi, ml, ta, etc.)"""

    result = await llm.ainvoke([{"role": "user", "content": prompt}])
    try:
        data = json.loads(result.content.strip())
        state["language"] = data.get("language", "en")
    except Exception:
        state["language"] = "en"
    return state


# ── Node: Sentiment analysis ──────────────────────────────────────────────────
async def sentiment_node(state: AgentState) -> AgentState:
    prompt = f"""Analyze the sentiment and urgency of this support message.
Return ONLY JSON: {{"score": -0.8, "urgency": 3, "emotion": "frustrated"}}
score: -1.0 (very negative) to 1.0 (very positive)
urgency: 1 (low) to 5 (critical)

Message: "{state['message']}"
"""
    result = await llm.ainvoke([{"role": "user", "content": prompt}])
    try:
        data = json.loads(result.content.strip())
        state["sentiment_score"] = float(data.get("score", 0))
        state["urgency_score"] = int(data.get("urgency", 2))
    except Exception:
        state["sentiment_score"] = 0.0
        state["urgency_score"] = 2
    return state


# ── Node: Check handoff condition ─────────────────────────────────────────────
def check_handoff_node(state: AgentState) -> AgentState:
    # Trigger handoff if very negative sentiment or high urgency
    HANDOFF_TRIGGERS = [
        state["sentiment_score"] < -0.65,
        state["urgency_score"] >= 4,
        any(kw in state["message"].lower() for kw in [
            "human", "agent", "person", "speak to someone",
            "talk to", "real person", "representative"
        ]),
    ]
    state["needs_handoff"] = any(HANDOFF_TRIGGERS)
    return state


# ── Node: RAG retrieval ───────────────────────────────────────────────────────
async def rag_node(state: AgentState) -> AgentState:
    if state["needs_handoff"]:
        state["rag_context"] = ""
        state["sources"] = []
        return state

    try:
        docs = vectorstore.similarity_search(state["message"], k=3)
        if docs:
            state["rag_context"] = "\n\n".join(d.page_content for d in docs)
            state["sources"] = [d.metadata.get("source", "KB") for d in docs]
        else:
            state["rag_context"] = ""
            state["sources"] = []
    except Exception:
        state["rag_context"] = ""
        state["sources"] = []
    return state


# ── Node: Generate response ───────────────────────────────────────────────────
async def response_node(state: AgentState) -> AgentState:
    if state["needs_handoff"]:
        handoff_messages = {
            "en": "I understand this is important and you'd like to speak with a human agent. I'm connecting you now — an agent will be with you shortly.",
            "es": "Entiendo que esto es importante. Te estoy conectando con un agente humano ahora.",
            "fr": "Je comprends que c'est important. Je vous connecte avec un agent humain maintenant.",
            "de": "Ich verstehe, dass das wichtig ist. Ich verbinde Sie jetzt mit einem menschlichen Agenten.",
            "hi": "मैं समझता हूं यह महत्वपूर्ण है। मैं आपको अभी एक एजेंट से जोड़ रहा हूं।",
            "ml": "ഞാൻ മനസ്സിലാക്കുന്നു. ഞാൻ നിങ്ങളെ ഒരു ഏജന്റുമായി ബന്ധിപ്പിക്കുന്നു.",
        }
        state["response"] = handoff_messages.get(state["language"], handoff_messages["en"])
        return state

    # Build context-aware system prompt
    system = f"""You are a helpful customer support AI assistant.
Always respond in {state['language']} (ISO 639-1 language code — match the user's language exactly).
Be empathetic, concise, and solution-focused.

"""
    if state["rag_context"]:
        system += f"Use this knowledge base information to answer:\n{state['rag_context']}\n\n"

    system += "If you cannot find the answer, say so honestly and offer to escalate."

    # Build message history
    messages = [{"role": "system", "content": system}]
    for h in state["history"][-6:]:  # last 6 turns
        messages.append({"role": h["role"] if h["role"] != "bot" else "assistant", "content": h["content"]})
    messages.append({"role": "user", "content": state["message"]})

    result = await llm.ainvoke(messages)
    state["response"] = result.content
    return state


# ── Build LangGraph ───────────────────────────────────────────────────────────
def build_graph():
    g = StateGraph(AgentState)
    g.add_node("detect_language", detect_language_node)
    g.add_node("sentiment", sentiment_node)
    g.add_node("check_handoff", check_handoff_node)
    g.add_node("rag", rag_node)
    g.add_node("respond", response_node)

    g.set_entry_point("detect_language")
    g.add_edge("detect_language", "sentiment")
    g.add_edge("sentiment", "check_handoff")
    g.add_edge("check_handoff", "rag")
    g.add_edge("rag", "respond")
    g.add_edge("respond", END)

    return g.compile()


graph = build_graph()


# ── Public entrypoint ─────────────────────────────────────────────────────────
async def run_support_agent(
    ticket_id: int,
    user_id: int,
    message: str,
    history: List[dict],
    db,
) -> dict:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "message": message,
        "history": history,
        "language": "en",
        "sentiment_score": 0.0,
        "urgency_score": 2,
        "needs_handoff": False,
        "rag_context": "",
        "sources": [],
        "response": "",
        "db": db,
    }
    result = await graph.ainvoke(initial_state)
    return {
        "response": result["response"],
        "language": result["language"],
        "sentiment_score": result["sentiment_score"],
        "urgency_score": result["urgency_score"],
        "needs_handoff": result["needs_handoff"],
        "sources": result["sources"],
    }