"""Upload straight into Cloud Storage, upload links for customers, access to
results (E.3.1 and E.3.3 of the review on 31.10.2026). GCS is mocked."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import auth as auth_router
from backend.app.services import auth as auth_svc

client = TestClient(app)
JOB = "33333333-3333-4333-8333-333333333333"
DATEI = {"dateiname": "platz.mp4", "groesse_bytes": 50_000_000, "content_type": "video/mp4"}


@pytest.fixture
def store(monkeypatch):
    """Fake bucket: JSON documents and existing blobs."""
    monkeypatch.setattr(auth_svc.settings, "JWT_SECRET", "x" * 32)
    data: dict = {}
    blobs: set = set()
    with patch("backend.app.services.gcs.get_json", side_effect=lambda p: data.get(p)), \
         patch("backend.app.services.gcs.put_json", side_effect=lambda p, d: data.__setitem__(p, d)), \
         patch("backend.app.services.gcs.blob_exists", side_effect=lambda p: p in blobs), \
         patch("backend.app.services.gcs.create_upload_session", return_value="https://storage.example/session") as session, \
         patch("backend.app.routers.upload.analyzer.run_pipeline", new_callable=MagicMock) as pipeline:
        yield {"data": data, "blobs": blobs, "session": session, "pipeline": pipeline}


def as_user(role, email=None):
    app.dependency_overrides[auth_router.get_current_user] = lambda: {"email": email or f"{role}@example.org", "role": role}


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def job_json(store, job_id=JOB, von="user@example.org", status="processing", **extra):
    store["data"][f"results/{job_id}/job.json"] = {"job_id": job_id, "erstellt_von": von, "status": status, "meta": {"schichtdauer_min": 450}, **extra}


# ── upload in two steps ──────────────────────────────────────────────────────

def test_upload_needs_sign_in(store):
    assert client.post("/api/v1/upload/session", json={**DATEI}).status_code == 401
    assert client.post(f"/api/v1/upload/{JOB}/start").status_code == 401


def test_session_creates_job_and_resumable_upload(store):
    as_user("berater")
    r = client.post("/api/v1/upload/session", json={**DATEI, "department": "Montage"}, headers={"Origin": "https://app.example.de"})
    assert r.status_code == 201, r.text
    body = r.json()
    job = store["data"][f"results/{body['job_id']}/job.json"]
    assert job["erstellt_von"] == "berater@example.org" and job["quelle"] == "intern" and job["status"] == "wartet_auf_upload"
    assert job["meta"]["schichtdauer_min"] == 450  # net working time, default (P9)
    store["session"].assert_called_once_with(f"raw/{body['job_id']}/video.mp4", "video/mp4", 50_000_000, "https://app.example.de")
    assert body["upload_url"] == "https://storage.example/session"


@pytest.mark.parametrize("aenderung", [
    {"content_type": "application/pdf"},
    {"groesse_bytes": 2 * 1024 ** 3},
    {"schichtdauer_min": 30},
    {"schichtdauer_min": 800},
    {"worker_height_cm": 180},
])
def test_session_rejects(store, aenderung):
    as_user("berater")
    assert client.post("/api/v1/upload/session", json={**DATEI, **aenderung}).status_code == 422
    assert store["data"] == {}


def test_start_only_after_upload_and_only_once(store):
    as_user("user")
    job_json(store, status="wartet_auf_upload")
    assert client.post(f"/api/v1/upload/{JOB}/start").status_code == 409  # video not there yet
    store["blobs"].add(f"raw/{JOB}/video.mp4")
    r = client.post(f"/api/v1/upload/{JOB}/start")
    assert r.status_code == 202 and r.json()["status"] == "processing"
    store["pipeline"].assert_called_once()
    assert store["pipeline"].call_args.args[1]["shift_duration_min"] == 450
    assert store["data"][f"results/{JOB}/job.json"]["status"] == "processing"
    assert client.post(f"/api/v1/upload/{JOB}/start").status_code == 409


def test_start_of_foreign_job_404(store):
    as_user("user", "andere@example.org")
    job_json(store, status="wartet_auf_upload")
    assert client.post(f"/api/v1/upload/{JOB}/start").status_code == 404


# ── results only with access to the job ──────────────────────────────────────

def test_results_need_sign_in(store):
    for path in (f"/api/v1/analysis/{JOB}", f"/api/v1/report/{JOB}/pdf"):
        assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", [f"/api/v1/analysis/{JOB}", f"/api/v1/report/{JOB}/pdf", "/api/v1/analysis/not-a-uuid"])
def test_foreign_or_invalid_job_404(store, path):
    as_user("user", "andere@example.org")
    job_json(store)
    assert client.get(path).status_code == 404


def test_team_sees_every_job_also_without_job_json(store):
    as_user("berater")
    with patch("backend.app.routers.analysis.gcs.get_result", return_value=None):
        store["blobs"].add(f"raw/{JOB}/video.mp4")
        r = client.get(f"/api/v1/analysis/{JOB}")
    assert r.status_code == 200 and r.json()["status"] == "processing"


def test_analysis_unknown_job_returns_404(store):
    as_user("berater")
    with patch("backend.app.routers.analysis.gcs.get_result", return_value=None):
        assert client.get(f"/api/v1/analysis/{JOB}").status_code == 404


def test_analysis_finds_error_result_after_raw_video_was_deleted(store):
    as_user("user")
    job_json(store)
    with patch("backend.app.routers.analysis.gcs.get_result", return_value={"error": "Im Video wurde keine Person erkannt."}):
        r = client.get(f"/api/v1/analysis/{JOB}")
    assert r.status_code == 200 and r.json() == {"status": "error", "result": None, "error": "Im Video wurde keine Person erkannt."}


# ── critical frames through short-lived links ────────────────────────────────

def test_frame_needs_valid_short_lived_token(store):
    token = auth_svc.create_token("bild", 15, job=JOB, datei="critical_1.jpg")
    with patch("backend.app.routers.analysis.gcs.download_bytes", return_value=b"jpg"):
        assert client.get(f"/api/v1/frames/{JOB}/critical_1.jpg?t={token}").status_code == 200
        assert client.get(f"/api/v1/frames/{JOB}/critical_2.jpg?t={token}").status_code == 403
        assert client.get(f"/api/v1/frames/{JOB}/critical_1.jpg").status_code == 422
        alt = jwt.encode({"typ": "bild", "job": JOB, "datei": "critical_1.jpg", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, "x" * 32, algorithm="HS256")
        assert client.get(f"/api/v1/frames/{JOB}/critical_1.jpg?t={alt}").status_code == 403
        sign_in = auth_svc.create_access_token("berater@example.org")
        assert client.get(f"/api/v1/frames/{JOB}/critical_1.jpg?t={sign_in}").status_code == 403


def test_frame_token_is_no_sign_in(store):
    token = auth_svc.create_token("bild", 15, job=JOB, datei="critical_1.jpg")
    with pytest.raises(jwt.PyJWTError):
        auth_svc.decode_access_token(token)


# ── upload links for customers (G2) ──────────────────────────────────────────

def test_only_team_creates_links(store):
    as_user("user")
    assert client.post("/api/v1/upload-links", json={}).status_code == 403


def link(store, **body):
    as_user("berater")
    r = client.post("/api/v1/upload-links", json={"department": "Montage", "task_description": "Baugruppe A", **body})
    assert r.status_code == 201, r.text
    app.dependency_overrides.clear()  # the customer is not signed in
    return r.json()


def test_link_flow_without_sign_in(store):
    res = link(store, schichtdauer_min=420)
    token = res["url"].rsplit("/", 1)[-1]
    assert res["url"].startswith("/hochladen/")
    info = client.get(f"/api/v1/upload-links/{token}").json()
    assert info["arbeitsplatz"] == "Montage · Baugruppe A" and info["schichtdauer_min"] == 420
    r = client.post(f"/api/v1/upload-links/{token}/session", json=DATEI)
    assert r.status_code == 200 and r.json()["upload_url"] == "https://storage.example/session"
    store["blobs"].add(f"raw/{res['job_id']}/video.mp4")
    r = client.post(f"/api/v1/upload-links/{token}/start")
    assert r.status_code == 202 and r.json()["job_id"] == ""
    # used: the link no longer works
    assert client.get(f"/api/v1/upload-links/{token}").status_code == 410
    assert client.post(f"/api/v1/upload-links/{token}/session", json=DATEI).status_code == 410


def test_expired_or_forged_link(store):
    alt = jwt.encode({"typ": "upload", "job": JOB, "exp": datetime.now(timezone.utc) - timedelta(days=1)}, "x" * 32, algorithm="HS256")
    assert client.get(f"/api/v1/upload-links/{alt}").status_code == 410
    falsch = jwt.encode({"typ": "upload", "job": JOB, "exp": datetime.now(timezone.utc) + timedelta(days=1)}, "y" * 32, algorithm="HS256")
    assert client.get(f"/api/v1/upload-links/{falsch}").status_code == 404
    # an internal job cannot be reached through a link token
    job_json(store, status="wartet_auf_upload", quelle="intern")
    token = auth_svc.create_token("upload", 60, job=JOB)
    assert client.get(f"/api/v1/upload-links/{token}").status_code == 404


def test_link_token_is_no_sign_in(store):
    token = link(store)["url"].rsplit("/", 1)[-1]
    assert client.get(f"/api/v1/analysis/{JOB}", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_production_refuses_to_start_without_secrets():
    from types import SimpleNamespace

    from backend.app.main import pruefe_produktion
    ok = dict(APP_ENV="production", JWT_SECRET="s" * 32, PUBLIC_APP_URL="https://app.example.de", CORS_ORIGINS="https://www.example.de")
    pruefe_produktion(SimpleNamespace(**ok))
    pruefe_produktion(SimpleNamespace(**{**ok, "APP_ENV": "dev", "JWT_SECRET": ""}))
    for fehler in ({"JWT_SECRET": "kurz"}, {"PUBLIC_APP_URL": ""}, {"CORS_ORIGINS": ""}):
        with pytest.raises(RuntimeError):
            pruefe_produktion(SimpleNamespace(**{**ok, **fehler}))
