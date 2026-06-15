"""User records stored in Firestore (collection ``users``, keyed by email)."""
from datetime import datetime, timezone
from typing import Optional

from ..dependencies import get_firestore_client

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
