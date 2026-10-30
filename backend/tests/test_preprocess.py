"""Normalisation, gaps and smoothing (S1, STECKBRIEF_MODUL §3.2)."""
import math

import numpy as np
import pytest

from backend.app.services.workplace.pose_store import KEPT_INDICES, KEPT_NAMES, PoseData
from backend.app.services.workplace.preprocess import PreprocessConfig, prepare
from backend.tests.pose_fixtures import body


def make_pose(frames, w=960, h=640, rate=15.0):
    lm = np.full((len(frames), len(KEPT_INDICES), 4), np.nan, dtype=np.float32)
    for f, pts in enumerate(frames):
        if pts:
            for k, i in enumerate(KEPT_INDICES):
                p = pts[i]
                lm[f, k] = (p.x, p.y, p.z, p.visibility)
    return PoseData(
        t=np.arange(len(frames)) / rate, landmarks=lm, indices=KEPT_INDICES, names=KEPT_NAMES,
        fps=rate, step=1, width=w, height=h,
    )


def test_origin_hip_scale_trunk_and_aspect_ratio():
    # upright person on a 3:2 video: the trunk must point straight up in body coordinates
    p = prepare(make_pose([body(960, 640, trunk_deg=0, dx_px=i) for i in range(30)]))
    hip_mid = (p.joint("left_hip") + p.joint("right_hip")) / 2
    sh_mid = (p.joint("left_shoulder") + p.joint("right_shoulder")) / 2
    assert np.allclose(hip_mid[:, :2], 0, atol=1e-6)
    assert np.allclose(sh_mid[:, :2], [0, -1], atol=1e-6)
    assert p.trunk_px == pytest.approx(640 * 0.25)
    # walking stays visible in the hip trajectory (1 px per frame)
    assert p.hip[-1, 0] - p.hip[0, 0] == pytest.approx(29 / 160, rel=1e-3)


def test_trunk_angle_correct_on_wide_video():
    p = prepare(make_pose([body(1920, 1080, trunk_deg=40)] * 10, w=1920, h=1080))
    sh = (p.joint("left_shoulder") + p.joint("right_shoulder")) / 2
    angle = math.degrees(math.atan2(abs(sh[0, 0]), abs(sh[0, 1])))
    assert angle == pytest.approx(40, abs=0.01)


def test_short_gap_interpolated_long_gap_marked():
    frames = [body(960, 640, dx_px=i) for i in range(60)]
    for i in range(10, 16):  # 6 frames = 0.4 s: filled
        frames[i] = []
    for i in range(30, 45):  # 15 frames = 1.0 s: stays missing
        frames[i] = []
    p = prepare(make_pose(frames), PreprocessConfig(window_s=0.0))
    assert p.valid[10:16].all()
    assert p.hip[12, 0] == pytest.approx((480 + 12) / 160, rel=1e-3)  # linear in between
    assert not p.valid[30:45].any() and p.long_gap[30:45].all()
    assert not p.long_gap[10:16].any()


def test_smoothing_reduces_noise_keeps_movement():
    rng = np.random.default_rng(1)
    rate, n = 15.0, 300
    t = np.arange(n) / rate
    frames = [body(960, 640, dx_px=60 * math.sin(2 * math.pi * ti / 4)) for ti in t]
    pose = make_pose(frames, rate=rate)
    pose.landmarks[..., :2] += rng.normal(0, 0.004, pose.landmarks[..., :2].shape).astype(np.float32)
    p = prepare(pose)
    ref = prepare(make_pose(frames, rate=rate), PreprocessConfig(window_s=0.0))
    noisy = prepare(pose, PreprocessConfig(window_s=0.0))
    err_smooth = np.nanstd(p.hip[:, 0] - ref.hip[:, 0])
    err_raw = np.nanstd(noisy.hip[:, 0] - ref.hip[:, 0])
    # short default window (0.33 s, keeps quick hand movements): about a third less noise
    assert err_smooth < 0.8 * err_raw
    wide = prepare(pose, PreprocessConfig(window_s=1.0))
    assert np.nanstd(wide.hip[:, 0] - ref.hip[:, 0]) < 0.5 * err_raw
    # amplitude of the 4 s movement kept within 5 % (projection onto the sine, robust to residual noise)
    basis = np.sin(2 * np.pi * t / 4)
    amp = lambda x: 2 * np.mean((x - x.mean()) * basis)  # noqa: E731
    assert amp(p.hip[:, 0]) == pytest.approx(amp(ref.hip[:, 0]), rel=0.05)
