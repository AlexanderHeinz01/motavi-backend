"""S5: JSON export against the schema, 2-page PDF, expert confirmation of recommendation and type."""
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from backend.app.main import app
from backend.app.routers import auth as auth_router
from backend.app.services.workplace import export, pdf_steckbrief, scoring_config, steckbrief
from backend.tests.profiles import PROFILE, module_results
from backend.tests.workcycle import prepared_work

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "docs" / "steckbrief_schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
CFG = scoring_config.get()


def build(name, bestaetigung=None, **override):
    return steckbrief.build(CFG, "a1b2c3d4e5f6", **module_results(name, **override), bestaetigung=bestaetigung,
                            arbeitsplatz="Montage · Baugruppe A")


def errors(doc):
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in VALIDATOR.iter_errors(doc)]


def pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type /Page[^s]", pdf))


# ── export ───────────────────────────────────────────────────────────────────


def test_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("name", [*PROFILE, "ohne_zyklus", "ohne_review"])
def test_export_valid_against_schema(name):
    if name == "ohne_zyklus":
        doc = build("keep", zyklen=None)
    elif name == "ohne_review":
        doc = build("automate", schritte=None)
    else:
        doc = build(name)
    out = export.to_export(doc)
    assert errors(out) == []
    assert out["format"] == "motavi-arbeitsplatz-steckbrief" and out["beispiel"] is False
    assert out["pflichthinweis"] == "Grobe Abschätzung, ersetzt kein Angebot."


def test_export_values_and_no_person_data():
    doc = build("improve-then-automate", bestaetigung={
        "empfehlung_id": "improve-then-automate", "typ_id": "pick_and_place", "vorschlag_id": "improve-then-automate",
        "vorschlag_typ_id": "pick_and_place", "bestaetigt_von": "berater@example.org", "bestaetigt_am": "2026-10-30T12:00:00+00:00"})
    out = export.to_export(doc)
    assert out["empfehlung"] == "Erst verbessern, dann automatisieren" and out["empfehlung_status"] == "bestaetigt"
    assert out["verbesserungs_score"] == 55 and out["automatisierungs_score"] == 81
    assert out["zykluszeit_median_s"] == 38.4 and out["zyklen_pro_schicht"] == 690
    assert out["typ_vorschlag"] == "Pick and Place" and out["automatisierung"]["basis"] == "verbesserter Ablauf"
    assert out["stunden_auto_jahr_bandbreite"] == out["automatisierung"]["stunden_jahr"]
    assert sum(s["anteil"] for s in out["ablaufschritte"]) == pytest.approx(1.0)
    assert "@" not in json.dumps(out)  # no e-mail of the consultant


def test_not_reliable_is_null_with_reason():
    out = export.to_export(build("keep", zyklen=None))
    assert out["zykluszeit_median_s"] is None and out["zyklen_pro_schicht"] is None
    assert out["qualitaet"]["zykluszeit_median_s"] == {"belastbar": False, "qualitaet": 0.0, "grund": "Kein wiederkehrender Zyklus erkannt"}
    assert out["ablaufschritte"] == [] and out["anteile_ablauf"] is None


def test_schema_rejects_wrong_documents():
    out = export.to_export(build("automate"))
    assert errors({**out, "verbesserungs_score": 120})
    assert errors({**out, "hersteller": "X"})  # no extra fields, vendor-neutral
    assert errors({k: v for k, v in out.items() if k != "empfehlung_id"})


# ── PDF ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", list(PROFILE))
def test_pdf_has_two_pages(name):
    pdf = pdf_steckbrief.generate(build(name))
    assert pdf.startswith(b"%PDF") and pages(pdf) == 2


def test_pdf_two_pages_in_edge_cases():
    for doc in (build("keep", zyklen=None), build("automate", schritte=None),
                build("automate", belastung=(9.0, 0.3, 0.2, 0.2), kunde={})):
        assert pages(pdf_steckbrief.generate(doc)) == 2


# ── expert confirmation ──────────────────────────────────────────────────────


def bestaetigung(empfehlung_id, typ_id=None, vorschlag_id="automate", vorschlag_typ_id="pick_and_place"):
    return {"empfehlung_id": empfehlung_id, "typ_id": typ_id, "kommentar": "geprüft", "vorschlag_id": vorschlag_id,
            "vorschlag_typ_id": vorschlag_typ_id, "bestaetigt_von": "b@example.org", "bestaetigt_am": "2026-10-30T12:00:00+00:00"}


def test_proposal_until_confirmed():
    e = build("automate")["empfehlung"]
    assert e["status"] == "vorschlag" and e["id"] == e["vorschlag_id"] == "automate" and not e["geaendert"]
    assert e["erklaerung"] == CFG.empfehlung.erklaerung["automate"]
    assert len(e["gruende"]) == 3


def test_confirmed_unchanged():
    doc = build("automate", bestaetigung("automate", "pick_and_place"))
    assert doc["empfehlung"]["status"] == "bestaetigt" and not doc["empfehlung"]["geaendert"]
    assert doc["automatisierungstyp"]["name"] == "Pick and Place" and not doc["automatisierungstyp"]["geaendert"]
    assert not any("seit der Bestätigung" in h for h in doc["hinweise"])


def test_expert_changes_recommendation_and_type():
    doc = build("automate", bestaetigung("improve-then-automate", "maschinenbeladung"))
    e, t = doc["empfehlung"], doc["automatisierungstyp"]
    assert e["id"] == "improve-then-automate" and e["vorschlag_id"] == "automate" and e["geaendert"]
    assert t["id"] == "maschinenbeladung" and t["vorschlag_id"] == "pick_and_place" and t["geaendert"]
    # economics follow the expert: improved process, the chosen type's ranges
    a = doc["wirtschaftlichkeit"]["automatisieren"]
    assert a["basis"] == "verbesserter Ablauf" and a["typ"] == "Maschinenbeladung"


