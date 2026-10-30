"""Reach and working heights (STECKBRIEF_MODUL §4.2).

Wrist positions relative to the hip centre, in trunk lengths (from
preprocess.prepare). Image y points downwards: negative y is above the hip.

- Height zones with time shares, per frame and hand, with the body's own
  landmarks as borders: below knee, knee to hip, hip to shoulder, above
  shoulder. Hidden knees (e.g. behind a bench): typical proportion, knee
  0.9 trunk lengths below the hip. A hand that is mostly hidden (far side in
  a side view) is left out.
- Grips: the hand comes to rest (low speed for a short time) after it has
  moved. A grip lies outside the favourable reach when it is not between
  hip and shoulder or not close to the body (horizontal distance from the
  shoulder centre above koerpernah_max trunk lengths). Thresholds in
  ReachConfig.
- Density of the hand positions over the body silhouette, for the reach
  graphic.

Relative values from 2D video: a reach towards the camera looks shorter.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .preprocess import Prepared
from .quality import Kennzahl

HINWEIS_2D = "Relative Werte aus 2D-Video. Für Zentimeterangaben ist eine Referenzmessung vor Ort nötig."
ZONEN = ("unter_knie", "knie_huefte", "huefte_schulter", "ueber_schulter")
ZONEN_TEXT = {"unter_knie": "unter Knie", "knie_huefte": "Knie bis Hüfte", "huefte_schulter": "Hüfte bis Schulter", "ueber_schulter": "über Schulter"}


@dataclass(frozen=True)
class ReachConfig:
    koerpernah_max: float = 0.7  # trunk lengths from the shoulder centre (horizontal)
    rest_speed: float = 0.4  # trunk lengths per second: the hand is at rest
    move_speed: float = 1.0  # before a grip the hand moved at least this fast
    min_rest_s: float = 0.2
    move_window_s: float = 1.0
    min_coverage: float = 0.6  # share of person frames in which a hand is visible
    knee_fallback: float = 0.9  # knee below the hip in trunk lengths, if the knees are hidden
    min_grips: int = 10
    reliable: float = 0.5
    # density grid in trunk lengths: x left/right of the hip, y from above the head to the feet
    grid_x: tuple[float, float, int] = (-2.0, 2.0, 20)
    grid_y: tuple[float, float, int] = (-2.5, 2.5, 25)


@dataclass(frozen=True)
class Griff:
    t_s: float
    hand: str  # "links" or "rechts"
    x: float  # body coordinates, trunk lengths
    y: float
    zone: str
    abstand: float  # horizontal distance from the shoulder centre
    ausserhalb: bool


@dataclass(frozen=True)
class GreifraumErgebnis:
    hoehenzonen: dict[str, Kennzahl]  # time share per zone (visible hands)
    griffe_ausserhalb: Kennzahl  # share of grips outside the favourable reach
    anzahl_griffe: int
    griffe: list[Griff]
    abdeckung: float
    hinweis: str = HINWEIS_2D
    dichte: np.ndarray = field(repr=False, default_factory=lambda: np.empty((0, 0)))  # [ny, nx], max 1
    dichte_x: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))  # bin edges
    dichte_y: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))


def _zone(y: np.ndarray, shoulder_y: np.ndarray, knee_y: np.ndarray) -> np.ndarray:
    """Zone index per value (0 below knee ... 3 above shoulder); -1 if unknown."""
    z = np.full(y.shape, -1)
    ok = ~np.isnan(y) & ~np.isnan(shoulder_y) & ~np.isnan(knee_y)
    z[ok & (y >= knee_y)] = 0
    z[ok & (y < knee_y) & (y >= 0)] = 1
    z[ok & (y < 0) & (y >= shoulder_y)] = 2
    z[ok & (y < shoulder_y)] = 3
    return z


def _runs(flag: np.ndarray) -> list[tuple[int, int]]:
    """Start and end (exclusive) of each run of True values."""
    d = np.diff(np.concatenate([[0], flag.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def _knee(prep: Prepared, cfg: ReachConfig) -> np.ndarray:
    """Knee height per frame: mean of the visible knees, else the typical proportion."""
    k = np.column_stack([prep.joint("left_knee")[:, 1], prep.joint("right_knee")[:, 1]])
    out = np.full(len(k), cfg.knee_fallback)
    seen = ~np.isnan(k)
    any_seen = seen.any(axis=1)
    out[any_seen] = np.nanmean(k[any_seen], axis=1)
    return out


def analyse_reach(prep: Prepared, cfg: ReachConfig = ReachConfig()) -> GreifraumErgebnis:
    rate = prep.rate_hz
    sh = (prep.joint("left_shoulder")[:, :2] + prep.joint("right_shoulder")[:, :2]) / 2
    knee_y = _knee(prep, cfg)
    hands = {"links": prep.joint("left_wrist")[:, :2], "rechts": prep.joint("right_wrist")[:, :2]}

    # hands that are visible in enough person frames
    seen = {h: prep.valid & ~np.isnan(w).any(axis=1) for h, w in hands.items()}
    n_valid = max(1, int(prep.valid.sum()))
    share = {h: float(s.sum()) / n_valid for h, s in seen.items()}
    hands = {h: w for h, w in hands.items() if share[h] >= cfg.min_coverage}
    # quality: share of frames with a person times the visibility of the used hands
    person = float(prep.valid.mean()) if prep.valid.size else 0.0
    coverage = person * float(np.mean([share[h] for h in hands])) if hands else 0.0

    # height zones: share of frames, visible hands counted
    counts = np.zeros(4)
    for h, w in hands.items():
        s = seen[h]
        z = _zone(w[s, 1], sh[s, 1], knee_y[s])
        counts += np.bincount(z[z >= 0], minlength=4)[:4]
    total = counts.sum()
    zone_q = coverage if total > 0 else 0.0
    hoehenzonen = {
        name: Kennzahl.bewertet(counts[i] / total if total else None, zone_q, cfg.reliable)
        for i, name in enumerate(ZONEN)
    }

    # grips: rest after movement, position relative to the body
    griffe: list[Griff] = []
    min_rest = max(1, int(round(cfg.min_rest_s * rate)))
    look_back = max(1, int(round(cfg.move_window_s * rate)))
    for hand, w in hands.items():
        world = w + prep.hip  # hand in the image frame (trunk lengths): rest = hand stands still
        speed = np.full(len(w), np.nan)
        speed[1:] = np.linalg.norm(np.diff(world, axis=0), axis=1) * rate
        rest = (speed < cfg.rest_speed) & seen[hand]
        for a, b in _runs(rest):
            if b - a < min_rest:
                continue
            before = speed[max(0, a - look_back) : a]
            if before.size == 0 or np.nanmax(np.nan_to_num(before, nan=0.0)) < cfg.move_speed:
                continue  # hand did not come from a movement (idle)
            i = a + int(np.nanargmin(speed[a:b]))
            x, y = float(w[i, 0]), float(w[i, 1])
            zone = int(_zone(np.array([y]), np.array([sh[i, 1]]), np.array([knee_y[i]]))[0])
            abstand = abs(x - float(sh[i, 0]))
            ausserhalb = zone != 2 or abstand > cfg.koerpernah_max
            griffe.append(Griff(float(prep.t[i]), hand, x, y, ZONEN[zone] if zone >= 0 else "unbekannt", abstand, ausserhalb))
    griffe.sort(key=lambda g: g.t_s)

    if len(griffe) >= cfg.min_grips:
        share = sum(g.ausserhalb for g in griffe) / len(griffe)
        ausserhalb = Kennzahl.bewertet(share, coverage, cfg.reliable)
    else:
        ausserhalb = Kennzahl.fehlt(f"Zu wenige Griffe erkannt ({len(griffe)}, mindestens {cfg.min_grips})")

    # density over the silhouette
    gx = np.linspace(*cfg.grid_x[:2], cfg.grid_x[2] + 1)
    gy = np.linspace(*cfg.grid_y[:2], cfg.grid_y[2] + 1)
    pts = np.vstack([w[seen[h]] for h, w in hands.items()]) if hands else np.empty((0, 2))
    hist, _, _ = np.histogram2d(pts[:, 1], pts[:, 0], bins=[gy, gx]) if len(pts) else (np.zeros((len(gy) - 1, len(gx) - 1)), None, None)
    dichte = hist / hist.max() if hist.max() > 0 else hist

    return GreifraumErgebnis(
        hoehenzonen=hoehenzonen,
        griffe_ausserhalb=ausserhalb,
        anzahl_griffe=len(griffe),
        griffe=griffe,
        abdeckung=coverage,
        dichte=dichte,
        dichte_x=gx,
        dichte_y=gy,
    )
