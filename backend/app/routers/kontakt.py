"""POST /contact: contact form of the website /pilot (WEBSITE_PLAN Phase 6).

Validation (schemas/kontakt.py), honeypot, rate limit per client IP,
storage in Firestore, optional e-mail. Public, no login.
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from ..config import settings
from ..schemas.kontakt import KontaktAnfrage
from ..services import kontakt

router = APIRouter()
logger = logging.getLogger(__name__)

ANTWORT = {"status": "eingegangen"}


def _client_ip(request: Request) -> str:
    """Rate limit key. The sender can write anything into X-Forwarded-For;
    the proxies append the address they saw. So the entry CONTACT_PROXY_HOPS
    from the right is the client (Cloud Run directly: the last one)."""
    eintraege = [e.strip() for e in request.headers.get("x-forwarded-for", "").split(",") if e.strip()]
    if len(eintraege) >= settings.CONTACT_PROXY_HOPS:
        return kontakt.ip_schluessel(eintraege[-settings.CONTACT_PROXY_HOPS])
    return kontakt.ip_schluessel(request.client.host if request.client else "")


@router.post("/contact", status_code=status.HTTP_202_ACCEPTED)
def contact(body: KontaktAnfrage, request: Request) -> dict:
    if not kontakt.rate_limiter.erlaubt(_client_ip(request), settings.CONTACT_RATE_LIMIT, settings.CONTACT_RATE_WINDOW_S):
        raise HTTPException(status_code=429, detail="Zu viele Anfragen. Bitte versuchen Sie es später erneut.")
    if body.website:
        # honeypot filled: answer like a success, store nothing
        return ANTWORT
    daten = body.model_dump(exclude={"website"})
    try:
        anfrage_id = kontakt.speichern(daten)
    except Exception:
        # without personal data in the log; alert on this message (docs/BETRIEB.md)
        logger.exception("Kontaktanfrage konnte nicht gespeichert werden")
        raise HTTPException(status_code=503, detail="Anfrage konnte nicht gespeichert werden. Bitte schreiben Sie uns per E-Mail.")
    kontakt.benachrichtigen(anfrage_id, daten["zielgruppe"])
    return ANTWORT
