"""Build Prepared pose data directly from wrist trajectories (body coordinates)."""
from __future__ import annotations

import numpy as np

from backend.app.services.workplace.pose_store import KEPT_NAMES
from backend.app.services.workplace.preprocess import Prepared


def prepared_from_wrists(t, left, right, rate=15.0, noise=0.0, seed=0, valid=None) -> Prepared:
    """Upright body (hip at 0, shoulders at y = -1, knees at y = 0.9); wrists given as (x, y) arrays."""
    rng = np.random.default_rng(seed)
    f = len(t)
    rel = np.zeros((f, len(KEPT_NAMES), 3))

    def put(name, x, y):
        k = KEPT_NAMES.index(name)
        rel[:, k, 0] = x
        rel[:, k, 1] = y

    put("left_shoulder", -0.35, -1.0); put("right_shoulder", 0.35, -1.0)
    put("left_hip", -0.15, 0.0); put("right_hip", 0.15, 0.0)
    put("left_knee", -0.15, 0.9); put("right_knee", 0.15, 0.9)
    put("left_wrist", np.asarray(left[0]), np.asarray(left[1]))
    put("right_wrist", np.asarray(right[0]), np.asarray(right[1]))
    if noise:
        rel[..., :2] += rng.normal(0, noise, rel[..., :2].shape)
    v = np.ones(f, dtype=bool) if valid is None else np.asarray(valid)
    rel[~v] = np.nan
    return Prepared(
        t=np.asarray(t, dtype=float), rel=rel, hip=np.zeros((f, 2)), valid=v, long_gap=~v,
        trunk_px=150.0, rate_hz=rate, names=KEPT_NAMES,
    )
