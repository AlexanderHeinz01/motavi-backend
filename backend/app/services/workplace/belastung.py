"""Load (STECKBRIEF_MODUL §4.4).

From the ergonomics pipeline (result.json, unchanged): REBA mean and maximum,
time shares bending and overhead. In addition, from the pose data: trunk
twist and twists per cycle, because result.json has no twist.

Twist: angle between the shoulder line and the hip line seen from above
(x and depth z). z is MediaPipe's estimated depth from a single 2D image,
so the twist is a rough value (Pilotphase).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cycles import ZyklusErgebnis
from .preprocess import Prepared
from .quality import Kennzahl


@dataclass(frozen=True)
class BelastungConfig:
    twist_deg: float = 30.0  # shoulders turned against the hips from this angle
    min_twist_s: float = 0.3  # a twist counts if it lasts at least this long
    reliable: float = 0.5  # share of frames with shoulders and hips


@dataclass(frozen=True)
class BelastungErgebnis:
    reba_mittel: Kennzahl
    reba_max: Kennzahl
    buecken_anteil: Kennzahl
    ueberkopf_anteil: Kennzahl
    drehung_anteil: Kennzahl
    drehungen_pro_zyklus: Kennzahl
    hinweis: str = "Drehung aus der geschätzten Tiefe des 2D-Videos, grober Wert (Pilotphase)."


def twist_angle(prep: Prepared) -> np.ndarray:
    """Twist per frame in degrees (NaN without shoulders or hips)."""
    def line(a: str, b: str) -> np.ndarray:
        d = prep.joint(b) - prep.joint(a)
        return np.degrees(np.arctan2(d[:, 2], d[:, 0]))

    diff = line("left_shoulder", "right_shoulder") - line("left_hip", "right_hip")
    return (diff + 180.0) % 360.0 - 180.0


def _runs(flag: np.ndarray) -> list[tuple[int, int]]:
    out, start = [], None
    for i, f in enumerate(flag):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flag)))
    return out


def analyse_twist(prep: Prepared, zyklen: ZyklusErgebnis | None, cfg: BelastungConfig = BelastungConfig()) -> tuple[Kennzahl, Kennzahl]:
    """Time share with a twist and twists per valid cycle."""
    angle = twist_angle(prep)
    seen = prep.valid & np.isfinite(angle)
    coverage = float(seen.mean()) if seen.size else 0.0
    if not seen.any():
        k = Kennzahl.fehlt("Schultern und Hüfte nicht sichtbar")
        return k, k
    twisted = seen & (np.abs(np.nan_to_num(angle)) >= cfg.twist_deg)
    min_len = max(1, int(round(cfg.min_twist_s * prep.rate_hz)))
    starts = [prep.t[a] for a, b in _runs(twisted) if b - a >= min_len]
    share = float(sum(b - a for a, b in _runs(twisted) if b - a >= min_len)) / float(seen.sum())
    anteil = Kennzahl.bewertet(share, coverage, cfg.reliable)

    gueltig = [z for z in (zyklen.zyklen if zyklen and zyklen.erkannt else []) if z.gueltig and z.art == "zyklus"]
    if not gueltig:
        pro_zyklus = Kennzahl.fehlt("Kein wiederkehrender Zyklus erkannt")
    else:
        n = sum(1 for s in starts for z in gueltig if z.start_s <= s < z.ende_s)
        pro_zyklus = Kennzahl.bewertet(n / len(gueltig), coverage, cfg.reliable)
    return anteil, pro_zyklus


def from_result(result: dict, cfg: BelastungConfig = BelastungConfig()) -> dict[str, Kennzahl]:
    """Posture index (field names reba_*) and movement shares of the
    ergonomics pipeline (result.json). Quality: share of sampled frames with
    a detected person (erkennung_anteil, from 31.10.2026; older results 1.0)."""
    out: dict[str, Kennzahl] = {}
    q = float(result.get("erkennung_anteil", 1.0))

    def kz(wert: float) -> Kennzahl:
        return Kennzahl.bewertet(wert, q, cfg.reliable)

    reba = result.get("reba_score")
    out["reba_mittel"] = kz(float(reba)) if reba is not None else Kennzahl.fehlt("Kein Ergonomie-Ergebnis")
    spitze = result.get("reba_max")
    if spitze is None:
        peaks = [f.get("reba") for f in result.get("critical_frames") or [] if f.get("reba") is not None]
        spitze = max(peaks) if peaks else None
    out["reba_max"] = kz(float(spitze)) if spitze is not None else Kennzahl.fehlt("Keine kritischen Momente gespeichert")
    moves = result.get("movements") or {}
    for key, name in (("buecken_anteil", "bending"), ("ueberkopf_anteil", "overhead")):
        pct = (moves.get(name) or {}).get("pct")
        out[key] = kz(float(pct) / 100.0) if pct is not None else Kennzahl.fehlt("Kein Ergonomie-Ergebnis")
    return out


def analyse_belastung(result: dict, prep: Prepared | None, zyklen: ZyklusErgebnis | None, cfg: BelastungConfig = BelastungConfig()) -> BelastungErgebnis:
    r = from_result(result)
    if prep is None:
        k = Kennzahl.fehlt("Keine Pose-Daten")
        drehung, pro_zyklus = k, k
    else:
        drehung, pro_zyklus = analyse_twist(prep, zyklen, cfg)
    return BelastungErgebnis(
        reba_mittel=r["reba_mittel"], reba_max=r["reba_max"], buecken_anteil=r["buecken_anteil"],
        ueberkopf_anteil=r["ueberkopf_anteil"], drehung_anteil=drehung, drehungen_pro_zyklus=pro_zyklus,
    )
