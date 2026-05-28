from datetime import datetime, timedelta
import os
import re
from typing import Annotated, Optional, TypedDict

from sqlalchemy.orm import Session

import models
from knowledge import search_knowledge_base
from sentiment import analyze_sentiment, contains_handoff_request, should_escalate

try:
    from langgraph.graph import END, StateGraph
    from langgraph.graph.message import add_messages
except Exception:
    END = None
    StateGraph = None


class AgentState(TypedDict):
    messages: Annotated[list, add_messages] if StateGraph else list
    user_id: int
    session_id: str
    conversation_id: int
    ticket_id: Optional[int]
    user_message: str
    language: str
    sentiment: dict
    sentiment_history: list[float]
    escalation_recommended: bool
    confidence: float
    retrieved_context: str
    user_memory: str
    reply: str
    sources: list[str]


def detect_language(text: str) -> str:
    lowered = text.lower()
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if any(word in lowered for word in ["hola", "gracias", "ayuda"]):
        return "es"
    if any(word in lowered for word in ["bonjour", "merci", "aide"]):
        return "fr"
    return "en"


def _llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _invoke_llm(prompt: str, message: str) -> Optional[str]:
    if not _llm_enabled():
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2, timeout=20)
        return model.invoke([SystemMessage(content=prompt), HumanMessage(content=message)]).content
    except Exception:
        return None


def _memory_search(user_id: int, query: str) -> str:
    if not _llm_enabled():
        return ""
    try:
        from mem0 import Memory
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {"path": os.path.join(os.path.dirname(__file__), "mem0_storage")},
            }
        }
        memory = Memory.from_config(config)
        memories = memory.search(query, user_id=str(user_id), limit=3)
        return "\n".join(item.get("memory", "") for item in memories if item.get("memory"))
    except Exception:
        return ""


def _memory_add(user_id: int, user_message: str, reply: str) -> None:
    if not _llm_enabled():
        return
    try:
        from mem0 import Memory
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {"path": os.path.join(os.path.dirname(__file__), "mem0_storage")},
            }
        }
        memory = Memory.from_config(config)
        memory.add(f"User asked: {user_message}\nAssistant replied: {reply}", user_id=str(user_id))
    except Exception:
        return


def analyze_sentiment_node(state: AgentState) -> dict:
    sentiment = analyze_sentiment(state["user_message"])
    history = [*state.get("sentiment_history", []), sentiment["normalized"]]
    handoff = contains_handoff_request(state["user_message"])
    escalation = handoff or should_escalate(history)
    return {"sentiment": sentiment, "sentiment_history": history, "escalation_recommended": escalation}


def retrieve_context_node(state: AgentState, db: Optional[Session] = None) -> dict:
    docs = search_knowledge_base(state["user_message"], db=db, n_results=3, language=state.get("language"))
    confidence = min(0.95, 0.45 + (0.15 * len(docs))) if docs else 0.35
    return {
        "retrieved_context": "\n\n---\n\n".join(docs) if docs else "No approved knowledge base article matched this request.",
        "sources": [f"knowledge:{i + 1}" for i in range(len(docs))],
        "confidence": confidence,
    }


def retrieve_memory_node(state: AgentState) -> dict:
    return {"user_memory": _memory_search(state["user_id"], state["user_message"])}


def _fallback_reply(state: AgentState) -> str:
    language = state.get("language", "en")
    context = state.get("retrieved_context", "")
    escalation = state.get("escalation_recommended", False) or state.get("confidence", 0) < 0.45
    if context and not context.startswith("No approved"):
        answer = context.split("A:", 1)[-1].strip() if "A:" in context else context.strip()
    else:
        answer = (
            "I do not have an approved article for this yet, but I captured the details. "
            "Please share your order/account identifier, screenshots, and the exact error so support can act quickly."
        )
    if escalation:
        answer += "\n\nI can also bring a human support agent into this conversation."
    if language == "es":
        return "Gracias por escribir. " + answer
    if language == "fr":
        return "Merci pour votre message. " + answer
    if language == "hi":
        return "मैं आपकी मदद कर रहा हूं। " + answer
    return answer


def generate_reply_node(state: AgentState) -> dict:
    prompt = f"""You are an empathetic customer-support agent.
Reply in language code {state['language']} unless the user explicitly asks otherwise.
Use approved knowledge first. Be honest when context is missing.
If escalation is recommended, state that a human agent can take over.

Knowledge:
{state['retrieved_context']}

User memory:
{state['user_memory'] or 'No stored memory.'}
"""
    reply = _invoke_llm(prompt, state["user_message"]) or _fallback_reply(state)
    _memory_add(state["user_id"], state["user_message"], reply)
    return {"reply": reply}


