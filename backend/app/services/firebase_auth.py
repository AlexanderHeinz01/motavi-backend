"""Sign-in with Firebase Authentication (decision 02.11.2026).

The browser signs in with Firebase (Google, Microsoft or e-mail and
password) and sends the Firebase ID token as Bearer token. This module
checks the token: signature with Google's public keys (cached), audience and
issuer of our Firebase project, expiry.

Firebase lets anybody sign in with a Google account, and with e-mail and
password anybody can create an account through the public API. So the token
alone grants nothing: access needs a role (services/users.py, zugang).
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request

from google.auth import jwt as google_jwt

from ..config import settings

_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
_cache: dict = {"certs": {}, "bis": 0.0}
_lock = threading.Lock()


def _certs(neu: bool = False) -> dict:
    """Google's public keys for Firebase ID tokens, cached for an hour."""
    with _lock:
        if neu or time.time() >= _cache["bis"] or not _cache["certs"]:
            with urllib.request.urlopen(_CERTS_URL, timeout=10) as resp:
                _cache["certs"] = json.loads(resp.read())
            _cache["bis"] = time.time() + 3600
        return _cache["certs"]


def verify(token: str) -> dict:
    """Claims of a valid Firebase ID token of our project; ValueError otherwise."""
    projekt = settings.FIREBASE_PROJECT_ID
    if not projekt:
        raise ValueError("Firebase is not configured")
    certs = _certs()
    kid = google_jwt.decode_header(token).get("kid")
    if kid not in certs:  # keys rotate: fetch once more
        certs = _certs(neu=True)
    claims = google_jwt.decode(token, certs=certs, audience=projekt, clock_skew_in_seconds=10)
    if claims.get("iss") != f"https://securetoken.google.com/{projekt}":
        raise ValueError("wrong issuer")
    if not claims.get("sub"):
        raise ValueError("no subject")
    return claims


# Providers whose e-mail addresses are confirmed by the provider itself
_BESTAETIGTE_ANBIETER = {"google.com", "microsoft.com"}


def email_bestaetigt(claims: dict) -> bool:
    anbieter = (claims.get("firebase") or {}).get("sign_in_provider")
    return bool(claims.get("email_verified")) or anbieter in _BESTAETIGTE_ANBIETER
