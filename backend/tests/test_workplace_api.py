"""Review API (S3): only consultants, proposal, validation, saved review."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import auth as auth_router
from backend.tests.workcycle import prepared_work

client = TestClient(app)
PREP = prepared_work()


@pytest.fixture
def store():
    data: dict = {"results/11111111-1111-4111-8111-111111111111/job.json": {"job_id": "11111111-1111-4111-8111-111111111111", "erstellt_von": "user@example.org", "status": "processing"}}
    with patch("backend.app.routers.workplace.gcs.download_bytes", return_value=b"npz"), \
         patch("backend.app.routers.workplace.load_npz", side_effect=lambda b: b), \
         patch("backend.app.routers.workplace.prepare", return_value=PREP), \
         patch("backend.app.routers.workplace.gcs.get_result", return_value={"shift_duration_min": 480}), \
         patch("backend.app.routers.workplace.gcs.get_json", side_effect=lambda p: data.get(p)), \
         patch("backend.app.routers.workplace.gcs.put_json", side_effect=lambda p, d: data.__setitem__(p, d)):
        yield data


def as_user(role):
    app.dependency_overrides[auth_router.get_current_user] = lambda: {"email": f"{role}@example.org", "role": role}


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_without_login_401(monkeypatch):
    monkeypatch.setattr(auth_router.settings, "JWT_SECRET", "test")
    assert client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/ablauf").status_code == 401
    assert client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/review", json={"segmente": []}).status_code == 401


def test_customer_role_403(store):
    as_user("user")
    r = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/ablauf")
    assert r.status_code == 403 and r.json()["detail"] == "Nur für angemeldete Berater."


def test_proposal_for_consultant(store):
    as_user("berater")
    r = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/ablauf")
    assert r.status_code == 200
    body = r.json()
    assert body["zyklen"]["erkannt"] and body["zyklen"]["median_s"] == pytest.approx(10.0, rel=0.02)
    assert body["vorschlag"][0]["start_phase"] == 0 and body["vorschlag"][-1]["ende_phase"] == 1
    assert body["typen"]["Gehen"] == "verschwendung"
    assert body["review"] is None and body["ergebnis"] is None
    assert len(body["median_zyklus"]["hand_speed"]) == 200


def test_review_saved_and_transferred(store):
    as_user("berater")
    seg = [
        {"start_phase": 0.0, "ende_phase": 0.3, "typ": "Gehen"},
        {"start_phase": 0.3, "ende_phase": 0.6, "typ": "Greifen"},
        {"start_phase": 0.6, "ende_phase": 0.9, "typ": "Fügen"},
        {"start_phase": 0.9, "ende_phase": 1.0, "typ": "Prüfen", "klasse": "verschwendung"},
    ]
    r = client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/review", json={"segmente": seg, "kommentar": "Greifweg lang"})
    assert r.status_code == 200, r.text
    body = r.json()
    saved = store["results/11111111-1111-4111-8111-111111111111/review.json"]
    assert saved["bestaetigt_von"] == "berater@example.org"
    assert saved["segmente"][1]["klasse"] == "notwendig"  # default of the type
    assert saved["segmente"][3]["klasse"] == "verschwendung"  # changed by the expert
    assert body["ergebnis"]["anteile_ablauf"]["verschwendung"] == pytest.approx(0.4)
    assert body["review"]["kommentar"] == "Greifweg lang"
    # GET returns the saved review
    again = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/ablauf").json()
    assert again["review"]["bestaetigt_von"] == "berater@example.org" and again["ergebnis"] is not None


def test_invalid_review_422(store):
    as_user("berater")
    r = client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/review", json={"segmente": [{"start_phase": 0, "ende_phase": 0.5, "typ": "Greifen"}]})
    assert r.status_code == 422 and "bei 1 enden" in r.json()["detail"]
    assert "results/11111111-1111-4111-8111-111111111111/review.json" not in store


def test_missing_pose_404():
    as_user("berater")
    with patch("backend.app.routers.workplace.gcs.download_bytes", side_effect=FileNotFoundError):
        r = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/ablauf")
    assert r.status_code == 404


def test_admin_may_review(store):
    as_user("admin")
    assert client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/ablauf").status_code == 200
