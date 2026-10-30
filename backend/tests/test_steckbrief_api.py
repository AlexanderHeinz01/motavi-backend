"""Steckbrief API (S4): GET /workplace/{job_id}, PUT /workplace/{job_id}/inputs."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import auth as auth_router
from backend.tests.workcycle import prepared_work

client = TestClient(app)
PREP = prepared_work()
RESULT = {
    "shift_duration_min": 480, "reba_score": 6.2, "critical_frames": [{"reba": 8.9}],
    "movements": {"bending": {"pct": 10.0}, "overhead": {"pct": 2.0}, "neutral": {"pct": 88.0}},
}
REVIEW = [
    {"start_phase": 0.0, "ende_phase": 0.15, "typ": "Gehen"},
    {"start_phase": 0.15, "ende_phase": 0.3, "typ": "Warten"},
    {"start_phase": 0.3, "ende_phase": 0.45, "typ": "Greifen"},
    {"start_phase": 0.45, "ende_phase": 0.6, "typ": "Bringen"},
    {"start_phase": 0.6, "ende_phase": 0.85, "typ": "Fügen"},
    {"start_phase": 0.85, "ende_phase": 1.0, "typ": "Gehen"},
]


@pytest.fixture
def store():
    data: dict = {}

    def download(path):
        if "missing" in path:
            raise FileNotFoundError(path)
        return b"npz"

    with patch("backend.app.routers.workplace.gcs.download_bytes", side_effect=download), \
         patch("backend.app.routers.workplace.load_npz", side_effect=lambda b: b), \
         patch("backend.app.routers.workplace.prepare", return_value=PREP), \
         patch("backend.app.routers.workplace.gcs.get_result", return_value=RESULT), \
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
    assert client.get("/api/v1/workplace/job").status_code == 401
    assert client.put("/api/v1/workplace/job/inputs", json={}).status_code == 401


def test_steckbrief_for_signed_in_user(store):
    as_user("user")
    r = client.get("/api/v1/workplace/job")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["zyklen"]["erkannt"] and doc["zyklen"]["zykluszeit_median_s"]["wert"] == pytest.approx(10.0, rel=0.02)
    assert doc["belastung"]["reba_mittel"]["wert"] == 6.2 and doc["belastung"]["reba_max"]["wert"] == 8.9
    assert doc["ablauf"]["bestaetigt"] is False
    assert doc["empfehlung"]["vorlaeufig"] and doc["empfehlung"]["status"] == "vorschlag"
    assert doc["wirtschaftlichkeit"]["hinweis"] == "Grobe Abschätzung, ersetzt kein Angebot."
    assert store["results/job/workplace.json"] == doc


def test_missing_pose_404_and_nothing_saved(store):
    as_user("user")
    assert client.get("/api/v1/workplace/missing").status_code == 404
    r = client.put("/api/v1/workplace/missing/inputs", json={"anzahl_varianten": 2})
    assert r.status_code == 404 and store == {}


@pytest.mark.parametrize("body", [
    {"besetzung_schwierigkeit": 6},
    {"schichten_pro_tag": 0},
    {"investition_euro": [90000, 50000]},
    {"unbekannt": 1},
])
def test_invalid_inputs_422(store, body):
    as_user("user")
    assert client.put("/api/v1/workplace/job/inputs", json=body).status_code == 422


def test_inputs_saved_and_used(store):
    as_user("user")
    before = client.get("/api/v1/workplace/job").json()["zyklen"]["zyklen_pro_schicht"]["wert"]
    kunde = {"anzahl_varianten": 2, "teilegewicht_kg": 1.5, "abmessungen_cm": {"laenge": 25}, "stueck_pro_schicht": 1000,
             "schichten_pro_tag": 2, "schichtdauer_min": 240, "arbeitstage_pro_jahr": 220,
             "vollkosten_euro_pro_stunde": 50, "besetzung_schwierigkeit": 3}
    r = client.put("/api/v1/workplace/job/inputs", json=kunde)
    assert r.status_code == 200, r.text
    assert store["results/job/inputs.json"] == {**kunde, "abmessungen_cm": {"laenge": 25}}
    doc = r.json()
    # the customer's shift of 240 minutes halves the cycles per shift
    assert doc["zyklen"]["zyklen_pro_schicht"]["wert"] == pytest.approx(before / 2, rel=0.01)
    # measured about 1,440 cycles per 240 min shift -> no hint; customer inputs are in the Steckbrief
    assert doc["kundenangaben"]["anzahl_varianten"] == 2
    assert client.get("/api/v1/workplace/job").json()["kundenangaben"] == store["results/job/inputs.json"]


def test_after_review_complete_steckbrief(store):
    as_user("berater")
    assert client.put("/api/v1/workplace/job/review", json={"segmente": REVIEW}).status_code == 200
    kunde = {"anzahl_varianten": 1, "teilegewicht_kg": 2, "abmessungen_cm": {"laenge": 20}, "schichten_pro_tag": 2,
             "arbeitstage_pro_jahr": 220, "vollkosten_euro_pro_stunde": 50, "besetzung_schwierigkeit": 4}
    doc = client.put("/api/v1/workplace/job/inputs", json=kunde).json()
    assert doc["ablauf"]["bestaetigt"] and doc["ablauf"]["bestaetigt_von"] == "berater@example.org"
    assert doc["ablauf"]["anteile_ablauf"]["verschwendung"] == pytest.approx(0.45)
    assert doc["verbesserungs_score"]["vollstaendig"]
    v = doc["wirtschaftlichkeit"]["verbessern"]
    # walking 30 % * 0.5 + waiting 15 % * 0.5 avoidable
    assert v["vermeidbar_anteil_zyklus"] == pytest.approx(0.225)
    assert v["euro_jahr"] is not None
    assert doc["empfehlung"]["id"] in ("improve-then-automate", "improve", "automate", "keep")
