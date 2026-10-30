"""Contact requests: rate limit, storage in Firestore, optional e-mail.

Firestore collection ``kontaktanfragen``; every document carries
``loeschen_am`` for a TTL policy (docs/KONTAKT.md), so requests are deleted
after CONTACT_RETENTION_DAYS without further action.
"""
from __future__ import annotations

import logging
import smtplib
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from ..config import settings
from ..dependencies import get_firestore_client

logger = logging.getLogger(__name__)
_COLLECTION = "kontaktanfragen"


class RateLimiter:
    """Sliding window per key, in memory (per instance; enough against simple floods)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def erlaubt(self, key: str, limit: int, fenster_s: float, jetzt: float | None = None) -> bool:
        t = time.monotonic() if jetzt is None else jetzt
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= t - fenster_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(t)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


def speichern(daten: dict) -> str:
    """Store a request; returns its id."""
    jetzt = datetime.now(timezone.utc)
    anfrage_id = uuid.uuid4().hex
    doc = {
        **daten,
        "eingegangen_am": jetzt,
        "loeschen_am": jetzt + timedelta(days=settings.CONTACT_RETENTION_DAYS),
    }
    get_firestore_client().collection(_COLLECTION).document(anfrage_id).set(doc)
    return anfrage_id


ZIELGRUPPE_TEXT = {"hersteller": "Hersteller", "anbieter": "Robotik-Anbieter oder Integrator"}


def benachrichtigen(anfrage_id: str, daten: dict) -> bool:
    """E-mail to CONTACT_NOTIFY_TO if SMTP is configured; failures are logged, not raised."""
    if not (settings.SMTP_HOST and settings.CONTACT_NOTIFY_TO and settings.SMTP_FROM):
        return False
    msg = EmailMessage()
    msg["Subject"] = f"Pilot-Anfrage: {daten['unternehmen']} ({ZIELGRUPPE_TEXT[daten['zielgruppe']]})"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = settings.CONTACT_NOTIFY_TO
    msg["Reply-To"] = daten["email"]
    zeilen = [f"{k}: {v}" for k, v in daten.items() if v not in (None, [], "")]
    msg.set_content("\n".join([f"Anfrage {anfrage_id}", "", *zeilen]))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception:  # the request is stored; the mail is only a convenience
        logger.exception("Kontakt-Benachrichtigung fehlgeschlagen (%s)", anfrage_id)
        return False
