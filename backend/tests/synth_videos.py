"""Synthetic "videos" with known cycles and process steps for the validation
script (S6): pose.npz in the pipeline format, the true time stamps, and an
expert review as the expert view would save it.

A work cycle: walk there, wait, grip, bring, join, walk back. The waiting time
varies from cycle to cycle (that is where cycle time variation comes from),
so the proportional transfer of the review cannot match every cycle exactly,
like in reality.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np

from backend.app.services.workplace.pose_store import FORMAT_VERSION, KEPT_INDICES, KEPT_NAMES

RATE = 15.0
W, H = 1280, 720
TRUNK = 150.0  # px

# fixed step durations as share of the base period; "Warten" is added per cycle
SCHRITTE = [("Gehen", 0.15), ("Warten", None), ("Greifen", 0.15), ("Bringen", 0.15), ("Fügen", 0.25), ("Gehen", 0.15)]
WARTEN_ANTEIL = 0.15


@dataclass
class SynthVideo:
    name: str
    npz: bytes
    zyklen: list[tuple[float, float]]  # true cycles
    segmente: list[tuple[float, float, str]]  # true process steps
    review: dict | None  # expert review (median proportions)
    dauer_s: float


def _smooth(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def _koerper(hip_x: np.ndarray, wrist: np.ndarray, rng, noise_px: float) -> np.ndarray:
    """Landmarks [F, 25, 4] (normalised x, y, z, visibility) for an upright person."""
    f = len(hip_x)
    cx = W / 2 + hip_x * TRUNK
    cy = np.full(f, H * 0.62)
    pos = {
        "left_hip": (-0.15, 0.0), "right_hip": (0.15, 0.0),
        "left_shoulder": (-0.35, -1.0), "right_shoulder": (0.35, -1.0),
        "left_knee": (-0.15, 0.9), "right_knee": (0.15, 0.9),
        "left_ankle": (-0.15, 1.7), "right_ankle": (0.15, 1.7),
        "left_heel": (-0.18, 1.75), "right_heel": (0.18, 1.75),
        "left_foot_index": (-0.1, 1.8), "right_foot_index": (0.1, 1.8),
        "nose": (0.0, -1.35), "left_ear": (-0.1, -1.4), "right_ear": (0.1, -1.4),
        "right_elbow": (0.4, -0.5), "right_wrist": (0.3, 0.1),
    }
    lm = np.zeros((f, len(KEPT_NAMES), 4))
    for k, name in enumerate(KEPT_NAMES):
        if name in pos:
            x = cx + pos[name][0] * TRUNK
            y = cy + pos[name][1] * TRUNK
        elif name.startswith("left_") and name in ("left_wrist", "left_pinky", "left_index", "left_thumb"):
            x = cx + wrist[:, 0] * TRUNK
            y = cy + wrist[:, 1] * TRUNK
        elif name == "left_elbow":
            x = cx + (-0.35 + wrist[:, 0]) / 2 * TRUNK
            y = cy + (-1.0 + wrist[:, 1]) / 2 * TRUNK
        else:  # right hand details
            x = cx + 0.3 * TRUNK
            y = cy + 0.12 * TRUNK
        lm[:, k, 0] = (x + rng.normal(0, noise_px, f)) / W
        lm[:, k, 1] = (y + rng.normal(0, noise_px, f)) / H
        lm[:, k, 3] = 0.98
    return lm


def _npz(t: np.ndarray, lm: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.savez_compressed(
        buf, version=np.int16(FORMAT_VERSION), t=t.astype(np.float32), landmarks=lm.astype(np.float16),
        indices=np.asarray(KEPT_INDICES, dtype=np.int16), names=np.asarray(KEPT_NAMES), fps=np.float32(30.0),
        step=np.int16(2), width=np.int32(W), height=np.int32(H),
    )
    return buf.getvalue()


def arbeitszyklen(name: str, periode: float, n: int, warten_vk: float = 0.3, pause_nach: int | None = None,
                  pause_s: float = 0.0, vorlauf_s: float = 4.0, noise_px: float = 1.5, seed: int = 0) -> SynthVideo:
    """n cycles of about periode seconds; optionally a pause (standing, hands still) after cycle pause_nach."""
    rng = np.random.default_rng(seed)
    basis = periode * (1 - WARTEN_ANTEIL)
    t_ende = vorlauf_s
    zyklen, segmente, plan = [], [], []
    for i in range(n):
        warten = max(0.2, periode * WARTEN_ANTEIL * (1 + warten_vk * rng.standard_normal()))
        start = t_ende
        s = start
        for typ, anteil in SCHRITTE:
            d = warten if anteil is None else basis * anteil / (1 - WARTEN_ANTEIL)
            segmente.append((s, s + d, typ))
            plan.append((s, s + d, typ))
            s += d
        zyklen.append((start, s))
        t_ende = s
        if pause_nach is not None and i == pause_nach - 1:
            t_ende += pause_s
    dauer = t_ende + vorlauf_s
    t = np.arange(int(dauer * RATE)) / RATE
    hip_x = np.zeros_like(t)
    wrist = np.tile([0.4, -0.4], (len(t), 1)).astype(float)
    gehen = 0
    for s, e, typ in plan:
        m = (t >= s) & (t < e)
        u = (t[m] - s) / (e - s)
        if typ == "Gehen":
            hip_x[m] = 1.2 * _smooth(u) if gehen % 2 == 0 else 1.2 * (1 - _smooth(u))
            gehen += 1
        else:
            hip_x[m] = 1.2
            if typ == "Greifen":
                wrist[m, 0] = 0.4 + 0.9 * _smooth(u)
            elif typ == "Bringen":
                wrist[m, 0] = 1.3 - 0.9 * _smooth(u)
            elif typ == "Fügen":
                wrist[m, 1] = -0.4 + 0.05 * np.sin(2 * np.pi * 3 * u)
    lm = _koerper(hip_x, wrist, rng, noise_px)
    # the review: the expert confirms the steps in the median cycle (mean proportions)
    dauern = np.array([[e - s for s, e, _ in segmente[k * len(SCHRITTE):(k + 1) * len(SCHRITTE)]] for k in range(n)])
    anteile = (dauern / dauern.sum(axis=1, keepdims=True)).mean(axis=0)
    grenzen = np.concatenate([[0.0], np.cumsum(anteile)])
    grenzen[-1] = 1.0
    review = {"segmente": [{"start_phase": float(grenzen[k]), "ende_phase": float(grenzen[k + 1]), "typ": typ, "klasse": None}
                           for k, (typ, _) in enumerate(SCHRITTE)]}
    return SynthVideo(name, _npz(t, lm), zyklen, segmente, review, dauer)


def ohne_zyklus(name: str, dauer: float = 180.0, seed: int = 0) -> SynthVideo:
    """Aperiodic work: random reaches at random times, no recurring cycle."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dauer * RATE)) / RATE
    wrist = np.tile([0.4, -0.4], (len(t), 1)).astype(float)
    s = 2.0
    while s < dauer - 5:
        d = rng.uniform(1.0, 6.0)
        m = (t >= s) & (t < s + d)
        u = (t[m] - s) / d
        ziel = rng.uniform(-0.6, 1.0, 2)
        wrist[m] = np.array([0.4, -0.4]) + np.outer(np.sin(np.pi * u), ziel - [0.4, -0.4])
        s += d + rng.uniform(0.5, 12.0)
    lm = _koerper(np.zeros_like(t), wrist, rng, 1.5)
    return SynthVideo(name, _npz(t, lm), [], [], None, dauer)


