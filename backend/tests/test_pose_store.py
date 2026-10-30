"""PoseRecorder and pose.npz (S1)."""
import numpy as np
import pytest

from backend.app.services.workplace.pose_store import (
    DROPPED,
    KEPT_INDICES,
    KEPT_NAMES,
    MEDIAPIPE_NAMES,
    PoseRecorder,
    frame_step,
    load_npz,
)
from backend.tests.pose_fixtures import FakeResult, body


@pytest.mark.parametrize("fps,step,hz", [(10, 1, 10), (25, 2, 12.5), (30, 2, 15), (50, 4, 12.5), (60, 4, 15), (120, 8, 15)])
def test_rate_at_most_15_hz(fps, step, hz):
    assert frame_step(fps) == step
    assert fps / step == pytest.approx(hz)
    assert fps / step <= 15


def test_eyes_and_mouth_dropped_nose_and_ears_kept():
    assert len(KEPT_INDICES) == 25
    for i in range(1, 7):
        assert i not in KEPT_INDICES
    assert 9 not in KEPT_INDICES and 10 not in KEPT_INDICES
    for name in ("nose", "left_ear", "right_ear", "left_wrist", "right_hip"):
        assert name in KEPT_NAMES
    assert not any("eye" in n or "mouth" in n for n in KEPT_NAMES)
    assert DROPPED == frozenset({1, 2, 3, 4, 5, 6, 9, 10})
    assert KEPT_NAMES == tuple(MEDIAPIPE_NAMES[i] for i in KEPT_INDICES)


def test_roundtrip_float16_and_indices_in_file():
    w, h, fps = 640, 360, 30.0
    rec = PoseRecorder()
    rec.start(fps, w, h)
    for i in range(60):
        rec.add(i, FakeResult([] if 20 <= i < 26 else [body(w, h, trunk_deg=i)]))
    data = load_npz(rec.to_npz_bytes())
    assert len(rec) == 30 and data.landmarks.shape == (30, 25, 4)
    assert data.rate_hz == 15 and data.step == 2
    assert data.t[1] == pytest.approx(2 / 30)
    assert data.indices == KEPT_INDICES and data.names == KEPT_NAMES
    assert (data.width, data.height) == (w, h)
    # frames 20 to 25 without a person: NaN
    assert np.isnan(data.landmarks[10:13]).all() and not np.isnan(data.landmarks[13]).any()
    # stored as float16: precision about 1e-3 on 0..1 coordinates
    nose = body(w, h, trunk_deg=0)[0]
    assert data.landmarks[0, data.column("nose"), 0] == pytest.approx(nose.x, abs=1e-3)
    with np.load(__import__("io").BytesIO(rec.to_npz_bytes())) as f:
        assert f["landmarks"].dtype == np.float16
        assert f["t"].dtype == np.float32  # float16 would lose time precision after about 30 min
