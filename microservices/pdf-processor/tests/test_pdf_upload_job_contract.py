"""
Contract tests for PDF upload validation and job status / process enqueue behavior.
"""
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

PDF_API = "/api/v1/pdf/pdf_processor"


def test_upload_rejects_non_pdf():
    from main import app

    with TestClient(app) as client:
        files = {"file": ("notes.txt", b"hello", "text/plain")}
        r = client.post(
            f"{PDF_API}/upload_new_pdf",
            params={"user_id": "user-1"},
            files=files,
        )
    assert r.status_code == 400
    assert "pdf" in r.json()["detail"].lower()


def test_upload_happy_path_mocks_r2():
    from main import app

    with (
        patch(
            "app.routers.pdf_processor.r2_svc.generate_key",
            return_value=("path/to/file.pdf", "key-1", "My Book", "pdf"),
        ),
        patch(
            "app.routers.pdf_processor.r2_svc.upload_processed_data",
            return_value={"key": "r2-key-1", "bucket": "test-bucket"},
        ),
    ):
        with TestClient(app) as client:
            files = {"file": ("chapter.pdf", b"%PDF-1.4 minimal", "application/pdf")}
            r = client.post(
                f"{PDF_API}/upload_new_pdf",
                params={"user_id": "user-1"},
                files=files,
            )

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["r2_bucket"] == "test-bucket"
    assert "r2_key" in body


def test_get_job_status_response_shape():
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

    with patch(
        "app.routers.pdf_processor.pdf_processor.get_job_by_id",
        new_callable=AsyncMock,
        return_value=job_payload,
    ):
        with TestClient(app) as client:
            r = client.get(
                f"{PDF_API}/job/job_sample",
                params={"user_id": "user-1"},
            )

    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == "job_sample"
    assert data["status"] == "pending"
    assert data["progress"] == 0


def test_process_pdf_returns_202():
    from main import app

    async def _noop_task(*_a, **_k):
        return None

    with (
        patch("app.routers.pdf_processor.r2_svc.file_exists", return_value=True),
        patch(
            "app.routers.pdf_processor.pdf_processor.create_job",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.routers.pdf_processor.pdf_processor.process_pdf_task",
            _noop_task,
        ),
    ):
        with TestClient(app) as client:
                r = client.post(
                    f"{PDF_API}/process_pdf",
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
