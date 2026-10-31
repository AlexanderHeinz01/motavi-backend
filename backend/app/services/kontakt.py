"""Contact requests: rate limit, storage in Firestore, optional e-mail.

Firestore collection ``kontaktanfragen``; every document carries
``loeschen_am`` for a TTL policy (docs/KONTAKT.md), so requests are deleted
after CONTACT_RETENTION_DAYS without further action.
"""
from __future__ import annotations

import ipaddress
import logging
import smtplib
import ssl
import threading
import time
import uuid
from collections import OrderedDict, deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from ..config import settings
from ..dependencies import get_firestore_client

logger = logging.getLogger(__name__)
_COLLECTION = "kontaktanfragen"


def ip_schluessel(adresse: str) -> str:
    """Rate limit key of an address: IPv4 as is, IPv6 per /64 network (one
    connection usually has a whole /64). Anything else counts together."""
    try:
        ip = ipaddress.ip_address(adresse)
    except ValueError:
        return "ungueltig"
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


class RateLimiter:
    """Sliding window per key, in memory (per instance; enough against simple
    floods). At most max_keys keys; the least recently used go first, empty
    windows are removed, so memory stays bounded."""

    def __init__(self, max_keys: int = 10_000) -> None:
        self._hits: OrderedDict[str, deque] = OrderedDict()
        self._lock = threading.Lock()
        self.max_keys = max_keys

    def erlaubt(self, key: str, limit: int, fenster_s: float, jetzt: float | None = None) -> bool:
        t = time.monotonic() if jetzt is None else jetzt
        with self._lock:
            q = self._hits.pop(key, None) or deque()
            while q and q[0] <= t - fenster_s:
                q.popleft()
            erlaubt = len(q) < limit
            if erlaubt:
                q.append(t)
            if q:
                self._hits[key] = q  # most recently used at the end
            while len(self._hits) > self.max_keys:
                self._hits.popitem(last=False)
            return erlaubt

    def __len__(self) -> int:
        return len(self._hits)

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


def benachrichtigen(anfrage_id: str, zielgruppe: str) -> bool:
    """Notice to CONTACT_NOTIFY_TO if SMTP is configured; failures are logged, not raised.

    Without the content of the request (decision on 31.10.2026): no personal
    data in mailboxes outside the 365 days; the request is read in Firestore.
    """
    if not (settings.SMTP_HOST and settings.CONTACT_NOTIFY_TO and settings.SMTP_FROM):
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Neue Pilot-Anfrage ({ZIELGRUPPE_TEXT.get(zielgruppe, 'Website')})"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = settings.CONTACT_NOTIFY_TO
        msg.set_content(
            "Über die Website ist eine neue Anfrage eingegangen.\n\n"
            f"Firestore, Sammlung {_COLLECTION}, Dokument {anfrage_id}\n\n"
            "Die Anfrage wird nach 365 Tagen automatisch gelöscht. "
            "Bitte innerhalb einer Woche antworten."
        )
        kontext = ssl.create_default_context()
        if settings.SMTP_PORT == 465:
            verbindung = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10, context=kontext)
        else:
            verbindung = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        with verbindung as s:
            if settings.SMTP_PORT != 465:
                s.starttls(context=kontext)
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception:  # the request is stored; the mail is only a convenience
        logger.exception("Kontakt-Benachrichtigung fehlgeschlagen (%s)", anfrage_id)
        return False
