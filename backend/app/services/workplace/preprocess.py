"""Normalisation and smoothing of the pose data (STECKBRIEF_MODUL §3.2).

1. Pixels: x and y times width and height, so angles are correct on any
   aspect ratio (z uses the width, like MediaPipe's x).
2. Gaps (no person or landmark not visible) up to max_gap_s are filled by
   linear interpolation; longer gaps stay NaN and are marked.
3. Savitzky-Golay smoothing on each continuous stretch.
4. Origin at the hip centre of each frame, scale = trunk length (hip centre
   to shoulder centre). The scale is the median over the video, not per
   frame: when the person bends or turns, the projected trunk gets shorter
   and a per-frame scale would distort the hands.

The hip centre trajectory is kept separately (in trunk lengths), because
walking shows up there and the body-relative coordinates remove it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import savgol_filter

from .pose_store import PoseData


@dataclass(frozen=True)
class PreprocessConfig:
    window_s: float = 0.33  # smoothing window
    polyorder: int = 2
    max_gap_s: float = 0.5  # longer gaps are not interpolated
    min_visibility: float = 0.5  # below this a landmark counts as missing


@dataclass(frozen=True)
class Prepared:
    t: np.ndarray  # [F] seconds
    rel: np.ndarray  # [F, L, 3] body-relative, in trunk lengths, y downwards
    hip: np.ndarray  # [F, 2] hip centre in trunk lengths (image frame)
    valid: np.ndarray  # [F] bool: person present (measured or interpolated)
    long_gap: np.ndarray  # [F] bool: inside a gap longer than max_gap_s
    trunk_px: float  # trunk length in pixels (median)
    rate_hz: float
    names: tuple[str, ...]

    def joint(self, name: str) -> np.ndarray:
        return self.rel[:, self.names.index(name)]


def _interpolate_gaps(values: np.ndarray, missing: np.ndarray, max_gap: int) -> tuple[np.ndarray, np.ndarray]:
    """Linear interpolation over runs of missing frames up to max_gap long.

    values [F, ...]; missing [F] bool. Returns filled values and a mask of
    frames that stay missing (gaps longer than max_gap and gaps at the ends).
    """
    out = values.copy()
    still = missing.copy()
    f = len(missing)
    i = 0
    while i < f:
        if not missing[i]:
            i += 1
            continue
        j = i
        while j < f and missing[j]:
            j += 1
        # run i..j-1 is missing
        if i > 0 and j < f and (j - i) <= max_gap:
            a, b = out[i - 1], out[j]
            for k in range(i, j):
                w = (k - i + 1) / (j - i + 1)
                out[k] = a + (b - a) * w
            still[i:j] = False
        i = j
    return out, still


def _smooth(values: np.ndarray, missing: np.ndarray, window: int, polyorder: int) -> np.ndarray:
    """Savitzky-Golay on each continuous stretch that is long enough."""
    out = values.copy()
    f = len(missing)
    i = 0
    while i < f:
        if missing[i]:
            i += 1
            continue
        j = i
        while j < f and not missing[j]:
            j += 1
        n = j - i
        w = min(window, n if n % 2 else n - 1)
        if w > polyorder + 1:
            out[i:j] = savgol_filter(values[i:j], w, polyorder, axis=0)
        i = j
    return out


def prepare(pose: PoseData, cfg: PreprocessConfig = PreprocessConfig()) -> Prepared:
    lm = pose.landmarks
    f, n_lm, _ = lm.shape
    rate = pose.rate_hz

    # 1. pixels
    xyz = np.stack([lm[..., 0] * pose.width, lm[..., 1] * pose.height, lm[..., 2] * pose.width], axis=-1)
    visible = np.nan_to_num(lm[..., 3], nan=0.0) >= cfg.min_visibility
    xyz[~visible] = np.nan

    # 2. gaps per landmark
    max_gap = max(0, int(round(cfg.max_gap_s * rate)))
    for k in range(n_lm):
        miss = np.isnan(xyz[:, k, 0])
        xyz[:, k], _ = _interpolate_gaps(xyz[:, k], miss, max_gap)

    names = pose.names
    hips = [names.index("left_hip"), names.index("right_hip")]
    shoulders = [names.index("left_shoulder"), names.index("right_shoulder")]
    hip_px = xyz[:, hips, :2].mean(axis=1)
    sh_px = xyz[:, shoulders, :2].mean(axis=1)
    # A frame counts as valid when hips and shoulders are known
    valid = ~(np.isnan(hip_px).any(axis=1) | np.isnan(sh_px).any(axis=1))
    person_missing = np.all(np.isnan(lm[..., 0]), axis=1)
    _, long_gap = _interpolate_gaps(np.zeros((f, 1)), person_missing, max_gap)

    # 3. smoothing
    window = max(3, int(round(cfg.window_s * rate)) | 1)
    for k in range(n_lm):
        miss = np.isnan(xyz[:, k, 0])
        xyz[:, k] = _smooth(xyz[:, k], miss, window, cfg.polyorder)
    hip_px = xyz[:, hips, :2].mean(axis=1)
    sh_px = xyz[:, shoulders, :2].mean(axis=1)

    # 4. origin and scale
    trunk = np.linalg.norm(sh_px - hip_px, axis=1)
    trunk_px = float(np.nanmedian(trunk[valid])) if valid.any() else float("nan")
    origin = np.concatenate([hip_px, np.zeros((f, 1))], axis=1)
    rel = (xyz - origin[:, None, :]) / trunk_px
    hip = hip_px / trunk_px

    return Prepared(
        t=pose.t,
        rel=rel,
        hip=hip,
        valid=valid,
        long_gap=long_gap,
        trunk_px=trunk_px,
        rate_hz=rate,
        names=names,
    )
