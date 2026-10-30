"""Per-frame pose data for the Steckbrief module (S1, docs/POSE_DATEN.md).

The analysis pipeline detects the pose on every frame for anonymisation; the
recorder keeps a copy of the landmarks at up to 15 Hz instead of discarding
them. Only coordinates, no image data. Landmarks of the eyes and the mouth
are dropped (data minimisation); nose and ears stay for the neck angle.

File results/{job_id}/pose.npz (numpy savez_compressed):

    version     int16        format version (1)
    t           float32 [F]  time stamp of each frame in seconds
    landmarks   float16 [F, 25, 4]  x, y, z, visibility per kept landmark;
                             NaN where no person was detected
    indices     int16 [25]   MediaPipe Pose index of each kept landmark
    names       str [25]     MediaPipe name of each kept landmark
    fps         float32      frame rate of the video
    step        int16        every step-th video frame is recorded
    width       int32        video width in pixels
    height      int32        video height in pixels

x and y are normalised to 0..1 of the image width and height (MediaPipe);
for angles multiply by width and height first. z is MediaPipe's relative
depth (same scale as x).
"""
from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

FORMAT_VERSION = 1
MAX_HZ = 15.0

# MediaPipe Pose landmark names by index (33 landmarks)
MEDIAPIPE_NAMES: tuple[str, ...] = (
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
)

# Dropped: eyes (1 to 6) and mouth (9, 10). Kept: nose, ears, body.
DROPPED: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 9, 10})
KEPT_INDICES: tuple[int, ...] = tuple(i for i in range(33) if i not in DROPPED)
KEPT_NAMES: tuple[str, ...] = tuple(MEDIAPIPE_NAMES[i] for i in KEPT_INDICES)


def frame_step(fps: float, max_hz: float = MAX_HZ) -> int:
    """Record every step-th frame so that the rate stays at or below max_hz."""
    return max(1, math.ceil(fps / max_hz - 1e-9))


class PoseRecorder:
    """Collects landmarks while the pipeline runs; see the module docstring."""

    def __init__(self, max_hz: float = MAX_HZ) -> None:
        self.max_hz = max_hz
        self._t: list[float] = []
        self._lm: list[np.ndarray] = []
        self.fps = 0.0
        self.width = 0
        self.height = 0
        self.failed = False

    def start(self, fps: float, width: int, height: int) -> None:
        self.fps, self.width, self.height = float(fps), int(width), int(height)
        self._step = frame_step(self.fps, self.max_hz)

    def add(self, frame_idx: int, pose_result) -> None:
        """Called for every decoded frame with the MediaPipe result.

        Never raises: on an error the recording stops (and no pose.npz is
        written), the analysis itself goes on.
        """
        if self.failed or frame_idx % self._step:
            return
        try:
            self._add(frame_idx, pose_result)
        except Exception:
            logger.exception("Pose recording stopped at frame %d", frame_idx)
            self.failed = True

    def _add(self, frame_idx: int, pose_result) -> None:
        row = np.full((len(KEPT_INDICES), 4), np.nan, dtype=np.float32)
        if pose_result.pose_landmarks:
            lm = pose_result.pose_landmarks[0]  # first detected person, as in the pipeline
            for k, i in enumerate(KEPT_INDICES):
                p = lm[i]
                row[k] = (p.x, p.y, p.z, p.visibility if p.visibility is not None else np.nan)
        self._t.append(frame_idx / self.fps)
        self._lm.append(row)

    def __len__(self) -> int:
        return len(self._t)

    def to_npz_bytes(self) -> bytes:
        if self.failed:
            raise RuntimeError("pose recording incomplete, not saved")
        buf = io.BytesIO()
        landmarks = np.stack(self._lm) if self._lm else np.empty((0, len(KEPT_INDICES), 4), dtype=np.float32)
        np.savez_compressed(
            buf,
            version=np.int16(FORMAT_VERSION),
            t=np.asarray(self._t, dtype=np.float32),
            landmarks=landmarks.astype(np.float16),
            indices=np.asarray(KEPT_INDICES, dtype=np.int16),
            names=np.asarray(KEPT_NAMES),
            fps=np.float32(self.fps),
            step=np.int16(self._step),
            width=np.int32(self.width),
            height=np.int32(self.height),
        )
        return buf.getvalue()


@dataclass(frozen=True)
class PoseData:
    t: np.ndarray  # [F] seconds
    landmarks: np.ndarray  # [F, 25, 4] float32 (converted from float16)
    indices: tuple[int, ...]
    names: tuple[str, ...]
    fps: float
    step: int
    width: int
    height: int

    @property
    def rate_hz(self) -> float:
        return self.fps / self.step

    def column(self, name: str) -> int:
        """Position of a MediaPipe landmark (by name) in the landmarks array."""
        return self.names.index(name)


def load_npz(data: bytes) -> PoseData:
    with np.load(io.BytesIO(data), allow_pickle=False) as f:
        version = int(f["version"])
        if version != FORMAT_VERSION:
            raise ValueError(f"pose.npz version {version} not supported")
        return PoseData(
            t=f["t"].astype(np.float64),
            landmarks=f["landmarks"].astype(np.float32),
            indices=tuple(int(i) for i in f["indices"]),
            names=tuple(str(n) for n in f["names"]),
            fps=float(f["fps"]),
            step=int(f["step"]),
            width=int(f["width"]),
            height=int(f["height"]),
        )
