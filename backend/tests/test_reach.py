"""Reach and working heights (S2, STECKBRIEF_MODUL §4.2)."""
import numpy as np
import pytest

from backend.app.services.workplace.reach import HINWEIS_2D, ReachConfig, analyse_reach
from backend.tests.prepared import prepared_from_wrists

RATE = 15.0


def moves(points, hold_s=1.0, move_s=0.6, repeat=10):
    """Hand trajectory: hold at each point, move linearly to the next one."""
    xs, ys = [], []
    seq = points * repeat
    for (x0, y0), (x1, y1) in zip(seq, seq[1:] + seq[:1]):
        xs += [x0] * int(hold_s * RATE); ys += [y0] * int(hold_s * RATE)
        n = int(move_s * RATE)
        xs += list(np.linspace(x0, x1, n, endpoint=False)); ys += list(np.linspace(y0, y1, n, endpoint=False))
    return np.array(xs), np.array(ys)


def test_zones_with_time_shares():
    t = np.arange(int(100 * RATE)) / RATE
    # left hand 30 % of the time above the shoulder, otherwise at chest height
    ly = np.where((t % 10) < 3, -1.3, -0.5)
    prep = prepared_from_wrists(t, (0.3 + 0 * t, ly), (0.3 + 0 * t, 0.5 + 0 * t))
    r = analyse_reach(prep)
    z = {k: v.wert for k, v in r.hoehenzonen.items()}
    assert z["ueber_schulter"] == pytest.approx(0.15, abs=0.01)  # 30 % of one of two hands
    assert z["huefte_schulter"] == pytest.approx(0.35, abs=0.01)
    assert z["knie_huefte"] == pytest.approx(0.5, abs=0.01)
    assert z["unter_knie"] == pytest.approx(0.0, abs=0.01)
    assert sum(z.values()) == pytest.approx(1.0)
    assert r.hinweis == HINWEIS_2D


def test_grips_inside_and_outside_the_favourable_reach():
    # alternate between a point close to the body at chest height and a far one
    x, y = moves([(0.4, -0.5), (1.4, -0.5)])
    t = np.arange(len(x)) / RATE
    prep = prepared_from_wrists(t, (x, y), (0.2 + 0 * t, 0.3 + 0 * t))
    r = analyse_reach(prep)
    assert r.anzahl_griffe == pytest.approx(20, abs=1)
    assert r.griffe_ausserhalb.belastbar
    assert r.griffe_ausserhalb.wert == pytest.approx(0.5, abs=0.06)
    far = [g for g in r.griffe if g.x > 1.0]
    assert far and all(g.ausserhalb for g in far)


def test_grip_below_knee_is_outside():
    x, y = moves([(0.4, -0.5), (0.4, 1.2)])
    t = np.arange(len(x)) / RATE
    r = analyse_reach(prepared_from_wrists(t, (x, y), (0.2 + 0 * t, 0.3 + 0 * t)))
    low = [g for g in r.griffe if g.zone == "unter_knie"]
    assert low and all(g.ausserhalb for g in low)
    assert r.griffe_ausserhalb.wert == pytest.approx(0.5, abs=0.06)


def test_idle_hand_is_not_a_grip():
    t = np.arange(int(60 * RATE)) / RATE
    r = analyse_reach(prepared_from_wrists(t, (0.3 + 0 * t, 0.2 + 0 * t), (0.3 + 0 * t, 0.2 + 0 * t)))
    assert r.anzahl_griffe == 0
    assert not r.griffe_ausserhalb.belastbar and "Zu wenige Griffe" in r.griffe_ausserhalb.grund


def test_threshold_close_to_body_from_config():
    x, y = moves([(0.4, -0.5), (0.9, -0.5)], move_s=0.3)
    t = np.arange(len(x)) / RATE
    prep = prepared_from_wrists(t, (x, y), (0.2 + 0 * t, 0.3 + 0 * t))
    assert analyse_reach(prep, ReachConfig(koerpernah_max=0.7)).griffe_ausserhalb.wert == pytest.approx(0.5, abs=0.06)
    assert analyse_reach(prep, ReachConfig(koerpernah_max=1.0)).griffe_ausserhalb.wert == pytest.approx(0.0, abs=0.01)


def test_low_coverage_is_not_reliable():
    x, y = moves([(0.4, -0.5), (1.4, -0.5)])
    t = np.arange(len(x)) / RATE
    valid = (np.arange(len(t)) % 3) == 0  # a third of the frames
    r = analyse_reach(prepared_from_wrists(t, (x, y), (0.2 + 0 * t, 0.3 + 0 * t), valid=valid))
    assert all(not k.belastbar for k in r.hoehenzonen.values())


def test_density_normalised():
    x, y = moves([(0.4, -0.5), (1.4, -0.5)])
    t = np.arange(len(x)) / RATE
    r = analyse_reach(prepared_from_wrists(t, (x, y), (0.2 + 0 * t, 0.3 + 0 * t)))
    assert r.dichte.max() == pytest.approx(1.0) and r.dichte.shape == (25, 20)


def test_hidden_far_hand_and_knees_side_view():
    # side view: the right hand is hidden most of the time, knees behind a bench
    x, y = moves([(0.4, -0.5), (1.4, -0.5)])
    t = np.arange(len(x)) / RATE
    prep = prepared_from_wrists(t, (x, y), (0.2 + 0 * t, 0.3 + 0 * t))
    k = list(prep.names)
    prep.rel[:, k.index("right_wrist")] = np.nan
    prep.rel[:, k.index("left_knee")] = np.nan
    prep.rel[:, k.index("right_knee")] = np.nan
    r = analyse_reach(prep)
    assert r.hoehenzonen["huefte_schulter"].belastbar
    assert r.hoehenzonen["huefte_schulter"].wert == pytest.approx(1.0)
    assert r.griffe_ausserhalb.wert == pytest.approx(0.5, abs=0.06)
