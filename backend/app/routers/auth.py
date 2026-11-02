import hmac
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from ..services import auth as auth_svc
from ..services import firebase_auth
from ..services import jobs as jobs_svc
from ..services import kontakt as kontakt_svc
from ..services import users as users_svc

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

# Sign-in attempts per address and e-mail (E.3.15): 10 in 15 minutes
_anmeldungen = kontakt_svc.RateLimiter()
# bcrypt hash of a random value: unknown users take as long as known ones
_DUMMY_HASH = auth_svc.hash_password("dummy-password-for-timing")


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        email=user["email"],
        name=user.get("name"),
        company=user.get("company"),
        role=user.get("role", "user"),
    )


def _require_config() -> None:
    if not settings.JWT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Auth is not configured (JWT_SECRET missing).",
        )


def _firebase_user(token: str) -> dict:
    """User of a Firebase ID token: confirmed e-mail and a granted role."""
    try:
        claims = firebase_auth.verify(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Anmeldung abgelaufen oder ungültig.", headers={"WWW-Authenticate": "Bearer"})
    email = (claims.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=401, detail="Das Konto hat keine E-Mail-Adresse.")
    if not firebase_auth.email_bestaetigt(claims):
        raise HTTPException(status_code=403, detail="E-Mail-Adresse noch nicht bestätigt.")
    try:
        user = users_svc.zugang(email)
    except Exception:  # Firestore unavailable
        raise HTTPException(status_code=503, detail="Anmeldung derzeit nicht möglich.")
    if not user:
        raise HTTPException(status_code=403, detail="Kein Zugang. Bitte wenden Sie sich an das Motavi-Team.")
    return {**user, "email": email, "name": user.get("name") or claims.get("name")}


def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if cred is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if settings.FIREBASE_PROJECT_ID:
        return _firebase_user(cred.credentials)
    _require_config()
    try:
        payload = auth_svc.decode_access_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("sub")
    try:
        user = users_svc.get_user_by_email(email) if email else None
    except Exception:  # Firestore unavailable
        raise HTTPException(status_code=503, detail="Anmeldung derzeit nicht möglich.")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


BERATER_ROLES = auth_svc.BERATER_ROLES


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Nur für Admins.")
    return user


def require_berater(user: dict = Depends(get_current_user)) -> dict:
    """Signed-in consultant; everyone else gets 403."""
    if user.get("role") not in BERATER_ROLES:
        raise HTTPException(status_code=403, detail="Nur für angemeldete Berater.")
    return user


def require_job(job_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Signed-in user who may see this job (services/jobs.py); 404 otherwise,
    so that foreign job ids are not confirmed."""
    if not jobs_svc.gueltige_id(job_id):
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    try:
        job = jobs_svc.laden(job_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Speicher nicht erreichbar.")
    if not jobs_svc.darf_zugreifen(job, user):
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    return user


def require_berater_job(job_id: str, user: dict = Depends(require_berater)) -> dict:
    """Consultant and a well-formed job id (the team sees every job)."""
    if not jobs_svc.gueltige_id(job_id):
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    return user


@router.get("/auth/config")
def auth_config() -> dict:
    """Public sign-in configuration for the page: Firebase web config or the
    former password sign-in (firebase None)."""
    if not settings.FIREBASE_PROJECT_ID:
        return {"firebase": None, "anbieter": ["passwort_alt"]}
    return {
        "firebase": {
            "apiKey": settings.FIREBASE_API_KEY,
            "authDomain": settings.FIREBASE_AUTH_DOMAIN or f"{settings.FIREBASE_PROJECT_ID}.firebaseapp.com",
            "projectId": settings.FIREBASE_PROJECT_ID,
            "appId": settings.FIREBASE_APP_ID,
        },
        "anbieter": [a.strip() for a in settings.FIREBASE_PROVIDERS.split(",") if a.strip()],
    }


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    """Former password sign-in; off once Firebase is configured."""
    if settings.FIREBASE_PROJECT_ID:
        raise HTTPException(status_code=410, detail="Anmeldung über Firebase.")
    _require_config()
    adresse = request.client.host if request.client else ""
    if not _anmeldungen.erlaubt(f"{adresse}|{body.email.lower()}", 10, 900):
        raise HTTPException(status_code=429, detail="Zu viele Anmeldeversuche. Bitte warten Sie 15 Minuten.")
    try:
        user = users_svc.get_user_by_email(body.email)
    except Exception:  # Firestore unavailable
        raise HTTPException(status_code=503, detail="Anmeldung derzeit nicht möglich.")
    passwort_ok = auth_svc.verify_password(body.password, user.get("password_hash", "") if user else _DUMMY_HASH)
    if not user or not passwort_ok:
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort ist falsch.")
    token = auth_svc.create_access_token(user["email"])
    return TokenResponse(access_token=token, user=_to_public(user))


@router.get("/auth/me", response_model=UserPublic)
def me(user: dict = Depends(get_current_user)) -> UserPublic:
    return _to_public(user)


@router.post("/auth/register", response_model=UserPublic, status_code=201)
def register(
    body: RegisterRequest,
    x_setup_key: Optional[str] = Header(default=None),
) -> UserPublic:
    """Provision a user. Guarded by the X-Setup-Key header (bootstrap only).
    Off with Firebase: accesses are granted on the page Zugänge."""
    if settings.FIREBASE_PROJECT_ID:
        raise HTTPException(status_code=410, detail="Zugänge werden im Werkzeug unter Zugänge vergeben.")
    _require_config()
    if not settings.SETUP_KEY or not hmac.compare_digest((x_setup_key or "").encode(), settings.SETUP_KEY.encode()):
        raise HTTPException(status_code=403, detail="Registration disabled.")
    try:
        if users_svc.get_user_by_email(body.email):
            raise HTTPException(status_code=409, detail="User already exists.")
        created = users_svc.create_user(
            body.email,
            auth_svc.hash_password(body.password),
            body.name,
            body.company,
            body.role,
        )
    except HTTPException:
        raise
    except Exception:  # Firestore unavailable
        raise HTTPException(status_code=503, detail="Benutzerspeicher nicht erreichbar.")
    return _to_public(created)
