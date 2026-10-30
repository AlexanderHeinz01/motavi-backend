"""API models of the Steckbrief module (STECKBRIEF_MODUL §6)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Klasse = Literal["wertschoepfend", "notwendig", "verschwendung"]


class SegmentReview(BaseModel):
    start_phase: float = Field(ge=0, le=1)
    ende_phase: float = Field(ge=0, le=1)
    typ: str
    # default: the class of the type (segments.STEP_TYPES)
    klasse: Optional[Klasse] = None


class ReviewRequest(BaseModel):
    segmente: list[SegmentReview] = Field(min_length=1)
    kommentar: Optional[str] = Field(default=None, max_length=2000)


class SegmentVorschlag(BaseModel):
    start_phase: float
    ende_phase: float
    start_s: float
    ende_s: float
    dauer_s: float
    art: Literal["bewegung", "ruhe", "ortswechsel"]
    vorschlag_typ: Optional[str] = None


class ZyklenInfo(BaseModel):
    erkannt: bool
    hinweis: Optional[str] = None
    median_s: Optional[float] = None
    anzahl_gueltig: int
    konfidenz: float
    zyklen_pro_schicht: Optional[float] = None


class MedianZyklusDaten(BaseModel):
    dauer_s: float
    anzahl_zyklen: int
    phase: list[float]
    hand_speed: list[float]
    hip_speed: list[float]


class ReviewGespeichert(BaseModel):
    segmente: list[SegmentReview]
    kommentar: Optional[str] = None
    bestaetigt_von: str
    bestaetigt_am: str


class AblaufErgebnisDaten(BaseModel):
    ablaufschritte: list[dict]
    anteile_ablauf: dict[str, float]
    sekunden_je_zyklus: dict[str, float]
    minuten_pro_schicht: dict[str, Optional[float]]
    anzahl_zyklen: int
    hinweis: str


class AblaufResponse(BaseModel):
    job_id: str
    zyklen: ZyklenInfo
    median_zyklus: Optional[MedianZyklusDaten] = None
    vorschlag: list[SegmentVorschlag]
    typen: dict[str, Klasse]
    review: Optional[ReviewGespeichert] = None
    ergebnis: Optional[AblaufErgebnisDaten] = None


class Abmessungen(BaseModel):
    laenge: Optional[float] = Field(default=None, gt=0, le=1000)
    breite: Optional[float] = Field(default=None, gt=0, le=1000)
    hoehe: Optional[float] = Field(default=None, gt=0, le=1000)


class Kundenangaben(BaseModel):
    """Customer inputs (STECKBRIEF_MODUL §4.5); everything optional, the
    Steckbrief uses what is there and names what is missing."""

    model_config = {"extra": "forbid"}

    teilegewicht_kg: Optional[float] = Field(default=None, ge=0, le=1000)
    abmessungen_cm: Optional[Abmessungen] = None
    anzahl_varianten: Optional[int] = Field(default=None, ge=1, le=10000)
    stueck_pro_schicht: Optional[int] = Field(default=None, ge=1, le=100000)
    schichten_pro_tag: Optional[int] = Field(default=None, ge=1, le=4)
    schichtdauer_min: Optional[int] = Field(default=None, ge=60, le=720)
    arbeitstage_pro_jahr: Optional[int] = Field(default=None, ge=1, le=366)
    vollkosten_euro_pro_stunde: Optional[float] = Field(default=None, gt=0, le=1000)
    besetzung_schwierigkeit: Optional[int] = Field(default=None, ge=1, le=5)
    # rough investment range for the automation; without it the default of the type applies
    investition_euro: Optional[tuple[float, float]] = None

    @model_validator(mode="after")
    def _range(self):
        if self.investition_euro is not None:
            lo, hi = self.investition_euro
            if not 0 < lo <= hi:
                raise ValueError("investition_euro: von muss größer 0 und höchstens bis sein")
        return self


class EmpfehlungBestaetigung(BaseModel):
    """The expert's decision on recommendation and type (STECKBRIEF_MODUL §6.4)."""

    model_config = {"extra": "forbid"}

    empfehlung_id: Literal["improve-then-automate", "improve", "automate", "keep"]
    # only with a recommendation with automation; None: type left open
    typ_id: Optional[str] = None
    kommentar: Optional[str] = Field(default=None, max_length=2000)
