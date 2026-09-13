# Knowledge-corpus admin API: upload / list / delete RAG documents.
# Admin-only (JWT role check); files are validated (type + size) and pushed
# through the same incremental ingestion pipeline as the seed corpus.

import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.companies import normalize_company
from app.ai.document_loader import load_document
from app.ai.ingest import (
    _content_hash,
    _infer_metadata,
    delete_document_chunks_by_source,
)
from app.ai.weaviate_client import (
    delete_document_chunks,
    get_client,
    get_collection,
)
from app.api.deps import require_role
from app.core.config import settings
from app.core.observability import metrics
from app.db.db import get_db
from app.db.models import User

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# document_type values the corpus is indexed with (kept in sync with ingest heuristics).
DOCUMENT_TYPES = (
    "placement_policy",
    "eligibility_matrix",
    "offer_process",
    "document_requirement",
    "schedule",
    "announcement",
    "placement_statistics",
    "job_description",
    "interview_experience",
    "general",
)


@router.post("/documents", status_code=201)
def upload_document(
    file: UploadFile,
    document_type: str = Form(default="general"),
    company: str = Form(default=""),
    role: str = Form(default=""),
    year: int | None = Form(default=None),
    source_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Ingest one document into the RAG corpus (admin only)."""
    _validate_upload(file)
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="uploaded file is empty")
    digest = _content_hash(data)

    # Write to a temp file so the standard loader (PDF/TXT extraction) applies.
    import tempfile
    from pathlib import Path

    name = source_name or file.filename or "uploaded.pdf"
    if not any(name.lower().endswith(ext) for ext in settings.ALLOWED_DOC_TYPES):
        raise HTTPException(status_code=400, detail=f"unsupported file type: {name}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / f"upload{Path(name).suffix.lower()}"
        tmp_path.write_bytes(data)
        try:
            pages = load_document(tmp_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"could not extract text: {exc}") from exc

    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"document_type must be one of {sorted(DOCUMENT_TYPES)}")
    company_canonical = normalize_company(company) if company else ""
    if company and not company_canonical:
        # Allow arbitrary companies for uploads, but index a clean value.
        company_canonical = company.strip()

    from app.ai.chunker import chunk_text
    from app.ai.embeddings import embed_texts

    document_id = str(uuid.uuid4())
    metadata = {
        "company": company_canonical,
        "year": year if year is not None else _infer_year_default(),
        "document_type": document_type,
        "role": role.strip(),
        "source": name,
        "content_hash": digest,
        "embedding_model": settings.EMBEDDING_MODEL,
    }
    chunks = chunk_text(
        pages,
        document_id=document_id,
        metadata=metadata,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="no extractable text found in the document")

    client = get_client()
    try:
        collection = get_collection(client)
        # Replace any previous version of the same source file.
        delete_document_chunks_by_source(client, name)
        vectors = embed_texts([c.text for c in chunks])
        with collection.batch.dynamic() as batch:
            for chunk, vector in zip(chunks, vectors):
                batch.add_object(
                    properties={"text": chunk.text, **chunk.metadata},
                    vector=vector,
                )
    finally:
        client.close()

    metrics.inc("knowledge_uploads")
    return {
        "ingested": True,
        "document_id": document_id,
        "source": name,
        "chunks": len(chunks),
        "content_hash": digest,
    }


@router.get("/documents")
def list_documents(
    user: User = Depends(require_role("admin")),
) -> dict:
    """List the indexed corpus manifest (source -> hash / model / doc id)."""
    client = get_client()
    try:
        collection = get_collection(client)
        manifest: dict[str, dict] = {}
        for obj in collection.iterator():
            props = obj.properties
            src = props.get("source")
            if not src:
                continue
            manifest.setdefault(
                src,
                {
                    "document_id": props.get("document_id"),
                    "content_hash": props.get("content_hash"),
                    "embedding_model": props.get("embedding_model"),
                    "company": props.get("company"),
                    "document_type": props.get("document_type"),
                    "chunk_count": 0,
                },
            )
            manifest[src]["chunk_count"] += 1
        return {"documents": sorted(manifest.values(), key=lambda d: d.get("document_id") or "")}
    finally:
        client.close()


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
) -> dict:
    """Remove one document's chunks from the RAG corpus (admin only)."""
    client = get_client()
    try:
        deleted = delete_document_chunks(client, str(document_id))
    finally:
        client.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="no chunks found for that document_id")
    return {"deleted": deleted, "document_id": str(document_id)}


def _validate_upload(file: UploadFile) -> None:
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="missing file")
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"file type '{ext}' not allowed; permitted: {', '.join(settings.ALLOWED_DOC_TYPES)}",
        )
    if file.size is not None and file.size > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file too large")


def _infer_year_default() -> int:
    import datetime

    return datetime.date.today().year
