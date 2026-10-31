"""Password hashing (bcrypt) and signed tokens (JWT).

Three kinds of token share JWT_SECRET and are told apart by the claim "typ":
  access  sign-in of a user (sub = e-mail)
  upload  upload link for a customer (job = job id), see routers/upload_links.py
  bild    short-lived access to one critical frame (job, datei)
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# Roles of the Motavi team: see every job, review steps, confirm Steckbriefe,
# create upload links (STECKBRIEF_MODUL §4.3). Everyone else sees own jobs only.
BERATER_ROLES = {"berater", "admin"}


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "access",
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a sign-in token. Raises jwt.PyJWTError on failure.

    Tokens issued before "typ" existed count as access tokens; upload and
    frame tokens are rejected here.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("typ", "access") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def create_token(typ: str, minutes: int, **claims) -> str:
    """Signed token of another kind (upload, bild), valid for *minutes*."""
    now = datetime.now(timezone.utc)
    payload = {"typ": typ, "iat": now, "exp": now + timedelta(minutes=minutes), **claims}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, typ: str) -> dict:
    """Verify a token of kind *typ*. Raises jwt.PyJWTError on failure or another kind."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("typ") != typ:
        raise jwt.InvalidTokenError(f"not a {typ} token")
    return payload