def test_expert_without_automation_drops_type_and_automation_economics():
    doc = build("automate", bestaetigung("keep"))
    assert doc["automatisierungstyp"]["id"] is None and not doc["empfehlung"]["mit_automatisierung"]
    assert not doc["wirtschaftlichkeit"]["automatisieren"]["berechnet"]


def test_type_left_open():
    doc = build("automate", bestaetigung("automate", None))
    assert doc["automatisierungstyp"]["text"] == "Typ vom Experten offen gelassen."
    assert doc["wirtschaftlichkeit"]["automatisieren"]["grund"] == "Kein Automatisierungstyp festgelegt."


def test_stale_confirmation_is_pointed_out():
    doc = build("automate", bestaetigung("automate", "pick_and_place", vorschlag_id="improve"))
    assert any("seit der Bestätigung geändert" in h for h in doc["hinweise"])


# ── API ──────────────────────────────────────────────────────────────────────

client = TestClient(app)
PREP = prepared_work()
RESULT = {"shift_duration_min": 480, "reba_score": 6.2, "critical_frames": [{"reba": 8.9}], "department": "Montage",
          "task_description": "Baugruppe A", "movements": {"bending": {"pct": 10.0}, "overhead": {"pct": 2.0}}}


@pytest.fixture
def store():
    data: dict = {"results/11111111-1111-4111-8111-111111111111/job.json": {"job_id": "11111111-1111-4111-8111-111111111111", "erstellt_von": "user@example.org", "status": "processing"}}
    with patch("backend.app.routers.workplace.gcs.download_bytes", return_value=b"npz"), \
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


def test_api_without_login_401(monkeypatch):
    monkeypatch.setattr(auth_router.settings, "JWT_SECRET", "test")
    for path in ("/api/v1/workplace/11111111-1111-4111-8111-111111111111/pdf", "/api/v1/workplace/11111111-1111-4111-8111-111111111111/export"):
        assert client.get(path).status_code == 401
    assert client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/empfehlung", json={"empfehlung_id": "keep"}).status_code == 401


def test_api_confirmation_only_for_consultants(store):
    as_user("user")
    r = client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/empfehlung", json={"empfehlung_id": "keep"})
    assert r.status_code == 403 and list(store) == ["results/11111111-1111-4111-8111-111111111111/job.json"]


@pytest.mark.parametrize("body", [
    {"empfehlung_id": "keep", "typ_id": "pick_and_place"},
    {"empfehlung_id": "automate", "typ_id": "roboterhersteller_x"},
    {"empfehlung_id": "sofort"},
])
def test_api_confirmation_invalid_422(store, body):
    as_user("berater")
    assert client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/empfehlung", json=body).status_code == 422
    assert "results/11111111-1111-4111-8111-111111111111/empfehlung.json" not in store


def test_api_confirmation_saved(store):
    as_user("berater")
    r = client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/empfehlung", json={"empfehlung_id": "automate", "typ_id": "pick_and_place", "kommentar": "passt"})
    assert r.status_code == 200, r.text
    saved = store["results/11111111-1111-4111-8111-111111111111/empfehlung.json"]
    assert saved["bestaetigt_von"] == "berater@example.org" and saved["typ_id"] == "pick_and_place"
    assert saved["vorschlag_id"] == r.json()["empfehlung"]["vorschlag_id"]
    as_user("user")
    doc = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111").json()
    assert doc["empfehlung"]["status"] == "bestaetigt" and doc["empfehlung"]["kommentar"] == "passt"
    assert doc["arbeitsplatz"] == "Montage · Baugruppe A"


def test_confirmed_steckbrief_frozen(store):
    """E.2.14: after the confirmation it is served from steckbrief.json, also
    when pose.npz has been deleted, and reading it writes nothing."""
    as_user("berater")
    doc = client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/empfehlung", json={"empfehlung_id": "keep"}).json()
    assert store["results/11111111-1111-4111-8111-111111111111/steckbrief.json"] == doc
    vorher = dict(store)
    with patch("backend.app.routers.workplace.gcs.download_bytes", side_effect=FileNotFoundError):
        r = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111")
        assert r.status_code == 200 and r.json() == doc
        assert client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/pdf").status_code == 200
    assert store == vorher


def test_change_after_confirmation_freezes_again(store):
    as_user("berater")
    client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/empfehlung", json={"empfehlung_id": "keep"})
    doc = client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/inputs", json={"anzahl_varianten": 3}).json()
    assert store["results/11111111-1111-4111-8111-111111111111/steckbrief.json"] == doc
    assert doc["kundenangaben"]["anzahl_varianten"] == 3


def test_foreign_user_sees_no_job(store):
    app.dependency_overrides[auth_router.get_current_user] = lambda: {"email": "andere@example.org", "role": "user"}
    for path in ("", "/pdf", "/export"):
        assert client.get(f"/api/v1/workplace/11111111-1111-4111-8111-111111111111{path}").status_code == 404
    assert client.put("/api/v1/workplace/11111111-1111-4111-8111-111111111111/inputs", json={}).status_code == 404


def test_api_pdf_and_export(store):
    as_user("user")
    r = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert 'filename="motavi-steckbrief-11111111.pdf"' in r.headers["content-disposition"] and pages(r.content) == 2
    r = client.get("/api/v1/workplace/11111111-1111-4111-8111-111111111111/export")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert errors(r.json()) == []
