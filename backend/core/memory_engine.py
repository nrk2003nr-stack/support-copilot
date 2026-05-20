import os
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MEM0_CHROMA_DIR = os.getenv("MEM0_CHROMA_DIR", "./mem0_db")

# We bypass Mem0's LLM layer entirely and use ChromaDB directly.
# This makes memory save/retrieve fast and reliable with Ollama.

_chroma_client = None
_collection    = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        from chromadb.config import Settings

        os.makedirs(MEM0_CHROMA_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=MEM0_CHROMA_DIR)
        _collection    = _chroma_client.get_or_create_collection(
            name="customer_memories",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _embed(text: str) -> List[float]:
    """Generate embedding via Ollama."""
    from langchain_ollama import OllamaEmbeddings
    embedder = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
    return embedder.embed_query(text)


def get_customer_context(customer_id: str, query: str) -> str:
    """Retrieve the top-5 most relevant memories for a customer."""
    try:
        collection = _get_collection()
        count = collection.count()
        if count == 0:
            return "No previous interaction history found for this customer."

        query_embedding = _embed(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(5, count),
            where={"customer_id": customer_id},
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            return "No previous interaction history found for this customer."

        context_lines = [f"- {doc}" for doc in docs]
        return "Customer history:\n" + "\n".join(context_lines)

    except Exception as e:
        print(f"Warning: could not retrieve memories for {customer_id}: {e}")
        return "Memory retrieval unavailable."


def save_interaction_memory(
    customer_id: str,
    ticket_subject: str,
    customer_message: str,
    agent_response: str,
):
    """
    Save interaction facts directly to ChromaDB — no LLM processing needed.
    Fast, reliable, and immune to Ollama timeouts.
    """
    try:
        collection = _get_collection()
        now        = datetime.now(timezone.utc).isoformat()

        memories = [
            f"Ticket subject: {ticket_subject}",
            f"Customer issue: {customer_message[:400]}",
            f"Resolution provided: {agent_response[:400]}",
        ]

        for memory_text in memories:
            embedding = _embed(memory_text)
            collection.add(
                ids=[str(uuid.uuid4())],
                embeddings=[embedding],
                documents=[memory_text],
                metadatas=[{
                    "customer_id": customer_id,
                    "ticket_subject": ticket_subject,
                    "created_at": now,
                }],
            )

        print(f"✅ Memory saved for {customer_id} — {ticket_subject}")

    except Exception as e:
        print(f"Warning: could not save memory for {customer_id}: {e}")


def get_all_customer_memories(customer_id: str) -> List[Dict]:
    """Return all memories stored for a customer."""
    try:
        collection = _get_collection()
        count      = collection.count()
        if count == 0:
            return []

        results = collection.get(
            where={"customer_id": customer_id},
            include=["documents", "metadatas"],
        )

        memories = []
        docs      = results.get("documents", [])
        metas     = results.get("metadatas", [])
        ids       = results.get("ids", [])

        for i, doc in enumerate(docs):
            memories.append({
                "id":         ids[i] if i < len(ids) else str(i),
                "memory":     doc,
                "created_at": metas[i].get("created_at", "") if i < len(metas) else "",
                "user_id":    customer_id,
            })

        # Sort newest first
        memories.sort(key=lambda x: x["created_at"], reverse=True)
        return memories

    except Exception as e:
        print(f"Warning: could not retrieve memories for {customer_id}: {e}")
        return []


def delete_customer_memory(customer_id: str):
    """GDPR-compliant: delete all memories for a customer."""
    try:
        collection = _get_collection()
        results    = collection.get(where={"customer_id": customer_id})
        ids        = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        print(f"🗑️ Deleted {len(ids)} memories for {customer_id}")
    except Exception as e:
        print(f"Warning: could not delete memories for {customer_id}: {e}")