"""Synthetic work cycle with known phases for the process step tests."""
from __future__ import annotations

import numpy as np

from backend.tests.prepared import prepared_from_wrists

RATE = 15.0
# phase boundaries of one cycle: walk there, rest, reach out, bring back, join (rest), walk back
PHASES = [("gehen", 0.0, 0.15), ("ruhe", 0.15, 0.3), ("hin", 0.3, 0.45), ("zurueck", 0.45, 0.6), ("fuegen", 0.6, 0.85), ("gehen", 0.85, 1.0)]


def _smoothstep(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def cycle_signals(period=10.0, n_cycles=8, noise=0.01, seed=0):
    """Hip and left wrist trajectories over n_cycles; returns t, hip [F,2], wrist [F,2]."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(period * n_cycles * RATE)) / RATE
    ph = (t % period) / period
    hip_x = np.zeros_like(t)
    wx = np.full_like(t, 0.4)
    wy = np.full_like(t, -0.4)
    for name, a, b in PHASES:
        m = (ph >= a) & (ph < b)
        u = (ph[m] - a) / (b - a)
        if name == "gehen":
            # 1.2 trunk lengths in 1.5 s and back: walking pace
            hip_x[m] = 1.2 * _smoothstep(u) if a == 0.0 else 1.2 * (1 - _smoothstep(u))
        elif name in ("ruhe", "fuegen"):
            hip_x[m] = 1.2 if a < 0.85 else 0.0
        elif name == "hin":
            hip_x[m] = 1.2
            wx[m] = 0.4 + 0.9 * _smoothstep(u)
        elif name == "zurueck":
            hip_x[m] = 1.2
            wx[m] = 1.3 - 0.9 * _smoothstep(u)
    hip = np.column_stack([hip_x, np.zeros_like(t)]) + rng.normal(0, noise, (len(t), 2))
    wrist = np.column_stack([wx, wy]) + rng.normal(0, noise, (len(t), 2))
    return t, hip, wrist


def prepared_work(period=10.0, n_cycles=8, noise=0.01, seed=0):
    t, hip, wrist = cycle_signals(period, n_cycles, noise, seed)
    prep = prepared_from_wrists(t, (wrist[:, 0], wrist[:, 1]), (0.3 + 0 * t, 0.2 + 0 * t))
    object.__setattr__(prep, "hip", hip)
    return prep
