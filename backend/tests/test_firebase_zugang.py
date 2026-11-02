"""Sign-in with Firebase, access grants and the job overview (02.11.2026)."""
import datetime as dt
import time
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from google.auth import crypt
from google.auth import jwt as google_jwt

from backend.app.main import app
from backend.app.routers import auth as auth_router
from backend.app.services import analyzer, firebase_auth, jobs, users

client = TestClient(app)
PROJEKT = "motavi-test"


def _schluessel():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    jetzt = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(jetzt - dt.timedelta(days=1)).not_valid_after(jetzt + dt.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    pem_key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return crypt.RSASigner.from_string(pem_key, key_id="k1"), cert.public_bytes(serialization.Encoding.PEM).decode()


SIGNER, CERT = _schluessel()


def token(**claims) -> str:
    jetzt = int(time.time())
    payload = {"iss": f"https://securetoken.google.com/{PROJEKT}", "aud": PROJEKT, "sub": "uid1", "iat": jetzt,
               "exp": jetzt + 3600, "email": "berater@example.org", "email_verified": True,
               "firebase": {"sign_in_provider": "password"}, **claims}
    return google_jwt.encode(SIGNER, payload).decode()


@pytest.fixture
def firebase(monkeypatch):
    monkeypatch.setattr(firebase_auth.settings, "FIREBASE_PROJECT_ID", PROJEKT)
    monkeypatch.setattr(firebase_auth.settings, "ADMIN_EMAILS", "chefin@example.org")
    monkeypatch.setattr(firebase_auth, "_certs", lambda neu=False: {"k1": CERT})
    konten = {"berater@example.org": {"email": "berater@example.org", "role": "berater"}}
    monkeypatch.setattr(users, "get_user_by_email", lambda e: konten.get(e.strip().lower()))
    return konten


# ── token check ──────────────────────────────────────────────────────────────

def test_valid_token(firebase):
    assert firebase_auth.verify(token())["email"] == "berater@example.org"


@pytest.mark.parametrize("claims", [
    {"aud": "anderes-projekt"},
    {"iss": "https://securetoken.google.com/anderes-projekt"},
    {"exp": int(time.time()) - 60, "iat": int(time.time()) - 4000},
    {"sub": ""},
])
def test_invalid_tokens(firebase, claims):
    with pytest.raises(Exception):
        firebase_auth.verify(token(**claims))


def test_foreign_signature(firebase):
    fremd, _ = _schluessel()
    jetzt = int(time.time())
    t = google_jwt.encode(fremd, {"iss": f"https://securetoken.google.com/{PROJEKT}", "aud": PROJEKT, "sub": "x", "iat": jetzt, "exp": jetzt + 60}).decode()
    with pytest.raises(Exception):
        firebase_auth.verify(t)


# ── access through the API ───────────────────────────────────────────────────

def me(t):
    return client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"})


def test_granted_user_signs_in(firebase):
    r = me(token())
    assert r.status_code == 200 and r.json()["role"] == "berater"


def test_without_grant_no_access(firebase):
    r = me(token(email="fremd@example.org"))
    assert r.status_code == 403 and "Kein Zugang" in r.json()["detail"]


def test_unconfirmed_password_address_no_access(firebase):
    assert me(token(email_verified=False)).status_code == 403
    # Google confirms addresses itself
    assert me(token(email_verified=False, firebase={"sign_in_provider": "google.com"})).status_code == 200


def test_fixed_admin_and_old_tokens(firebase):
    assert me(token(email="chefin@example.org")).json()["role"] == "admin"
    assert me("kein-firebase-token").status_code == 401


def test_password_sign_in_off_with_firebase(firebase):
    assert client.post("/api/v1/auth/login", json={"email": "a@b.de", "password": "x"}).status_code == 410
    assert client.post("/api/v1/auth/register", json={"email": "a@b.de", "password": "x" * 12}).status_code == 410


def test_config_for_the_sign_in_page(firebase, monkeypatch):
    monkeypatch.setattr(firebase_auth.settings, "FIREBASE_API_KEY", "AIza-test")
    monkeypatch.setattr(firebase_auth.settings, "FIREBASE_PROVIDERS", "password, google ,microsoft")
    c = client.get("/api/v1/auth/config").json()
    assert c["firebase"]["projectId"] == PROJEKT and c["firebase"]["authDomain"] == f"{PROJEKT}.firebaseapp.com"
    assert c["anbieter"] == ["password", "google", "microsoft"]


def test_config_without_firebase(monkeypatch):
    monkeypatch.setattr(firebase_auth.settings, "FIREBASE_PROJECT_ID", "")
    assert client.get("/api/v1/auth/config").json()["firebase"] is None


# ── access grants (admins only) ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def as_user(role, email=None):
    app.dependency_overrides[auth_router.get_current_user] = lambda: {"email": email or f"{role}@example.org", "role": role}


def test_grants_only_for_admins():
    as_user("berater")
    assert client.get("/api/v1/zugaenge").status_code == 403
    assert client.put("/api/v1/zugaenge/neu@example.org", json={"role": "berater"}).status_code == 403


def test_grant_and_withdraw(monkeypatch):
    as_user("admin")
    monkeypatch.setattr(users.settings, "ADMIN_EMAILS", "admin@example.org")
    with patch.object(users, "zugang_setzen", return_value={"email": "neu@example.org", "role": "berater"}) as setzen, \
         patch.object(users, "zugang_entfernen") as entfernen:
        assert client.put("/api/v1/zugaenge/Neu@Example.org", json={"role": "berater", "name": "Neu"}).status_code == 200
        setzen.assert_called_once_with("neu@example.org", "berater", "Neu", "admin@example.org")
        assert client.put("/api/v1/zugaenge/neu@example.org", json={"role": "chef"}).status_code == 422
        assert client.put("/api/v1/zugaenge/keine-adresse", json={"role": "user"}).status_code == 422
        assert client.delete("/api/v1/zugaenge/neu@example.org").status_code == 204
        entfernen.assert_called_once_with("neu@example.org")
        # fixed admins and the own access stay
        assert client.delete("/api/v1/zugaenge/admin@example.org").status_code == 409


# ── job overview ─────────────────────────────────────────────────────────────

JOBS = [
    {"job_id": "a", "erstellt_von": "berater@example.org", "erstellt_am": "2026-11-01T10:00:00", "quelle": "upload_link",
     "status": "fertig", "meta": {"department": "Montage", "task_description": "Platz 3"}},
    {"job_id": "b", "erstellt_von": "kunde@example.org", "erstellt_am": "2026-11-02T09:00:00", "quelle": "intern",
     "status": "processing", "meta": {}},
]


def test_overview_newest_first_for_the_team():
    as_user("berater")
    with patch.object(jobs.gcs, "list_json", return_value=JOBS) as liste:
        r = client.get("/api/v1/jobs")
    liste.assert_called_once_with("results/*/job.json")
    assert [j["job_id"] for j in r.json()] == ["b", "a"]
    assert r.json()[1]["arbeitsplatz"] == "Montage · Platz 3"


def test_overview_own_jobs_only_for_users():
    as_user("user", "kunde@example.org")
    with patch.object(jobs.gcs, "list_json", return_value=JOBS):
        assert [j["job_id"] for j in client.get("/api/v1/jobs").json()] == ["b"]


def test_analysis_sets_the_job_status():
    with patch.object(analyzer, "_run", return_value=True), patch.object(analyzer, "_delete_raw"), \
         patch.object(jobs, "status_setzen") as setzen:
        analyzer._pipeline_sync("j1", {})
    setzen.assert_called_once_with("j1", "fertig")
    with patch.object(analyzer, "_run", side_effect=RuntimeError), patch.object(analyzer, "_delete_raw"), \
         patch.object(analyzer, "_write_error"), patch.object(jobs, "status_setzen") as setzen:
        analyzer._pipeline_sync("j1", {})
    setzen.assert_called_once_with("j1", "fehler")
