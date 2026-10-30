"""Process steps, semi-automatic (STECKBRIEF_MODUL §4.3).

1. Speed of the wrists and movement of the hip (for walking), in trunk
   lengths per second, in the image frame (a hand at rest on a part does not
   move in the image, even if the body sways a little).
2. Median cycle: every valid cycle is resampled to the same phase grid
   (0 to 1); per phase the median over all cycles.
3. In the median cycle the phases are separated: movement, rest, change of
   place (walking) and change of direction. Segments shorter than
   min_segment_s are merged into a neighbour.
4. The expert assigns a type to every segment and confirms or changes its
   class (value-adding, necessary, waste); see STEP_TYPES.
5. The assignment is transferred to all valid cycles in proportion to their
   duration (same phase share, scaled to the cycle's own length).

The tool proposes, the expert decides: only "Gehen" is proposed as a type
(clearly measurable from the hip), all other types come from the expert.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import scoring_config
from .cycles import ZyklusErgebnis
from .preprocess import Prepared

# Type -> default class (STECKBRIEF_MODUL §4.3), from config/workplace_scoring.json;
# the expert may change the class
STEP_TYPES: dict[str, str] = dict(scoring_config.get().schritt_typen)
KLASSEN = scoring_config.KLASSEN
ARTEN = ("bewegung", "ruhe", "ortswechsel")


@dataclass(frozen=True)
class SegmentConfig:
    grid: int = 200  # samples of the median cycle
    rest_speed: float = 0.4  # trunk lengths per second: hands at rest
    walk_speed: float = 0.5  # hip speed (trunk lengths per second): change of place
    min_walk_s: float = 0.4
    direction_change_deg: float = 100.0  # split a movement where the hand turns back
    min_segment_s: float = 0.4


@dataclass(frozen=True)
class MedianZyklus:
    phase: np.ndarray  # [G] 0..1
    dauer_s: float  # median cycle duration
    hand_speed: np.ndarray  # [G] trunk lengths per second
    hip_speed: np.ndarray  # [G]
    hand_vel: np.ndarray  # [G, 2] median velocity of the faster hand
    anzahl_zyklen: int


@dataclass(frozen=True)
class Segment:
    start_phase: float
    ende_phase: float
    art: str  # bewegung, ruhe, ortswechsel
    vorschlag_typ: str | None = None
    hand_speed: float = 0.0
    hip_speed: float = 0.0

    def dauer(self, zyklus_s: float) -> float:
        return (self.ende_phase - self.start_phase) * zyklus_s


@dataclass(frozen=True)
class BewerteterSchritt:
    start_phase: float
    ende_phase: float
    typ: str
    klasse: str


@dataclass(frozen=True)
class AblaufErgebnis:
    """Result after the expert review, transferred to all valid cycles."""

    ablaufschritte: list[dict]  # typ, klasse, anteil, dauer_s (median cycle)
    anteile_ablauf: dict[str, float]  # share per class of the cycle time
    je_zyklus: list[dict]  # start_s, dauer_s and seconds per class
    sekunden_je_zyklus: dict[str, float]  # mean per class
    minuten_pro_schicht: dict[str, float | None]
    anzahl_zyklen: int
    hinweis: str = "Ablaufschritte vom Experten bestätigt, auf alle gültigen Zyklen übertragen."
    extras: dict = field(default_factory=dict)


# ── signals ──────────────────────────────────────────────────────────────────


def _velocity(x: np.ndarray, rate: float, window_s: float = 0.3) -> np.ndarray:
    """Velocity per frame from positions [F, 2], smoothed over about window_s,
    so that position noise does not look like movement."""
    w = max(1, int(round(window_s * rate)) | 1)
    k = np.ones(w) / w
    sm = np.column_stack([np.convolve(np.nan_to_num(x[:, c], nan=np.nanmean(x[:, c]) if np.isfinite(x[:, c]).any() else 0.0), k, mode="same") for c in range(2)])
    sm[np.isnan(x).any(axis=1)] = np.nan
    v = np.gradient(sm, axis=0) * rate
    # the edges of the convolution are biased
    v[: w // 2] = np.nan
    v[len(v) - w // 2 :] = np.nan
    return v


def _speeds(prep: Prepared) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hand speed (faster visible hand), its velocity and hip speed per frame."""
    rate = prep.rate_hz
    hip = prep.hip
    hip_v = np.linalg.norm(_velocity(hip, rate), axis=1)
    speeds, vels = [], []
    for name in ("left_wrist", "right_wrist"):
        v = _velocity(prep.joint(name)[:, :2] + hip, rate)
        speeds.append(np.linalg.norm(v, axis=1))
        vels.append(v)
    s = np.column_stack(speeds)
    with np.errstate(invalid="ignore"):
        idx = np.nanargmax(np.where(np.isnan(s), -1, s), axis=1)
    hand_s = np.nanmax(np.where(np.isnan(s), -np.inf, s), axis=1)
    hand_s[np.isinf(hand_s)] = np.nan
    hand_v = np.where(idx[:, None] == 0, vels[0], vels[1])
    return hand_s, hand_v, hip_v


