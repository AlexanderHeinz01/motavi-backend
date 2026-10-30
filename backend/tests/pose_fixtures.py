"""Synthetic pose data for the tests: MediaPipe-like results without the model."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class FakeLandmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 0.99


@dataclass
class FakeResult:
    pose_landmarks: list


def body(w: int, h: int, trunk_deg: float = 0.0, arms_up: bool = False, dx_px: float = 0.0) -> list[FakeLandmark]:
    """33 landmarks of a person in pixel geometry, returned normalised (x / w, y / h).

    trunk_deg: forward bend of the trunk in the image plane. dx_px: shift
    of the whole person (walking).
    """
    hip = (w * 0.5 + dx_px, h * 0.6)
    trunk = h * 0.25
    a = math.radians(trunk_deg)
    sh = (hip[0] + trunk * math.sin(a), hip[1] - trunk * math.cos(a))
    head = (sh[0] + 0.3 * trunk * math.sin(a), sh[1] - 0.3 * trunk * math.cos(a))
    pts = [None] * 33

    def put(i, x, y, z=0.0):
        pts[i] = FakeLandmark(x / w, y / h, z / w)

    put(0, *head)
    for i in range(1, 11):  # eyes, ears, mouth around the head
        put(i, head[0] + (i - 5) * 2, head[1] - 4)
    half = trunk * 0.35
    put(11, sh[0] - half, sh[1]); put(12, sh[0] + half, sh[1])
    if arms_up:
        put(13, sh[0] - half, sh[1] - 30); put(14, sh[0] + half, sh[1] - 30)
        put(15, sh[0] - half, sh[1] - 60); put(16, sh[0] + half, sh[1] - 60)
    else:
        put(13, sh[0] - half, sh[1] + 30); put(14, sh[0] + half, sh[1] + 30)
        put(15, sh[0] - half + 20, sh[1] + 45); put(16, sh[0] + half + 20, sh[1] + 45)
    for i in range(17, 23):  # hands
        put(i, pts[15 + (i % 2)].x * w + 3, pts[15 + (i % 2)].y * h + 3)
    put(23, hip[0] - 15, hip[1]); put(24, hip[0] + 15, hip[1])
    put(25, hip[0] - 15, hip[1] + 45); put(26, hip[0] + 15, hip[1] + 45)
    put(27, hip[0] - 15, hip[1] + 90); put(28, hip[0] + 15, hip[1] + 90)
    for i in range(29, 33):
        put(i, hip[0] + (-15 if i % 2 else 15), hip[1] + 95)
    return pts


def scripted_result(frame_idx: int, fps: float, w: int, h: int) -> FakeResult:
    """10 s scene: bending up to 40 degrees, arms up from 6 to 7.5 s, no person from 4 to 5 s."""
    t = frame_idx / fps
    if 4.0 <= t < 5.0:
        return FakeResult([])
    trunk = 20 + 20 * math.sin(2 * math.pi * t / 2.5)
    return FakeResult([body(w, h, trunk_deg=trunk, arms_up=6.0 <= t < 7.5)])
