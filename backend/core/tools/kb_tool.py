"""
Knowledge Base Tool — exposes RAG search as a LangChain tool
so the agent can call it during its reasoning loop.
"""

from langchain_core.tools import tool
from backend.core.rag_engine import search_knowledge_base

@tool
def search_kb(query: str) -> str:
    """
    Search the internal knowledge base for answers to support questions.
    Use this when you need to find product documentation, policies, or FAQs.
    Returns the most relevant answer and its source documents.
    """
    result = search_knowledge_base(query)
    answer = result.get("answer", "No relevant information found.")
    sources = result.get("sources", [])
    if sources:
        return f"{answer}\n\nSources: {', '.join(sources)}"
    return answer