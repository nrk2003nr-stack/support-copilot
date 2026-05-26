import chromadb
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.orm import Session
import models
import os
from datetime import datetime

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
embeddings = OpenAIEmbeddings()

def get_kb_collection():
    return chroma_client.get_or_create_collection("knowledge_base")

def add_to_knowledge_base(question: str, answer: str, source_ticket_id: int, approved_by: int, db: Session):
    """
    Called when an agent resolves a ticket and marks it for KB ingestion.
    Adds Q&A pair to both SQLite (for audit) and ChromaDB (for RAG).
    """
    # 1. Store in SQLite
    entry = models.KnowledgeEntry(
        question=question,
        answer=answer,
        source_ticket_id=source_ticket_id,
        approved_by=approved_by,
        added_to_chroma=False,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # 2. Add to ChromaDB
    try:
        collection = get_kb_collection()
        doc_text = f"Q: {question}\nA: {answer}"
        embedding_vector = embeddings.embed_query(doc_text)
        collection.add(
            ids=[f"kb_{entry.id}"],
            documents=[doc_text],
            embeddings=[embedding_vector],
            metadatas=[{
                "source": "agent_resolution",
                "ticket_id": source_ticket_id,
                "created_at": entry.created_at.isoformat()
            }]
        )
        entry.added_to_chroma = True
        db.commit()
    except Exception as e:
        print(f"ChromaDB ingestion failed: {e}")

    return entry

def search_knowledge_base(query: str, n_results: int = 3) -> list[str]:
    """Used by the LangGraph agent to answer questions from curated KB"""
    collection = get_kb_collection()
    query_embedding = embeddings.embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents"]
    )
    return results["documents"][0] if results["documents"] else []