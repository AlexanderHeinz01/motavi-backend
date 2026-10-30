"""Contact request of the website form /pilot (WEBSITE_PLAN Phase 6)."""
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Pragmatic check: something@domain.tld, no spaces (no extra dependency)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class KontaktAnfrage(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    zielgruppe: Literal["hersteller", "anbieter"]
    name: str = Field(min_length=2, max_length=120)
    unternehmen: str = Field(min_length=2, max_length=160)
    funktion: Optional[str] = Field(default=None, max_length=120)
    email: str = Field(max_length=200)
    telefon: Optional[str] = Field(default=None, max_length=40)
    anzahl_arbeitsplaetze: Optional[int] = Field(default=None, ge=1, le=100000)
    interesse: list[Literal["kapazitaet", "automatisierung", "gesundheit"]] = Field(default_factory=list, max_length=3)
    nachricht: Optional[str] = Field(default=None, max_length=4000)
    # Honeypot: hidden field, people leave it empty
    website: Optional[str] = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        if not _EMAIL.match(v):
            raise ValueError("Bitte eine gültige E-Mail-Adresse angeben.")
        return v.lower()

    @field_validator("telefon")
    @classmethod
    def _telefon(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.fullmatch(r"[0-9 +()/.-]{5,40}", v):
            raise ValueError("Bitte nur Ziffern, Leerzeichen und + ( ) / - verwenden.")
        return v or None

    @field_validator("interesse")
    @classmethod
    def _eindeutig(cls, v: list) -> list:
        return list(dict.fromkeys(v))