def median_cycle(prep: Prepared, zyklen: ZyklusErgebnis, cfg: SegmentConfig = SegmentConfig()) -> MedianZyklus | None:
    """Resample every valid cycle to the phase grid and take the median."""
    gueltig = [z for z in zyklen.zyklen if z.gueltig and z.art == "zyklus"]
    if not zyklen.erkannt or not gueltig:
        return None
    hand_s, hand_v, hip_v = _speeds(prep)
    phase = (np.arange(cfg.grid) + 0.5) / cfg.grid
    rows_h, rows_hip, rows_v = [], [], []
    for z in gueltig:
        sel = (prep.t >= z.start_s) & (prep.t < z.ende_s)
        if sel.sum() < 4:
            continue
        p = (prep.t[sel] - z.start_s) / (z.ende_s - z.start_s)
        rows_h.append(np.interp(phase, p, np.nan_to_num(hand_s[sel], nan=0.0)))
        rows_hip.append(np.interp(phase, p, np.nan_to_num(hip_v[sel], nan=0.0)))
        rows_v.append(np.column_stack([np.interp(phase, p, np.nan_to_num(hand_v[sel, k], nan=0.0)) for k in (0, 1)]))
    if not rows_h:
        return None
    return MedianZyklus(
        phase=phase,
        dauer_s=float(np.median([z.dauer_s for z in gueltig])),
        hand_speed=np.median(rows_h, axis=0),
        hip_speed=np.median(rows_hip, axis=0),
        hand_vel=np.median(rows_v, axis=0),
        anzahl_zyklen=len(rows_h),
    )


# ── proposal ─────────────────────────────────────────────────────────────────


def _runs(labels: list[str]) -> list[tuple[int, int, str]]:
    out, start = [], 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            out.append((start, i, labels[start]))
            start = i
    return out


def _split_direction(a: int, b: int, m: MedianZyklus, cfg: SegmentConfig) -> list[int]:
    """Split points inside a movement where the hand turns back (local speed minimum)."""
    cuts = []
    v = m.hand_vel
    s = m.hand_speed
    for i in range(a + 2, b - 2):
        if not (s[i] <= s[i - 1] and s[i] <= s[i + 1]):
            continue
        before, after = v[max(a, i - 3)], v[min(b - 1, i + 3)]
        nb, na = np.linalg.norm(before), np.linalg.norm(after)
        if nb < 1e-6 or na < 1e-6:
            continue
        angle = np.degrees(np.arccos(np.clip(np.dot(before, after) / (nb * na), -1, 1)))
        if angle >= cfg.direction_change_deg:
            cuts.append(i)
    return cuts


def propose_segments(m: MedianZyklus, cfg: SegmentConfig = SegmentConfig()) -> list[Segment]:
    g = len(m.phase)
    walk = m.hip_speed >= cfg.walk_speed
    labels = ["ortswechsel" if walk[i] else ("ruhe" if m.hand_speed[i] < cfg.rest_speed else "bewegung") for i in range(g)]
    # walking only if it lasts long enough
    min_walk = max(1, int(round(cfg.min_walk_s / m.dauer_s * g)))
    for a, b, lab in _runs(labels):
        if lab == "ortswechsel" and b - a < min_walk:
            for i in range(a, b):
                labels[i] = "ruhe" if m.hand_speed[i] < cfg.rest_speed else "bewegung"

    bounds: list[tuple[int, int, str]] = []
    for a, b, lab in _runs(labels):
        if lab == "bewegung":
            pts = [a, *_split_direction(a, b, m, cfg), b]
            bounds += [(pts[k], pts[k + 1], lab) for k in range(len(pts) - 1)]
        else:
            bounds.append((a, b, lab))

    # merge segments shorter than min_segment_s into the longer neighbour
    min_len = max(1, int(round(cfg.min_segment_s / m.dauer_s * g)))
    changed = True
    while changed and len(bounds) > 1:
        changed = False
        for k, (a, b, lab) in enumerate(bounds):
            if b - a >= min_len:
                continue
            left = bounds[k - 1] if k > 0 else None
            right = bounds[k + 1] if k + 1 < len(bounds) else None
            target = k - 1 if right is None or (left is not None and (left[1] - left[0]) >= (right[1] - right[0])) else k + 1
            ta, tb, tlab = bounds[target]
            merged = (min(a, ta), max(b, tb), tlab)
            lo, hi = sorted((k, target))
            bounds[lo : hi + 1] = [merged]
            changed = True
            break

    # neighbours of the same kind become one (rest, walking); split movements stay apart
    joined: list[tuple[int, int, str]] = []
    for a, b, lab in bounds:
        if joined and joined[-1][2] == lab and lab != "bewegung":
            joined[-1] = (joined[-1][0], b, lab)
        else:
            joined.append((a, b, lab))
    out: list[Segment] = []
    for a, b, lab in joined:
        out.append(
            Segment(
                start_phase=a / g,
                ende_phase=b / g,
                art=lab,
                vorschlag_typ="Gehen" if lab == "ortswechsel" else None,
                hand_speed=float(np.mean(m.hand_speed[a:b])),
                hip_speed=float(np.mean(m.hip_speed[a:b])),
            )
        )
    return out


