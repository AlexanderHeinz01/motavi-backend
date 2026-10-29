"""Upload endpoint tests (GCS is mocked)."""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


@patch("backend.app.routers.upload.gcs.upload_video", return_value="uploads/test/video.mp4")
@patch("backend.app.routers.upload.analyzer.run_pipeline", new_callable=MagicMock)
def test_upload_mp4_returns_202(mock_pipeline, mock_gcs_upload):
    data = b"\x00\x01" * 100  # fake binary payload
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.mp4", io.BytesIO(data), "video/mp4")},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert "job_id" in body
    mock_gcs_upload.assert_called_once()


def test_upload_empty_file_returns_422():
    response = client.post(
        "/api/v1/upload",
        files={"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")},
    )
    assert response.status_code == 422


def test_upload_unsupported_type_returns_422():
    response = client.post(
        "/api/v1/upload",
        files={"file": ("doc.pdf", io.BytesIO(b"dummy"), "application/pdf")},
    )
    assert response.status_code == 422


@patch("backend.app.routers.analysis.gcs.blob_exists", return_value=False)
def test_analysis_unknown_job_returns_404(mock_exists):
    response = client.get("/api/v1/analysis/nonexistent-job-id")
    assert response.status_code == 404


@patch("backend.app.routers.analysis.gcs.blob_exists", return_value=True)
@patch("backend.app.routers.analysis.gcs.get_result",  return_value=None)
def test_analysis_pending_returns_processing(mock_result, mock_exists):
    response = client.get("/api/v1/analysis/some-job-id")
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
