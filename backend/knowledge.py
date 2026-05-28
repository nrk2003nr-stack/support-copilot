from datetime import datetime
import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import require_role
from database import get_db
import models

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeCreate(BaseModel):
    question: str = Field(..., min_length=3)
    answer: str = Field(..., min_length=3)
    product: str = "general"
    topic: str = "support"
    language: str = "en"
    status: str = "draft"
    source_ticket_id: Optional[int] = None


class KnowledgeUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    product: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _openai_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _get_chroma_collection():
    if not _openai_enabled():
        return None, None
    try:
        import chromadb
        from langchain_openai import OpenAIEmbeddings
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        return client.get_or_create_collection("knowledge_base"), OpenAIEmbeddings()
    except Exception:
        return None, None


def add_to_knowledge_base(
    question: str,
    answer: str,
    source_ticket_id: Optional[int],
    approved_by: Optional[int],
    db: Session,
    status: str = "draft",
    product: str = "general",
    topic: str = "support",
    language: str = "en",
):
    entry = models.KnowledgeEntry(
        question=question,
        answer=answer,
        source_ticket_id=source_ticket_id,
        approved_by=approved_by if status == "approved" else None,
        added_to_chroma=False,
        product=product,
        topic=topic,
        language=language,
        source="agent_resolution" if source_ticket_id else "manual",
        status=status,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    if status == "approved":
        publish_to_chroma(entry, db)
    return entry


def publish_to_chroma(entry: models.KnowledgeEntry, db: Session) -> models.KnowledgeEntry:
    collection, embeddings = _get_chroma_collection()
    if not collection or not embeddings:
        return entry
    try:
        doc_text = f"Q: {entry.question}\nA: {entry.answer}"
        collection.upsert(
            ids=[f"kb_{entry.id}"],
            documents=[doc_text],
            embeddings=[embeddings.embed_query(doc_text)],
            metadatas=[{
                "source": entry.source,
                "ticket_id": entry.source_ticket_id or "",
                "product": entry.product,
                "topic": entry.topic,
                "language": entry.language,
                "status": entry.status,
            }],
        )
        entry.added_to_chroma = True
        db.commit()
    except Exception:
        db.rollback()
    return entry


def search_knowledge_base(query: str, db: Optional[Session] = None, n_results: int = 3, language: Optional[str] = None) -> list[str]:
    collection, embeddings = _get_chroma_collection()
    if collection and embeddings:
        try:
            where = {"status": "approved"}
            if language:
                where["language"] = language
            results = collection.query(
                query_embeddings=[embeddings.embed_query(query)],
                n_results=n_results,
                where=where,
                include=["documents"],
            )
            docs = results.get("documents") or []
            if docs and docs[0]:
                return docs[0]
        except Exception:
            pass
    if not db:
        return []
    query_terms = _tokenize(query)
    entries = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.status == "approved").all()
    scored = []
    for entry in entries:
        if language and entry.language != language:
            continue
        text = f"{entry.question} {entry.answer}"
        score = len(query_terms & _tokenize(text))
        if score:
            scored.append((score, f"Q: {entry.question}\nA: {entry.answer}"))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in scored[:n_results]]


@knowledge_router.get("/")
def list_entries(status: Optional[str] = None, db: Session = Depends(get_db), _=Depends(require_role("agent", "admin"))):
    query = db.query(models.KnowledgeEntry)
    if status:
        query = query.filter(models.KnowledgeEntry.status == status)
    return query.order_by(models.KnowledgeEntry.created_at.desc()).all()


@knowledge_router.post("/")
def create_entry(req: KnowledgeCreate, db: Session = Depends(get_db), current_user=Depends(require_role("agent", "admin"))):
    return add_to_knowledge_base(**req.model_dump(), approved_by=current_user.id if req.status == "approved" else None, db=db)


@knowledge_router.patch("/{entry_id}")
def update_entry(entry_id: int, req: KnowledgeUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)
    if entry.status == "approved":
        entry.approved_by = current_user.id
    db.commit()
    db.refresh(entry)
    if entry.status == "approved":
        publish_to_chroma(entry, db)
    return entry


@knowledge_router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted"}
