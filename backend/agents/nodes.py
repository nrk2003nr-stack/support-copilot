"""
New LangGraph nodes to add to your existing graph.
Import these into your existing graph.py and wire them in.
"""
from typing import TypedDict, Optional, List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_smart = ChatOpenAI(model="gpt-4o", temperature=0.3)


# ─── Shared state schema ────────────────────────────────────────────────────

class AgentState(TypedDict):
    ticket_id: str
    user_id: str
    messages: List[dict]          # [{"role": "user"|"bot"|"agent", "content": "..."}]
    user_query: str
    bot_response: str
    detected_language: str
    sentiment_score: float         # -1.0 to 1.0
    sentiment_emotion: str
    consecutive_negative: int      # how many negative messages in a row
    should_handoff: bool
    urgency_score: int             # 1-5
    summary: Optional[str]
    kb_context: Optional[str]      # RAG results from ChromaDB


# ─── Language detection node ────────────────────────────────────────────────

def language_detect_node(state: AgentState) -> AgentState:
    """Detect language of user query. Fast and cheap with gpt-4o-mini."""
    response = llm.invoke([
        SystemMessage(content=(
            "Detect the language of the text. "
            "Reply only with a JSON object: {\"language\": \"<ISO 639-1 code>\"}. "
            "Examples: en, es, fr, de, ar, hi, ta, ml"
        )),
        HumanMessage(content=state["user_query"]),
    ])
    try:
        data = json.loads(response.content)
        lang = data.get("language", "en")
    except Exception:
        lang = "en"
    return {**state, "detected_language": lang}


# ─── Sentiment analysis node ─────────────────────────────────────────────────

def sentiment_node(state: AgentState) -> AgentState:
    """Score sentiment of the latest user message. Updates frustrated flag."""
    response = llm.invoke([
        SystemMessage(content=(
            "Analyze the sentiment of this support message. "
            "Reply only with JSON: {\"score\": <float -1.0 to 1.0>, \"emotion\": \"<one word>\"}. "
            "Score: -1 = very angry/frustrated, 0 = neutral, 1 = very happy/satisfied."
        )),
        HumanMessage(content=state["user_query"]),
    ])
    try:
        data = json.loads(response.content)
        score = float(data.get("score", 0))
        emotion = data.get("emotion", "neutral")
    except Exception:
        score = 0.0
        emotion = "neutral"

    consecutive = state.get("consecutive_negative", 0)
    if score < -0.5:
        consecutive += 1
    else:
        consecutive = 0

    return {
        **state,
        "sentiment_score": score,
        "sentiment_emotion": emotion,
        "consecutive_negative": consecutive,
    }


# ─── Urgency scoring node ────────────────────────────────────────────────────

def urgency_node(state: AgentState) -> AgentState:
    """Score urgency 1-5 based on message content."""
    response = llm.invoke([
        SystemMessage(content=(
            "Rate the urgency of this support message from 1 (low) to 5 (critical). "
            "Consider: anger, billing issues, service outages, data loss, VIP signals. "
            "Reply only with JSON: {\"urgency\": <int 1-5>}"
        )),
        HumanMessage(content=state["user_query"]),
    ])
    try:
        data = json.loads(response.content)
        urgency = int(data.get("urgency", 3))
    except Exception:
        urgency = 3

    return {**state, "urgency_score": urgency}


# ─── Handoff decision node ───────────────────────────────────────────────────

def handoff_check_node(state: AgentState) -> AgentState:
    """Decide if this ticket should be handed off to a human agent."""
    should_handoff = False

    # Rule 1: Very negative sentiment for 2+ messages
    if state.get("consecutive_negative", 0) >= 2:
        should_handoff = True

    # Rule 2: Critical urgency
    if state.get("urgency_score", 3) >= 5:
        should_handoff = True

    # Rule 3: User explicitly asks for human
    query_lower = state["user_query"].lower()
    human_keywords = ["human", "agent", "person", "representative", "speak to someone", "real person"]
    if any(kw in query_lower for kw in human_keywords):
        should_handoff = True

    return {**state, "should_handoff": should_handoff}


# ─── RAG node (integrates with your existing ChromaDB) ───────────────────────

def rag_node(state: AgentState, chroma_collection) -> AgentState:
    """Retrieve relevant KB articles from ChromaDB."""
    results = chroma_collection.query(
        query_texts=[state["user_query"]],
        n_results=3,
    )
    docs = results.get("documents", [[]])[0]
    kb_context = "\n\n".join(docs) if docs else ""
    return {**state, "kb_context": kb_context}


# ─── Response generation node ────────────────────────────────────────────────

def generate_response_node(state: AgentState) -> AgentState:
    """Generate bot response in the user's detected language using KB context."""
    lang = state.get("detected_language", "en")
    kb_context = state.get("kb_context", "")
    history = state.get("messages", [])[-6:]  # last 3 exchanges for context

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )

    system_prompt = f"""You are a helpful, empathetic customer support agent.
Always respond in language code: {lang}.
{"Use this knowledge base context to answer:\n" + kb_context if kb_context else ""}
Conversation so far:
{history_text}
Be concise, friendly, and solution-focused."""

    response = llm_smart.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_query"]),
    ])

    return {**state, "bot_response": response.content}


# ─── Handoff message node ────────────────────────────────────────────────────

def handoff_message_node(state: AgentState) -> AgentState:
    """Generate a friendly handoff message and trigger agent notification."""
    lang = state.get("detected_language", "en")
    response = llm.invoke([
        SystemMessage(content=f"Write a brief, empathetic message in language {lang} telling the user they're being connected to a live support agent. Keep it under 2 sentences."),
        HumanMessage(content="Generate handoff message"),
    ])
    return {**state, "bot_response": response.content}


# ─── Summary generation node ─────────────────────────────────────────────────

def summary_node(state: AgentState) -> AgentState:
    """Generate a post-resolution summary of the ticket conversation."""
    history = state.get("messages", [])
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )
    response = llm.invoke([
        SystemMessage(content=(
            "Summarize this support conversation in 2-3 sentences. "
            "Include: the user's issue, how it was resolved, and any follow-up needed. "
            "Be concise and professional."
        )),
        HumanMessage(content=history_text),
    ])
    return {**state, "summary": response.content}


# ─── KB auto-update extraction ───────────────────────────────────────────────

def extract_kb_article(conversation_history: list, csat_score: int) -> Optional[dict]:
    """
    Call this after a ticket is resolved with CSAT >= 4.
    Returns a KB article dict or None if not suitable.
    """
    if csat_score < 4:
        return None

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation_history
    )

    response = llm.invoke([
        SystemMessage(content=(
            "Extract a knowledge base article from this resolved support conversation. "
            "Reply only with JSON: {\"question\": \"...\", \"answer\": \"...\", \"category\": \"...\"}. "
            "If the conversation doesn't contain a reusable answer, reply with {\"skip\": true}."
        )),
        HumanMessage(content=history_text),
    ])

    try:
        data = json.loads(response.content)
        if data.get("skip"):
            return None
        return data
    except Exception:
        return None