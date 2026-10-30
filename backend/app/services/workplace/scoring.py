"""Scores, recommendation, priority and automation type (STECKBRIEF_MODUL §5).

Everything configurable comes from config/workplace_scoring.json
(scoring_config). Inputs are plain metric values (Kennzahlen dict): a metric
that is missing or not reliable is None. A criterion without a value drops
out and its weight is spread over the others; below min_gewicht_vorhanden the
score is not reliable and there is no recommendation (guideline 3).

The tool proposes, the expert confirms: the recommendation and the type are
proposals.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .quality import NICHT_BELASTBAR
from .scoring_config import Bedingung, Index, Score, ScoringConfig, TypRegel

# Display names of the metrics used in conditions and criteria
KENNZAHL_TEXT = {
    "verschwendung_anteil": "Zeitanteil Verschwendung",
    "griffe_ausserhalb": "Griffe außerhalb des Greifraums",
    "belastung_index": "Belastungsindex",
    "handhabbarkeit_index": "Handhabbarkeitsindex",
    "zykluszeit_vk": "Variationskoeffizient Zykluszeit",
    "zyklen_pro_schicht": "Zyklen pro Schicht",
    "zeitanteil_in_zyklen": "Zeitanteil in Zyklen",
    "anzahl_varianten": "Varianten",
    "besetzung_schwierigkeit": "Schwierigkeit der Stellenbesetzung",
    "teilegewicht_kg": "Teilegewicht in kg",
    "groesste_kante_cm": "größte Kante in cm",
    "zone_knie_bis_schulter": "Zeitanteil Hände zwischen Knie und Schulter",
    "reba_mittel": "REBA-Mittel",
    "buecken_anteil": "Zeitanteil Bücken",
    "ueberkopf_anteil": "Zeitanteil Überkopf",
    "drehung_anteil": "Zeitanteil Drehung",
}


def runden(x: float) -> int:
    """Half up (Python's round() rounds half to even)."""
    return int(math.floor(x + 0.5))


# ── weighted indices and scores ──────────────────────────────────────────────


@dataclass(frozen=True)
class IndexErgebnis:
    wert: float | None  # 0..1
    vorhanden: float  # share of the weight with a value
    teile: dict[str, float | None]  # partial value 0..1 per metric


def index(cfg: Index, werte: dict[str, float | None]) -> IndexErgebnis:
    teile: dict[str, float | None] = {}
    summe = gewicht = 0.0
    for name, teil in cfg.teile.items():
        w = werte.get(name)
        if w is None:
            teile[name] = None
            continue
        teile[name] = teil(w)
        summe += teil.gewicht * teile[name]
        gewicht += teil.gewicht
    total = sum(t.gewicht for t in cfg.teile.values())
    vorhanden = gewicht / total if total else 0.0
    wert = summe / gewicht if gewicht and vorhanden >= cfg.min_gewicht_vorhanden else None
    return IndexErgebnis(wert, vorhanden, teile)


@dataclass(frozen=True)
class KriteriumErgebnis:
    id: str
    text: str
    quelle: str
    kennzahl: str
    gewicht: float
    messwert: float | None
    teilwert: float | None  # 0..1
    beitrag: float | None  # points of the score


@dataclass(frozen=True)
class ScoreErgebnis:
    wert: int | None  # 0..100, None = not reliable
    belastbar: bool
    vorhanden: float  # share of the weight with a value
    kriterien: list[KriteriumErgebnis]
    fehlend: list[str]  # texts of the criteria without a value

    @property
    def vollstaendig(self) -> bool:
        return not self.fehlend

    @property
    def anzeige(self) -> int | str:
        return self.wert if self.belastbar and self.wert is not None else NICHT_BELASTBAR


def score(cfg: Score, werte: dict[str, float | None], kein_zyklus: bool = False) -> ScoreErgebnis:
    """0..100: weighted mean of the partial values of the criteria with a value.

    kein_zyklus: the cycle detection found for sure no recurring cycle; then
    criteria with ohne_zyklus use that partial value instead of dropping out.
    """
    rows: list[tuple[str, object, float | None, float | None]] = []
    summe = gewicht = 0.0
    for kid, k in cfg.kriterien.items():
        w = werte.get(k.kennzahl)
        t = k(w) if w is not None else None
        if t is None and kein_zyklus and k.ohne_zyklus is not None:
            t = k.ohne_zyklus
        rows.append((kid, k, w, t))
        if t is not None:
            summe += k.gewicht * t
            gewicht += k.gewicht
    belastbar = gewicht >= cfg.min_gewicht_vorhanden - 1e-9 and gewicht > 0
    wert = runden(100 * summe / gewicht) if belastbar else None
    kriterien = [
        KriteriumErgebnis(
            id=kid, text=k.text, quelle=k.quelle, kennzahl=k.kennzahl, gewicht=k.gewicht,
            messwert=w, teilwert=None if t is None else round(t, 4),
            beitrag=None if t is None or not belastbar else round(100 * k.gewicht * t / gewicht, 1),
        )
        for kid, k, w, t in rows
    ]
    return ScoreErgebnis(wert, belastbar, round(gewicht, 4), kriterien, [k.text for k in kriterien if k.teilwert is None])


# ── recommendation and priority ──────────────────────────────────────────────


@dataclass(frozen=True)
class EmpfehlungErgebnis:
    id: str | None  # improve-then-automate, improve, automate, keep; None = no recommendation
    text: str
    vorlaeufig: bool  # a score lacks criteria
    mit_automatisierung: bool
    begruendung: list[str] = field(default_factory=list)
    status: str = "vorschlag"  # confirmed by the expert later (S5)


def empfehlung(cfg: ScoringConfig, v: ScoreErgebnis, a: ScoreErgebnis) -> EmpfehlungErgebnis:
    e = cfg.empfehlung
    if not (v.belastbar and a.belastbar):
        fehlt = [n for n, s in (("Verbesserungs-Score", v), ("Automatisierungs-Score", a)) if not s.belastbar]
        return EmpfehlungErgebnis(
            None, f"Keine Empfehlung: {' und '.join(fehlt)} nicht belastbar messbar.", True, False,
            [f"{n}: zu wenige Kriterien mit Messwert" for n in fehlt],
        )
    hv = "hoch" if v.wert >= e.schwelle_verbesserung else "niedrig"
    ha = "hoch" if a.wert >= e.schwelle_automatisierung else "niedrig"
    regel = next(r for r in e.regeln if r.verbesserung == hv and r.automatisierung == ha)
    begruendung = [
        f"Verbesserungs-Score {v.wert} {'ab' if hv == 'hoch' else 'unter'} {e.schwelle_verbesserung:g}",
        f"Automatisierungs-Score {a.wert} {'ab' if ha == 'hoch' else 'unter'} {e.schwelle_automatisierung:g}",
    ]
    return EmpfehlungErgebnis(
        regel.empfehlung, e.texte[regel.empfehlung], not (v.vollstaendig and a.vollstaendig),
        regel.empfehlung in e.mit_automatisierung, begruendung,
    )


@dataclass(frozen=True)
class VorrangErgebnis:
    vorrangig: bool
    text: str | None
    grund: str | None


def vorrang(cfg: ScoringConfig, reba_mittel: float | None) -> VorrangErgebnis:
    """Priority regardless of the recommendation (§5.3 additional rule)."""
    s = cfg.vorrang.reba_mittel_ab
    if reba_mittel is not None and reba_mittel >= s:
        wert = f"{reba_mittel:.1f}".replace(".", ",")
        return VorrangErgebnis(True, cfg.vorrang.text, f"REBA-Mittel {wert} ab {s:g}")
    return VorrangErgebnis(False, None, None)


# ── automation type ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BedingungErgebnis:
    text: str
    wert: float | None
    erfuellt: bool | None  # None = value missing


@dataclass(frozen=True)
class TypErgebnis:
    id: str
    name: str
    passt: bool | None  # None: no condition failed, but a value is missing
    bedingungen: list[BedingungErgebnis]


@dataclass(frozen=True)
class TypVorschlag:
    vorschlag: TypRegel | None
    text: str
    regeln: list[TypErgebnis]


def _bedingung(b: Bedingung, werte: dict[str, float | None], typ_anteile: dict[str, float] | None) -> BedingungErgebnis:
    if b.anteil_typen is not None:
        name = " + ".join(b.anteil_typen)
        wert = None if typ_anteile is None else sum(typ_anteile.get(t, 0.0) for t in b.anteil_typen)
        fmt = lambda x: f"{x * 100:g} %"  # noqa: E731
        label = f"Zeitanteil {name}"
    else:
        wert = werte.get(b.kennzahl)
        fmt = lambda x: f"{x:g}"  # noqa: E731
        label = KENNZAHL_TEXT.get(b.kennzahl, b.kennzahl)
    teile = []
    if b.ab is not None:
        teile.append(f"ab {fmt(b.ab)}")
    if b.bis is not None:
        teile.append(f"bis {fmt(b.bis)}")
    text = f"{label} {' und '.join(teile)}"
    if wert is None:
        return BedingungErgebnis(text, None, None)
    ok = (b.ab is None or wert >= b.ab) and (b.bis is None or wert <= b.bis)
    return BedingungErgebnis(text, round(wert, 4), ok)


def automatisierungstyp(cfg: ScoringConfig, werte: dict[str, float | None], typ_anteile: dict[str, float] | None) -> TypVorschlag:
    """Rules in their order; the first type whose conditions all hold is the proposal.

    typ_anteile: share of each process step type of the cycle (from the
    expert review); None if there is no review yet.
    """
    regeln: list[TypErgebnis] = []
    for r in cfg.automatisierungstypen.regeln:
        bs = [_bedingung(b, werte, typ_anteile) for b in r.bedingungen]
        if any(b.erfuellt is False for b in bs):
            passt = False
        elif all(b.erfuellt for b in bs):
            passt = True
        else:
            passt = None
        regeln.append(TypErgebnis(r.id, r.name, passt, bs))
    treffer = next((r for r, e in zip(cfg.automatisierungstypen.regeln, regeln) if e.passt), None)
    if treffer:
        return TypVorschlag(treffer, treffer.name, regeln)
    text = cfg.automatisierungstypen.kein_typ
    if typ_anteile is None:
        text = "Kein Typ: Ablaufschritte noch nicht vom Experten bestätigt."
    return TypVorschlag(None, text, regeln)
