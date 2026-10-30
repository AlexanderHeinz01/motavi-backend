"""Run the analysis pipeline on a synthetic video with a scripted fake
landmarker (no model, deterministic). Used by the golden test and to create
its reference.

    python -m backend.tests.golden_run > backend/tests/golden/synthetic_result.json
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import cv2
import numpy as np

from backend.tests.pose_fixtures import scripted_result

FPS, W, H, FRAMES = 25.0, 320, 240, 250


def synthetic_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(FRAMES):
        writer.write(np.full((H, W, 3), 40 + (i % 50) * 3, dtype=np.uint8))
    writer.release()


class _FakeLandmarker:
    def __init__(self) -> None:
        self.i = 0

    @classmethod
    def create_from_options(cls, _options):
        return cls()

    def detect(self, _image):
        r = scripted_result(self.i, FPS, W, H)
        self.i += 1
        return r

    def close(self) -> None:
        pass


def run(analyzer, gcs, recorder=None) -> tuple[dict, dict[str, bytes]]:
    """Returns result.json as dict and everything written to the fake GCS."""
    store: dict[str, bytes] = {}
    saved = (analyzer.PoseLandmarker, analyzer._ensure_model, gcs.download_bytes, gcs.upload_bytes)
    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "video.mp4"
        synthetic_video(video)
        try:
            analyzer.PoseLandmarker = _FakeLandmarker
            analyzer._ensure_model = lambda: None
            gcs.download_bytes = lambda p: video.read_bytes() if p.endswith("video.mp4") else store[p]
            gcs.upload_bytes = lambda p, data, ct=None: store.__setitem__(p, data)
            if recorder is None:
                analyzer._run("golden", {})
            else:
                analyzer._run("golden", {}, recorder)
        finally:
            analyzer.PoseLandmarker, analyzer._ensure_model, gcs.download_bytes, gcs.upload_bytes = saved
    return json.loads(store["results/golden/result.json"]), store


if __name__ == "__main__":
    from backend.app.services import analyzer, gcs

    print(json.dumps(run(analyzer, gcs)[0], indent=1, sort_keys=True, ensure_ascii=False))
