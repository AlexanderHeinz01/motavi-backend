"""Movement rules of the analysis pipeline: trunk angle in pixels, overhead
above ear height, upper arm angle to the trunk."""
import math
from dataclasses import dataclass

import pytest

from backend.app.services import analyzer


@dataclass
class L:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 0.99


def person(w, h, trunk_deg=0.0, arm_deg=0.0):
    """Landmarks in pixel geometry (returned normalised). arm_deg: both upper
    arms at this angle to the trunk, pointing sideways in the image."""
    pts = [L(0.5, 0.5) for _ in range(33)]
    hip = (w / 2, h * 0.6)
    trunk = h * 0.25
    a = math.radians(trunk_deg)
    sh = (hip[0] + trunk * math.sin(a), hip[1] - trunk * math.cos(a))
    head = (sh[0] + 0.3 * trunk * math.sin(a), sh[1] - 0.3 * trunk * math.cos(a))

    def put(i, x, y):
        pts[i] = L(x / w, y / h)

    put(0, *head)
    put(7, head[0] - 8, head[1]); put(8, head[0] + 8, head[1])
    put(23, hip[0] - 15, hip[1]); put(24, hip[0] + 15, hip[1])
    for side, (si, ei, wi) in ((-1, (11, 13, 15)), (1, (12, 14, 16))):
        s = (sh[0] + side * 30, sh[1])
        b = math.radians(arm_deg)
        # trunk points down; the arm turns away from it to the side
        down = (-math.sin(a), math.cos(a))
        side_dir = (side * math.cos(a), side * math.sin(a))
        d = (down[0] * math.cos(b) + side_dir[0] * math.sin(b), down[1] * math.cos(b) + side_dir[1] * math.sin(b))
        put(si, *s)
        put(ei, s[0] + 90 * d[0], s[1] + 90 * d[1])
        put(wi, s[0] + 170 * d[0], s[1] + 170 * d[1])
    return pts


@pytest.mark.parametrize("w,h", [(640, 640), (1920, 1080), (960, 640), (1080, 1920)])
def test_trunk_angle_independent_of_aspect_ratio(w, h):
    assert analyzer._trunk_angle(person(w, h, trunk_deg=30), w, h) == pytest.approx(30, abs=0.01)


@pytest.mark.parametrize("arm,expected", [(0, 0), (45, 45), (90, 90), (120, 120), (170, 170)])
def test_upper_arm_angle(arm, expected):
    for w, h in [(1920, 1080), (640, 640)]:
        assert analyzer._upper_arm_elevation(person(w, h, arm_deg=arm), w, h) == pytest.approx(expected, abs=0.01)


def test_arms_at_shoulder_height_are_not_overhead():
    w, h = 1920, 1080
    assert analyzer._classify_movement(person(w, h, arm_deg=90), w, h) == "neutral"
    assert analyzer._classify_movement(person(w, h, arm_deg=100), w, h) == "neutral"


def test_wrist_above_ear_is_overhead():
    w, h = 1920, 1080
    assert analyzer._classify_movement(person(w, h, arm_deg=170), w, h) == "overhead"


def test_bending_threshold_from_settings(monkeypatch):
    w, h = 1920, 1080
    assert analyzer._classify_movement(person(w, h, trunk_deg=25), w, h) == "bending"
    monkeypatch.setattr(analyzer.settings, "MOVEMENT_BENDING_DEG", 30.0)
    assert analyzer._classify_movement(person(w, h, trunk_deg=25), w, h) == "neutral"


def test_ear_height_falls_back_to_nose():
    pts = person(640, 640)
    pts[7].visibility = pts[8].visibility = 0.1
    assert analyzer._ear_height(pts) == pts[0].y