def build_agent_graph(db: Optional[Session] = None):
    if not StateGraph:
        return None
    graph = StateGraph(AgentState)
    graph.add_node("sentiment", analyze_sentiment_node)
    graph.add_node("retrieve_context", lambda state: retrieve_context_node(state, db=db))
    graph.add_node("retrieve_memory", retrieve_memory_node)
    graph.add_node("generate", generate_reply_node)
    graph.set_entry_point("sentiment")
    graph.add_edge("sentiment", "retrieve_context")
    graph.add_edge("retrieve_context", "retrieve_memory")
    graph.add_edge("retrieve_memory", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def _invoke_graph(state: AgentState, db: Session) -> AgentState:
    graph = build_agent_graph(db)
    if graph:
        try:
            return graph.invoke(state)
        except Exception:
            pass
    state.update(analyze_sentiment_node(state))
    state.update(retrieve_context_node(state, db=db))
    state.update(retrieve_memory_node(state))
    state.update(generate_reply_node(state))
    return state


def _ensure_ticket(db: Session, conv: models.Conversation, user_message: str, sentiment: dict, language: str) -> Optional[models.Ticket]:
    if not conv.escalated and not conv.human_active:
        return conv.ticket
    if conv.ticket:
        return conv.ticket
    ticket = models.Ticket(
        title=f"Escalated conversation #{conv.id}",
        description=user_message[:2000],
        priority=models.TicketPriority.urgent if sentiment.get("is_negative") else models.TicketPriority.high,
        status=models.TicketStatus.open,
        user_id=conv.user_id,
        conversation_id=conv.id,
        sla_due_at=datetime.utcnow() + timedelta(hours=4),
        channel=conv.channel or "web",
        language=language,
        sentiment=sentiment.get("normalized", 0.0),
        tags="handoff",
    )
    db.add(ticket)
    db.flush()
    db.add(models.TicketEvent(ticket_id=ticket.id, actor_id=conv.user_id, event_type="handoff.created", payload="{}"))
    return ticket


async def run_agent(
    user_message: str,
    user_id: int,
    session_id: str,
    conversation_id: int,
    db: Session,
    sentiment_history: Optional[list[float]] = None,
    ticket_id: Optional[int] = None,
    language_override: Optional[str] = None,
) -> dict:
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    language = language_override or (conv.language if conv and conv.language else detect_language(user_message))
    initial_state: AgentState = {
        "messages": [],
        "user_id": user_id,
        "session_id": session_id,
        "conversation_id": conversation_id,
        "ticket_id": ticket_id,
        "user_message": user_message,
        "language": language,
        "sentiment": {},
        "sentiment_history": sentiment_history or [],
        "escalation_recommended": False,
        "confidence": 0.0,
        "retrieved_context": "",
        "user_memory": "",
        "reply": "",
        "sources": [],
    }
    result = _invoke_graph(initial_state, db)

    if conv:
        conv.language = language
        conv.escalated = bool(conv.escalated or result["escalation_recommended"] or result.get("confidence", 0) < 0.45)
        if conv.escalated:
            conv.human_active = True

    db.add(models.Message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        sentiment_score=result["sentiment"].get("normalized", 0.0),
        timestamp=datetime.utcnow(),
        channel=conv.channel if conv else "web",
        language=language,
    ))
    if not (conv and conv.human_active and conv.escalated and contains_handoff_request(user_message)):
        db.add(models.Message(
            conversation_id=conversation_id,
            role="assistant",
            content=result["reply"],
            timestamp=datetime.utcnow(),
            channel=conv.channel if conv else "web",
            language=language,
        ))

    ticket = _ensure_ticket(db, conv, user_message, result["sentiment"], language) if conv else None
    if conv and ticket:
        conv.ticket_id = ticket.id

    if conv:
        current = conv.sentiment_score or 0.0
        new_score = result["sentiment"].get("normalized", 0.0)
        conv.sentiment_score = round((current + new_score) / 2, 4)
        if result.get("confidence", 1.0) < 0.45:
            result["escalation_recommended"] = True
    db.commit()

    return {
        "reply": result["reply"],
        "session_id": session_id,
        "conversation_id": conversation_id,
        "ticket_id": ticket.id if ticket else ticket_id,
        "language": language,
        "confidence": result.get("confidence", 0.0),
        "sentiment": result["sentiment"],
        "escalation_recommended": result["escalation_recommended"],
        "sources": result["sources"],
        "sentiment_history": result["sentiment_history"],
    }
