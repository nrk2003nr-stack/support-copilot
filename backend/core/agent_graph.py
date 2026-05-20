import os
from typing import TypedDict
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from backend.core.tools.crm_tool import lookup_crm
from backend.core.tools.billing_tool import lookup_billing
from backend.core.memory_engine import get_customer_context

load_dotenv()

CHAT_MODEL      = os.getenv("CHAT_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ── Agent State ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    customer_id:        str
    customer_name:      str
    ticket_subject:     str
    ticket_description: str
    crm_data:           dict
    billing_data:       dict
    kb_answer:          str
    kb_sources:         list
    memory_context:     str
    draft_response:     str


# ── Shared LLM instance ───────────────────────────────────────────────────────
def get_llm():
    return ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,
    )


# ── Node 1: Fetch CRM + Billing ───────────────────────────────────────────────
def gather_crm_billing(state: AgentState) -> AgentState:
    customer_id    = state["customer_id"]
    crm_result     = lookup_crm.invoke({"customer_id": customer_id})
    billing_result = lookup_billing.invoke({"customer_id": customer_id})
    return {
        **state,
        "crm_data":     crm_result     if isinstance(crm_result, dict)     else {},
        "billing_data": billing_result if isinstance(billing_result, dict) else {},
    }


# ── Node 2: RAG search + Mem0 memory ─────────────────────────────────────────
def gather_kb_and_memory(state: AgentState) -> AgentState:
    from backend.core.rag_engine import search_knowledge_base
    query      = f"{state['ticket_subject']}: {state['ticket_description']}"
    kb_result  = search_knowledge_base(query)
    memory_ctx = get_customer_context(customer_id=state["customer_id"], query=query)
    return {
        **state,
        "kb_answer":      kb_result.get("answer", ""),
        "kb_sources":     kb_result.get("sources", []),
        "memory_context": memory_ctx,
    }


# ── Node 3: Generate draft response ──────────────────────────────────────────
def generate_draft_response(state: AgentState) -> AgentState:
    crm     = state.get("crm_data", {})
    billing = state.get("billing_data", {})
    llm     = get_llm()

    system_prompt = (
        "You are an expert customer support agent assistant. "
        "Draft a helpful, professional, and empathetic response to a customer support ticket. "
        "Use only the data provided below — do not make up information.\n\n"
        f"CUSTOMER PROFILE:\n"
        f"- Name: {state['customer_name']}\n"
        f"- Plan: {crm.get('plan', 'Unknown')}\n"
        f"- Account Health: {crm.get('health_score', 'Unknown')}\n"
        f"- Billing Status: {billing.get('status', 'Unknown')}\n"
        f"- Outstanding Amount: {billing.get('outstanding_amount', 0)}\n\n"
        f"CUSTOMER MEMORY (past interactions):\n{state['memory_context']}\n\n"
        f"KNOWLEDGE BASE ANSWER:\n{state['kb_answer']}\n\n"
        "Write a response that:\n"
        "1. Greets the customer by first name\n"
        "2. Acknowledges their specific issue\n"
        "3. Provides a clear solution using the knowledge base answer\n"
        "4. Mentions billing or account concerns if relevant\n"
        "5. Closes professionally with next steps"
    )

    human_msg = (
        f"Ticket Subject: {state['ticket_subject']}\n"
        f"Customer Message: {state['ticket_description']}\n\n"
        "Draft a support response:"
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_msg),
    ])

    return {**state, "draft_response": response.content}


# ── Build the graph ───────────────────────────────────────────────────────────
def build_support_agent():
    builder = StateGraph(AgentState)
    builder.add_node("gather_crm_billing",    gather_crm_billing)
    builder.add_node("gather_kb_and_memory",  gather_kb_and_memory)
    builder.add_node("generate_draft_response", generate_draft_response)

    builder.set_entry_point("gather_crm_billing")
    builder.add_edge("gather_crm_billing",    "gather_kb_and_memory")
    builder.add_edge("gather_kb_and_memory",  "generate_draft_response")
    builder.add_edge("generate_draft_response", END)

    return builder.compile()


_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = build_support_agent()
    return _agent


def run_agent(
    customer_id: str,
    customer_name: str,
    ticket_subject: str,
    ticket_description: str,
) -> dict:
    agent = get_agent()
    initial_state = AgentState(
        customer_id=customer_id,
        customer_name=customer_name,
        ticket_subject=ticket_subject,
        ticket_description=ticket_description,
        crm_data={},
        billing_data={},
        kb_answer="",
        kb_sources=[],
        memory_context="",
        draft_response="",
    )
    final_state = agent.invoke(initial_state)
    return {
        "draft_response": final_state["draft_response"],
        "kb_sources":     final_state["kb_sources"],
        "memory_context": final_state["memory_context"],
        "crm_data":       final_state["crm_data"],
        "billing_data":   final_state["billing_data"],
    }