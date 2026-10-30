"""Golden test (S1): result.json of the analysis pipeline must not change.

The reference was created at the fix commit 8b4de53 (movement rules, trunk
angle in pixels, duration from the video), before the pose recorder existed. The pipeline
runs on a synthetic video with a scripted landmarker, so the test needs no
model and no customer video.

Optional: MOTAVI_GOLDEN_VIDEO=/path/to/testvideo.mp4 additionally runs the
real MediaPipe model on the test video and compares with
golden/testvideo_result.json.
"""
import json
import os
from pathlib import Path

import numpy as np
import pytest

from backend.app.services import analyzer, gcs
from backend.app.services.workplace.pose_store import PoseRecorder, load_npz
from backend.tests import golden_run

GOLDEN = Path(__file__).parent / "golden"


def _reference(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text())


def test_result_unchanged_without_recorder():
    result, store = golden_run.run(analyzer, gcs)
    assert result == _reference("synthetic_result.json")
    assert not any(k.endswith("pose.npz") for k in store)


def test_result_unchanged_with_recorder_and_pose_written():
    rec = PoseRecorder()
    result, store = golden_run.run(analyzer, gcs, rec)
    assert result == _reference("synthetic_result.json")
    pose = load_npz(store["results/golden/pose.npz"])
    # 25 fps -> every 2nd frame -> 12.5 Hz, 125 frames over 10 s
    assert pose.rate_hz == 12.5 and len(pose.t) == 125
    # 4 to 5 s without a person
    gap = (pose.t >= 4.0) & (pose.t < 5.0)
    assert np.isnan(pose.landmarks[gap]).all()
    assert not np.isnan(pose.landmarks[~gap][..., :2]).any()


def test_recorder_failure_does_not_stop_the_analysis():
    class Broken(PoseRecorder):
        def to_npz_bytes(self):
            raise RuntimeError("disk full")

    result, store = golden_run.run(analyzer, gcs, Broken())
    assert result == _reference("synthetic_result.json")
    assert "results/golden/pose.npz" not in store


def test_error_inside_the_recorder_does_not_stop_the_analysis():
    class Broken(PoseRecorder):
        def _add(self, frame_idx, pose_result):
            if frame_idx > 40:
                raise ValueError("unexpected landmark")
            super()._add(frame_idx, pose_result)

    rec = Broken()
    result, store = golden_run.run(analyzer, gcs, rec)
    assert result == _reference("synthetic_result.json")
    assert rec.failed and "results/golden/pose.npz" not in store


@pytest.mark.skipif(not os.environ.get("MOTAVI_GOLDEN_VIDEO"), reason="MOTAVI_GOLDEN_VIDEO not set")
def test_real_video_unchanged():
    video = Path(os.environ["MOTAVI_GOLDEN_VIDEO"])
    store: dict[str, bytes] = {}
    saved = (gcs.download_bytes, gcs.upload_bytes)
    try:
        gcs.download_bytes = lambda p: video.read_bytes() if p.endswith("video.mp4") else store[p]
        gcs.upload_bytes = lambda p, data, ct=None: store.__setitem__(p, data)
        analyzer._run("testjob", {}, PoseRecorder())
    finally:
        gcs.download_bytes, gcs.upload_bytes = saved
    result = json.loads(store["results/testjob/result.json"])
    ref = _reference("testvideo_result.json")
    assert json.dumps(result, sort_keys=True) == json.dumps(ref, sort_keys=True)
