import hmac
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from ..services import auth as auth_svc
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


async def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    _require_config()
    if cred is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
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


async def require_berater(user: dict = Depends(get_current_user)) -> dict:
    """Signed-in consultant; everyone else gets 403."""
    if user.get("role") not in BERATER_ROLES:
        raise HTTPException(status_code=403, detail="Nur für angemeldete Berater.")
    return user


async def require_job(job_id: str, user: dict = Depends(get_current_user)) -> dict:
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


async def require_berater_job(job_id: str, user: dict = Depends(require_berater)) -> dict:
    """Consultant and a well-formed job id (the team sees every job)."""
    if not jobs_svc.gueltige_id(job_id):
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    return user


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
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
async def me(user: dict = Depends(get_current_user)) -> UserPublic:
    return _to_public(user)


@router.post("/auth/register", response_model=UserPublic, status_code=201)
async def register(
    body: RegisterRequest,
    x_setup_key: Optional[str] = Header(default=None),
) -> UserPublic:
    """Provision a user. Guarded by the X-Setup-Key header (bootstrap only)."""
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
