from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import shutil
import tempfile

from backend.db.database import get_db
from backend.db.models import KnowledgeDocument
from backend.core.rag_engine import ingest_document, get_collection_count

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_TYPES = {".pdf", ".docx", ".txt", ".md"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and index a support document into ChromaDB."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {ALLOWED_TYPES}",
        )

    # Write to a temp file so loaders can read from disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        chunk_count = ingest_document(tmp_path, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

    # Record the upload in SQLite
    doc = KnowledgeDocument(
        filename=file.filename,
        file_type=ext,
        chunk_count=chunk_count,
    )
    db.add(doc)
    db.commit()

    return {
        "filename": file.filename,
        "chunks_indexed": chunk_count,
        "total_kb_chunks": get_collection_count(),
    }


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    """List all indexed knowledge base documents."""
    return db.query(KnowledgeDocument).order_by(
        KnowledgeDocument.uploaded_at.desc()
    ).all()


@router.get("/stats")
def kb_stats():
    """Return ChromaDB vector count and status."""
    count = get_collection_count()
    return {
        "total_vectors": count,
        "status": "ready" if count > 0 else "empty",
    }