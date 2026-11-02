"""User records stored in Firestore (collection ``users``, keyed by email).

With Firebase sign-in (services/firebase_auth.py) a record is the access
grant: only e-mail addresses with a record and a role get in. Addresses in
ADMIN_EMAILS are always admin (to grant the first accesses). Records from the
former password sign-in keep working as grants.
"""
from datetime import datetime, timezone
from typing import Optional

from ..config import settings
from ..dependencies import get_firestore_client

ROLLEN = ("user", "berater", "admin")

_COLLECTION = "users"


def _doc_id(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[dict]:
    snap = get_firestore_client().collection(_COLLECTION).document(_doc_id(email)).get()
    return snap.to_dict() if snap.exists else None


def create_user(
    email: str,
    password_hash: str,
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: str = "user",
) -> dict:
    data = {
        "email": _doc_id(email),
        "password_hash": password_hash,
        "name": name,
        "company": company,
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    get_firestore_client().collection(_COLLECTION).document(_doc_id(email)).set(data)
    return data


def admin_emails() -> set[str]:
    return {e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()}


def zugang(email: str) -> Optional[dict]:
    """Access record of an e-mail address, or None without access."""
    email = _doc_id(email)
    if email in admin_emails():
        return {"email": email, "role": "admin", "fest": True}
    user = get_user_by_email(email)
    if not user or user.get("role") not in ROLLEN:
        return None
    return user


def zugaenge() -> list[dict]:
    """All grants without password hashes, fixed admins first."""
    fest = [{"email": e, "role": "admin", "fest": True} for e in sorted(admin_emails())]
    docs = get_firestore_client().collection(_COLLECTION).stream()
    rest = [
        {k: v for k, v in d.to_dict().items() if k != "password_hash"}
        for d in docs
        if d.id not in admin_emails()
    ]
    return fest + sorted(rest, key=lambda u: u.get("email", ""))


def zugang_setzen(email: str, role: str, name: Optional[str], von: str) -> dict:
    data = {
        "email": _doc_id(email),
        "role": role,
        "name": name,
        "freigegeben_von": von,
        "freigegeben_am": datetime.now(timezone.utc).isoformat(),
    }
    get_firestore_client().collection(_COLLECTION).document(_doc_id(email)).set(data, merge=True)
    return data


def zugang_entfernen(email: str) -> None:
    get_firestore_client().collection(_COLLECTION).document(_doc_id(email)).delete()
