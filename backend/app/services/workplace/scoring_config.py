"""Scoring configuration of the Steckbrief (STECKBRIEF_MODUL §5).

config/workplace_scoring.json in the repository root is the only source for
weights, thresholds, avoidable shares and rules. The website's
Arbeitsplatz-Check reads the same file. This module only loads and checks it;
keys starting with "_" are comments.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

KLASSEN = ("wertschoepfend", "notwendig", "verschwendung")
EMPFEHLUNGEN = ("improve-then-automate", "improve", "automate", "keep")

# backend/app/services/workplace/ -> repository root
DEFAULT_PATH = Path(__file__).resolve().parents[4] / "config" / "workplace_scoring.json"
ENV_PATH = "WORKPLACE_SCORING_CONFIG"


class _Model(BaseModel):
    model_config = {"extra": "ignore"}


class Rampe(_Model):
    """Linear map: value at null_bei -> 0, at voll_bei -> 1, clamped. Inverse if null_bei > voll_bei."""

    null_bei: float
    voll_bei: float

    @model_validator(mode="after")
    def _distinct(self):
        if self.null_bei == self.voll_bei:
            raise ValueError("null_bei und voll_bei müssen verschieden sein")
        return self

    def __call__(self, wert: float) -> float:
        u = (wert - self.null_bei) / (self.voll_bei - self.null_bei)
        return min(1.0, max(0.0, u))


class Teil(Rampe):
    gewicht: float = Field(gt=0)


class Index(_Model):
    """Weighted index 0..1 from several metrics (load, handling)."""

    teile: dict[str, Teil]
    min_gewicht_vorhanden: float = Field(ge=0, le=1)

    @field_validator("teile", mode="before")
    @classmethod
    def _skip_comments(cls, v):
        return {k: x for k, x in v.items() if not k.startswith("_")}


class Kriterium(Teil):
    text: str
    quelle: str
    kennzahl: str
    # partial value if no recurring cycle was found (a result, §4.1); None: criterion drops out
    ohne_zyklus: Optional[float] = Field(default=None, ge=0, le=1)


class Score(_Model):
    kriterien: dict[str, Kriterium]
    min_gewicht_vorhanden: float = Field(ge=0, le=1)

    @field_validator("kriterien", mode="before")
    @classmethod
    def _skip_comments(cls, v):
        return {k: x for k, x in v.items() if not k.startswith("_")}

    @model_validator(mode="after")
    def _sum_one(self):
        total = sum(k.gewicht for k in self.kriterien.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Gewichte ergeben {total:.3f} statt 1")
        return self


class Regel(_Model):
    verbesserung: Literal["hoch", "niedrig"]
    automatisierung: Literal["hoch", "niedrig"]
    empfehlung: Literal["improve-then-automate", "improve", "automate", "keep"]


class Empfehlung(_Model):
    schwelle_verbesserung: float = Field(ge=0, le=100)
    schwelle_automatisierung: float = Field(ge=0, le=100)
    regeln: list[Regel]
    texte: dict[str, str]
    mit_automatisierung: list[str]

    @model_validator(mode="after")
    def _complete(self):
        combos = {(r.verbesserung, r.automatisierung) for r in self.regeln}
        if len(combos) != 4 or len(self.regeln) != 4:
            raise ValueError("Die Regeln müssen jede Kombination aus hoch und niedrig genau einmal abdecken")
        missing = set(EMPFEHLUNGEN) - set(self.texte)
        if missing:
            raise ValueError(f"Texte fehlen für {sorted(missing)}")
        return self


class Vorrang(_Model):
    reba_mittel_ab: float
    text: str


class Bedingung(_Model):
    kennzahl: Optional[str] = None
    anteil_typen: Optional[list[str]] = None
    ab: Optional[float] = None
    bis: Optional[float] = None

    @model_validator(mode="after")
    def _one_source(self):
        if (self.kennzahl is None) == (self.anteil_typen is None):
            raise ValueError("Bedingung braucht entweder kennzahl oder anteil_typen")
        if self.ab is None and self.bis is None:
            raise ValueError("Bedingung braucht ab oder bis")
        return self


class TypRegel(_Model):
    id: str
    name: str
    bedingungen: list[Bedingung] = Field(min_length=1)
    automatisierbarer_anteil: tuple[float, float]
    investition_euro: tuple[float, float]
    # share of the saved labour cost that running the system costs again (maintenance, energy, programming)
    betriebskosten_anteil: tuple[float, float]

    @model_validator(mode="after")
    def _ranges(self):
        lo, hi = self.automatisierbarer_anteil
        if not 0 < lo <= hi <= 1:
            raise ValueError(f"{self.id}: automatisierbarer_anteil muss 0 < von <= bis <= 1 sein")
        lo, hi = self.betriebskosten_anteil
        if not 0 <= lo <= hi < 1:
            raise ValueError(f"{self.id}: betriebskosten_anteil muss 0 <= von <= bis < 1 sein")
        if not 0 < self.investition_euro[0] <= self.investition_euro[1]:
            raise ValueError(f"{self.id}: investition_euro muss 0 < von <= bis sein")
        return self


class Typen(_Model):
    regeln: list[TypRegel] = Field(min_length=1)
    kein_typ: str


class Kundenangaben(_Model):
    plausibilitaet_toleranz: float = Field(gt=0)


class Wirtschaftlichkeit(_Model):
    hinweis: str


class ScoringConfig(_Model):
    version: int
    schritt_typen: dict[str, Literal["wertschoepfend", "notwendig", "verschwendung"]]
    vermeidbarer_anteil: dict[str, float]
    belastung: Index
    handhabbarkeit: Index
    verbesserungs_score: Score
    automatisierungs_score: Score
    empfehlung: Empfehlung
    vorrang: Vorrang
    automatisierungstypen: Typen
    kundenangaben: Kundenangaben
    wirtschaftlichkeit: Wirtschaftlichkeit

    @field_validator("schritt_typen", "vermeidbarer_anteil", mode="before")
    @classmethod
    def _skip_comments(cls, v):
        return {k: x for k, x in v.items() if not k.startswith("_")}

    @model_validator(mode="after")
    def _consistent(self):
        for typ, anteil in self.vermeidbarer_anteil.items():
            if typ not in self.schritt_typen:
                raise ValueError(f"vermeidbarer_anteil: unbekannter Typ {typ!r}")
            if not 0 <= anteil <= 1:
                raise ValueError(f"vermeidbarer_anteil {typ}: {anteil} liegt nicht zwischen 0 und 1")
        for regel in self.automatisierungstypen.regeln:
            for b in regel.bedingungen:
                for typ in b.anteil_typen or []:
                    if typ not in self.schritt_typen:
                        raise ValueError(f"{regel.id}: unbekannter Typ {typ!r}")
        return self


def load(path: str | Path | None = None) -> ScoringConfig:
    p = Path(path or os.environ.get(ENV_PATH) or DEFAULT_PATH)
    with open(p, encoding="utf-8") as f:
        return ScoringConfig.model_validate(json.load(f))


@lru_cache(maxsize=1)
def get() -> ScoringConfig:
    """The configuration of the running service (read once)."""
    return load()
