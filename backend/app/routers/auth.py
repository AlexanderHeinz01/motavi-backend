from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from ..services import auth as auth_svc
from ..services import users as users_svc

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


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
    except Exception as exc:  # Firestore unavailable
        raise HTTPException(status_code=503, detail=f"User store unavailable: {exc}")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# Roles that may review process steps and confirm Steckbriefe (STECKBRIEF_MODUL §4.3)
BERATER_ROLES = {"berater", "admin"}


async def require_berater(user: dict = Depends(get_current_user)) -> dict:
    """Signed-in consultant; everyone else gets 403."""
    if user.get("role") not in BERATER_ROLES:
        raise HTTPException(status_code=403, detail="Nur für angemeldete Berater.")
    return user


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    _require_config()
    try:
        user = users_svc.get_user_by_email(body.email)
    except Exception as exc:  # Firestore unavailable
        raise HTTPException(status_code=503, detail=f"User store unavailable: {exc}")
    if not user or not auth_svc.verify_password(body.password, user.get("password_hash", "")):
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
    if not settings.SETUP_KEY or x_setup_key != settings.SETUP_KEY:
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
    except Exception as exc:  # Firestore unavailable
        raise HTTPException(status_code=503, detail=f"User store unavailable: {exc}")
    return _to_public(created)