def von_hand(v: SynthVideo, versatz_s: float = 0.3, seed: int = 1) -> list[tuple[str, float, float, str]]:
    """CSV rows as a person would record them: the true times with a timing error."""
    rng = np.random.default_rng(seed)
    j = lambda x: round(max(0.0, x + rng.normal(0, versatz_s)), 2)  # noqa: E731
    if not v.zyklen:
        return [(v.name, 0.0, round(v.dauer_s, 1), "kein Zyklus")]
    rows = []
    for s, e in v.zyklen:
        a, b = j(s), j(e)
        rows.append((v.name, a, max(b, a + 0.1), "Zyklus"))
    for s, e, typ in v.segmente:
        a, b = j(s), j(e)
        rows.append((v.name, a, max(b, a + 0.1), typ))
    return rows


def szenarien() -> list[SynthVideo]:
    return [
        arbeitszyklen("takt_12s.mp4", 12.0, 15, warten_vk=0.2, seed=1),
        arbeitszyklen("montage_25s_mit_pause.mp4", 25.0, 9, warten_vk=0.4, pause_nach=4, pause_s=45.0, seed=2),
        arbeitszyklen("kommissionieren_60s.mp4", 60.0, 5, warten_vk=0.6, noise_px=2.5, seed=3),
        ohne_zyklus("nacharbeit_ohne_zyklus.mp4", seed=4),
    ]


def schreibe(ordner) -> None:
    """Writes the scenarios as DIR/<stem>.npz, DIR/<stem>.review.json and DIR/manuell.csv."""
    import csv
    import json
    from pathlib import Path

    d = Path(ordner)
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for v in szenarien():
        stem = Path(v.name).stem
        (d / f"{stem}.npz").write_bytes(v.npz)
        if v.review:
            (d / f"{stem}.review.json").write_text(json.dumps(v.review), encoding="utf-8")
        rows += von_hand(v)
    with open(d / "manuell.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video", "start_s", "ende_s", "typ"])
        w.writerows(rows)


if __name__ == "__main__":
    # python -m backend.tests.synth_videos DIR
    import sys

    schreibe(sys.argv[1])
