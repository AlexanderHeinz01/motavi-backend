"""Access grants for the sign-in with Firebase (admins only).

GET    /zugaenge          all grants
PUT    /zugaenge/{email}  grant or change a role (user, berater, admin)
DELETE /zugaenge/{email}  withdraw
Addresses in ADMIN_EMAILS are fixed and cannot be changed here.
"""
import logging
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..services import users as users_svc
from .auth import require_admin

router = APIRouter()
logger = logging.getLogger(__name__)
_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$")


class ZugangRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "berater", "admin"]
    name: Optional[str] = Field(None, max_length=120)


def _pruefen(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=422, detail="Bitte eine gültige E-Mail-Adresse angeben.")
    if email in users_svc.admin_emails():
        raise HTTPException(status_code=409, detail="Diese Adresse ist fest als Admin eingetragen (ADMIN_EMAILS).")
    return email


@router.get("/zugaenge")
def liste(user: dict = Depends(require_admin)) -> list[dict]:
    try:
        return users_svc.zugaenge()
    except Exception:
        logger.exception("Listing the access grants failed")
        raise HTTPException(status_code=503, detail="Benutzerspeicher nicht erreichbar.")


@router.put("/zugaenge/{email}")
def setzen(email: str, body: ZugangRequest, user: dict = Depends(require_admin)) -> dict:
    email = _pruefen(email)
    try:
        return users_svc.zugang_setzen(email, body.role, body.name, user["email"])
    except Exception:
        logger.exception("Granting access failed")
        raise HTTPException(status_code=503, detail="Benutzerspeicher nicht erreichbar.")


@router.delete("/zugaenge/{email}", status_code=204)
def entfernen(email: str, user: dict = Depends(require_admin)) -> None:
    email = _pruefen(email)
    if email == user["email"]:
        raise HTTPException(status_code=409, detail="Den eigenen Zugang können Sie nicht entfernen.")
    try:
        users_svc.zugang_entfernen(email)
    except Exception:
        logger.exception("Withdrawing access failed")
        raise HTTPException(status_code=503, detail="Benutzerspeicher nicht erreichbar.")