# ── review and transfer ──────────────────────────────────────────────────────


def validate_review(schritte: list[BewerteterSchritt]) -> list[str]:
    """Problems of a review (empty list = valid): contiguous from 0 to 1, known types and classes."""
    errors = []
    if not schritte:
        return ["Keine Segmente."]
    if abs(schritte[0].start_phase) > 1e-6:
        errors.append("Das erste Segment muss bei 0 beginnen.")
    if abs(schritte[-1].ende_phase - 1) > 1e-6:
        errors.append("Das letzte Segment muss bei 1 enden.")
    for i, s in enumerate(schritte):
        if s.ende_phase <= s.start_phase:
            errors.append(f"Segment {i + 1}: Ende muss nach dem Start liegen.")
        if s.typ not in STEP_TYPES:
            errors.append(f"Segment {i + 1}: unbekannter Typ {s.typ!r}.")
        if s.klasse not in KLASSEN:
            errors.append(f"Segment {i + 1}: unbekannte Einstufung {s.klasse!r}.")
        if i and abs(s.start_phase - schritte[i - 1].ende_phase) > 1e-6:
            errors.append(f"Segment {i + 1}: Lücke oder Überlappung zum vorigen Segment.")
    return errors


def transfer(schritte: list[BewerteterSchritt], zyklen: ZyklusErgebnis) -> AblaufErgebnis:
    """Apply the confirmed steps to every valid cycle (proportional to its duration)."""
    gueltig = [z for z in zyklen.zyklen if z.gueltig and z.art == "zyklus"]
    je_zyklus = []
    for z in gueltig:
        row = {"start_s": z.start_s, "dauer_s": z.dauer_s, **{k: 0.0 for k in KLASSEN}}
        for s in schritte:
            row[s.klasse] += (s.ende_phase - s.start_phase) * z.dauer_s
        je_zyklus.append(row)
    total = sum(r["dauer_s"] for r in je_zyklus)
    anteile = {k: (sum(r[k] for r in je_zyklus) / total if total else 0.0) for k in KLASSEN}
    mittel = {k: (float(np.mean([r[k] for r in je_zyklus])) if je_zyklus else 0.0) for k in KLASSEN}
    median_s = zyklen.zykluszeit_median.wert or (float(np.median([z.dauer_s for z in gueltig])) if gueltig else 0.0)

    # steps of the same type in a row are listed once (e.g. two "Greifen" segments)
    schritt_liste: list[dict] = []
    for s in schritte:
        anteil = s.ende_phase - s.start_phase
        if schritt_liste and schritt_liste[-1]["typ"] == s.typ and schritt_liste[-1]["klasse"] == s.klasse:
            schritt_liste[-1]["anteil"] += anteil
        else:
            schritt_liste.append({"typ": s.typ, "klasse": s.klasse, "anteil": anteil})
    for row in schritt_liste:
        row["anteil"] = round(row["anteil"], 4)
        row["dauer_s"] = round(row["anteil"] * median_s, 2)

    pro_schicht = zyklen.zyklen_pro_schicht.wert
    minuten = {k: (round(mittel[k] * pro_schicht / 60, 1) if pro_schicht else None) for k in KLASSEN}
    return AblaufErgebnis(
        ablaufschritte=schritt_liste,
        anteile_ablauf={k: round(v, 4) for k, v in anteile.items()},
        je_zyklus=je_zyklus,
        sekunden_je_zyklus={k: round(v, 2) for k, v in mittel.items()},
        minuten_pro_schicht=minuten,
        anzahl_zyklen=len(gueltig),
    )
