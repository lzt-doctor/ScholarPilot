from io import BytesIO

import fitz
from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Document, User
from app.routers import documents as documents_router
from app.utils.dependencies import get_current_user
from tests.fakes import DeterministicFakeEmbedding


def _pdf_bytes(text: str = "ScholarPilot retrieval test document") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_upload_reindex_and_delete_document(db_session, tmp_path, monkeypatch) -> None:
    user = User(username="api-user", email="api@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    fake_embedding = DeterministicFakeEmbedding()
    monkeypatch.setattr(documents_router, "get_embedding_service", lambda: fake_embedding)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents/upload",
                files={"file": ("paper.pdf", BytesIO(_pdf_bytes()), "application/pdf")},
                data={"category": "test"},
            )
            assert response.status_code == 201, response.text
            document_id = response.json()["id"]
            assert response.json()["indexing_status"] == "ready"

            reindexed = client.post(f"/documents/{document_id}/reindex")
            assert reindexed.status_code == 200, reindexed.text
            assert reindexed.json()["embedding_model"] == fake_embedding.model_name

            deleted = client.delete(f"/documents/{document_id}")
            assert deleted.status_code == 204
            assert db_session.get(Document, document_id) is None
    finally:
        app.dependency_overrides.clear()


def test_invalid_pdf_returns_safe_error(db_session, tmp_path, monkeypatch) -> None:
    user = User(username="safe-user", email="safe@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents/upload",
                files={"file": ("bad.pdf", BytesIO(b"not a pdf"), "application/pdf")},
            )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_pdf_content"
        assert "traceback" not in response.text.lower()
    finally:
        app.dependency_overrides.clear()
