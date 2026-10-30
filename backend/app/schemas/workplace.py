"""API models of the Steckbrief module (STECKBRIEF_MODUL §6)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

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
