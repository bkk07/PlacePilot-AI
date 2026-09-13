# Tests for the admin knowledge-corpus upload API.
# Requires Postgres (for auth) + Weaviate (for indexing); skips otherwise.

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_token
from app.db.db import get_session_factory
from app.db.models import User
from app.main import app


def _db_up() -> bool:
    try:
        from sqlalchemy import text

        from app.db.db import get_engine

        with get_engine().connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception:
        return False


def _weaviate_up() -> bool:
    try:
        from app.ai.weaviate_client import get_client

        client = get_client()
        client.close()
        return True
    except Exception:
        return False


def _embedder_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not (_db_up() and _weaviate_up() and _embedder_available()),
    reason="Postgres, Weaviate, and/or sentence-transformers not available",
)

client = TestClient(app)


def _admin_token() -> str:
    session = get_session_factory()()
    try:
        user = session.query(User).filter(User.role == "admin").first()
        return create_token(str(user.id), "admin")
    finally:
        session.close()


def _student_token() -> str:
    session = get_session_factory()()
    try:
        user = session.query(User).filter(User.role == "student").first()
        return create_token(str(user.id), "student")
    finally:
        session.close()


def test_upload_requires_admin():
    r = client.post(
        "/knowledge/documents",
        headers={"Authorization": f"Bearer {_student_token()}"},
        files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"document_type": "general"},
    )
    assert r.status_code == 403


def test_upload_rejects_bad_type():
    r = client.post(
        "/knowledge/documents",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        data={"document_type": "general"},
    )
    assert r.status_code == 400


def test_upload_rejects_bad_document_type():
    r = client.post(
        "/knowledge/documents",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
        data={"document_type": "nonsense"},
    )
    assert r.status_code == 400


def test_upload_and_delete_roundtrip():
    name = f"test_upload_{uuid.uuid4().hex[:6]}.txt"
    content = f"Test policy upload {name}: interns get a stipend of 42000 rupees per month at TestCorp."
    r = client.post(
        "/knowledge/documents",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        files={"file": (name, io.BytesIO(content.encode()), "text/plain")},
        data={"document_type": "placement_policy", "company": "TestCorp"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ingested"] is True
    assert body["chunks"] >= 1
    document_id = body["document_id"]

    # The chunk must be retrievable through the RAG tool path.
    from app.ai.retriever import retrieve

    hits = retrieve("stipend TestCorp", top_k=5, filters={"document_type": "placement_policy"})
    assert any(name in (h.source or "") for h in hits)

    # Admin can list the manifest and see it.
    listing = client.get("/knowledge/documents", headers={"Authorization": f"Bearer {_admin_token()}"})
    assert listing.status_code == 200
    assert any(d.get("document_id") == document_id for d in listing.json()["documents"])

    # Delete by document_id, and confirm the chunks are gone.
    dele = client.delete(
        f"/knowledge/documents/{document_id}",
        headers={"Authorization": f"Bearer {_admin_token()}"},
    )
    assert dele.status_code == 200
    assert dele.json()["deleted"] >= 1

    hits2 = retrieve("stipend TestCorp", top_k=5, filters={"company": "TestCorp"})
    assert not any(name in (h.source or "") for h in hits2)
