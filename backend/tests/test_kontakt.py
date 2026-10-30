"""POST /api/v1/contact (WEBSITE_PLAN Phase 6): validation, honeypot, rate limit, storage, e-mail."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.services import kontakt

client = TestClient(app)

HERSTELLER = {
    "zielgruppe": "hersteller", "name": "Erika Muster", "unternehmen": "Beispiel GmbH", "funktion": "Werkleitung",
    "email": "Erika.Muster@example.org", "telefon": "+49 30 1234567", "anzahl_arbeitsplaetze": 12,
    "interesse": ["kapazitaet", "gesundheit"], "nachricht": "Wir möchten drei Montageplätze ansehen.", "website": "",
}
ANBIETER = {"zielgruppe": "anbieter", "name": "Max Beispiel", "unternehmen": "Integrator AG", "email": "max@example.org"}


@pytest.fixture
def store():
    gespeichert: list = []
    kontakt.rate_limiter.reset()
    with patch("backend.app.routers.kontakt.kontakt.speichern", side_effect=lambda d: gespeichert.append(d) or f"id{len(gespeichert)}"):
        yield gespeichert
    kontakt.rate_limiter.reset()


def test_both_target_groups_arrive(store):
    for body in (HERSTELLER, ANBIETER):
        r = client.post("/api/v1/contact", json=body)
        assert r.status_code == 202, r.text
        assert r.json() == {"status": "eingegangen"}
    assert [d["zielgruppe"] for d in store] == ["hersteller", "anbieter"]
    assert store[0]["email"] == "erika.muster@example.org"  # normalised
    assert "website" not in store[0]
    assert store[1]["interesse"] == [] and store[1]["telefon"] is None


def test_honeypot_answers_like_success_but_stores_nothing(store):
    r = client.post("/api/v1/contact", json={**ANBIETER, "website": "http://spam.example"})
    assert r.status_code == 202 and r.json() == {"status": "eingegangen"} and store == []


@pytest.mark.parametrize("aenderung", [
    {"email": "keine-adresse"},
    {"name": "A"},
    {"unternehmen": ""},
    {"zielgruppe": "presse"},
    {"interesse": ["preise"]},
    {"anzahl_arbeitsplaetze": 0},
    {"telefon": "bitte anrufen"},
    {"nachricht": "x" * 4001},
    {"unbekannt": 1},
])
def test_invalid_requests_rejected(store, aenderung):
    assert client.post("/api/v1/contact", json={**HERSTELLER, **aenderung}).status_code == 422
    assert store == []


def test_rate_limit_per_client(store, monkeypatch):
    monkeypatch.setattr(settings, "CONTACT_RATE_LIMIT", 3)
    for _ in range(3):
        assert client.post("/api/v1/contact", json=ANBIETER, headers={"X-Forwarded-For": "203.0.113.5"}).status_code == 202
    r = client.post("/api/v1/contact", json=ANBIETER, headers={"X-Forwarded-For": "203.0.113.5"})
    assert r.status_code == 429 and "Zu viele Anfragen" in r.json()["detail"]
    # another client is not affected
    assert client.post("/api/v1/contact", json=ANBIETER, headers={"X-Forwarded-For": "198.51.100.7"}).status_code == 202
    assert len(store) == 4


def test_sliding_window():
    rl = kontakt.RateLimiter()
    assert all(rl.erlaubt("a", 2, 10, jetzt=t) for t in (0, 1))
    assert not rl.erlaubt("a", 2, 10, jetzt=5)
    assert rl.erlaubt("a", 2, 10, jetzt=10.5)  # the first hit left the window


def test_storage_failure_503():
    kontakt.rate_limiter.reset()
    with patch("backend.app.routers.kontakt.kontakt.speichern", side_effect=RuntimeError("Firestore weg")):
        r = client.post("/api/v1/contact", json=ANBIETER)
    assert r.status_code == 503 and "per E-Mail" in r.json()["detail"]


def test_speichern_sets_retention(monkeypatch):
    fs = MagicMock()
    monkeypatch.setattr(kontakt, "get_firestore_client", lambda: fs)
    monkeypatch.setattr(settings, "CONTACT_RETENTION_DAYS", 365)
    anfrage_id = kontakt.speichern({"zielgruppe": "anbieter", "name": "X Y"})
    fs.collection.assert_called_with("kontaktanfragen")
    doc = fs.collection.return_value.document.return_value.set.call_args.args[0]
    assert (doc["loeschen_am"] - doc["eingegangen_am"]).days == 365 and len(anfrage_id) == 32


def test_mail_only_when_configured(monkeypatch):
    daten = {**HERSTELLER, "website": None}
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    assert kontakt.benachrichtigen("id", daten) is False
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(settings, "SMTP_FROM", "website@example.org")
    monkeypatch.setattr(settings, "CONTACT_NOTIFY_TO", "vertrieb@example.org")
    with patch("backend.app.services.kontakt.smtplib.SMTP") as smtp:
        assert kontakt.benachrichtigen("id", daten) is True
        msg = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert "Beispiel GmbH (Hersteller)" in msg["Subject"] and msg["Reply-To"] == daten["email"]
    with patch("backend.app.services.kontakt.smtplib.SMTP", side_effect=OSError("kein Server")):
        assert kontakt.benachrichtigen("id", daten) is False  # logged, request still counts
