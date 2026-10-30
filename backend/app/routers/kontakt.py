"""POST /contact: contact form of the website /pilot (WEBSITE_PLAN Phase 6).

Validation (schemas/kontakt.py), honeypot, rate limit per client IP,
storage in Firestore, optional e-mail. Public, no login.
"""
from fastapi import APIRouter, HTTPException, Request, status

from ..config import settings
from ..schemas.kontakt import KontaktAnfrage
from ..services import kontakt

router = APIRouter()

ANTWORT = {"status": "eingegangen"}


def _client_ip(request: Request) -> str:
    # Cloud Run sets X-Forwarded-For; the first entry is the client
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unbekannt")


@router.post("/contact", status_code=status.HTTP_202_ACCEPTED)
async def contact(body: KontaktAnfrage, request: Request) -> dict:
    if not kontakt.rate_limiter.erlaubt(_client_ip(request), settings.CONTACT_RATE_LIMIT, settings.CONTACT_RATE_WINDOW_S):
        raise HTTPException(status_code=429, detail="Zu viele Anfragen. Bitte versuchen Sie es später erneut.")
    if body.website:
        # honeypot filled: answer like a success, store nothing
        return ANTWORT
    daten = body.model_dump(exclude={"website"})
    try:
        anfrage_id = kontakt.speichern(daten)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Anfrage konnte nicht gespeichert werden. Bitte schreiben Sie uns per E-Mail.") from exc
    kontakt.benachrichtigen(anfrage_id, daten)
    return ANTWORT
