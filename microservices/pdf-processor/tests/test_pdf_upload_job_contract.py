"""
Contract tests for PDF upload validation and job status / process enqueue behavior.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import app.database.database as pdf_db
import app.routers.pdf_processor as pdf_router


@pytest.fixture(autouse=True)
def mongo_pdf():
    pdf_db.sync_client = __import__("mongomock").MongoClient()
    yield
    pdf_db.sync_client = None


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf():
    from main import app

    transport = ASGITransport(app=app, lifespan="off")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("notes.txt", b"hello", "text/plain")}
        r = await client.post(
            "/api/v1/pdf_processor/upload_new_pdf",
            params={"user_id": "user-1"},
            files=files,
        )
    assert r.status_code == 400
    assert "pdf" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_happy_path_mocks_r2():
    from main import app

    with (
        patch.object(
            pdf_router.r2_svc,
            "generate_key",
            return_value=("path/to/file.pdf", "key-1", "My Book", "pdf"),
        ),
        patch.object(
            pdf_router.r2_svc,
            "upload_processed_data",
            return_value={"key": "r2-key-1", "bucket": "test-bucket"},
        ),
    ):
        transport = ASGITransport(app=app, lifespan="off")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("chapter.pdf", b"%PDF-1.4 minimal", "application/pdf")}
            r = await client.post(
                "/api/v1/pdf_processor/upload_new_pdf",
                params={"user_id": "user-1"},
                files=files,
            )

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["r2_bucket"] == "test-bucket"
    assert "r2_key" in body


@pytest.mark.asyncio
async def test_get_job_status_response_shape():
    from main import app

    job_payload = {
        "job_id": "job_sample",
        "status": "pending",
        "progress": 0,
        "message": "queued",
        "created_at": "04-14-2026 at 10:00 AM",
        "completed_at": None,
        "result": None,
        "error": None,
    }

    with patch.object(
        pdf_router.pdf_processor,
        "get_job_by_id",
        new_callable=AsyncMock,
        return_value=job_payload,
    ):
        transport = ASGITransport(app=app, lifespan="off")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(
                "/api/v1/pdf_processor/job/job_sample",
                params={"user_id": "user-1"},
            )

    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == "job_sample"
    assert data["status"] == "pending"
    assert data["progress"] == 0


@pytest.mark.asyncio
async def test_process_pdf_returns_202():
    from main import app

    async def _noop_task(*_a, **_k):
        return None

    with (
        patch.object(pdf_router.r2_svc, "file_exists", return_value=True),
        patch.object(
            pdf_router.pdf_processor,
            "create_job",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(pdf_router.pdf_processor, "process_pdf_task", _noop_task),
    ):
        transport = ASGITransport(app=app, lifespan="off")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/pdf_processor/process_pdf",
                params={"user_id": "user-1"},
                json={
                    "r2_pdf_path": "user/x/doc.pdf",
                    "chunk_size": 1000,
                    "chunk_overlap": 100,
                    "output_format": "json",
                },
            )

    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "accepted"
    assert "job_id" in body
    assert body["r2_key"] == "user/x/doc.pdf"
