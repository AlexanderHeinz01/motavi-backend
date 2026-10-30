"""Load metrics (STECKBRIEF_MODUL §4.4): result.json and trunk twist from the pose."""
import numpy as np
import pytest

from backend.app.services.workplace.belastung import analyse_belastung, analyse_twist, from_result, twist_angle
from backend.tests.prepared import prepared_from_wrists
from backend.tests.profiles import kein_zyklus, zyklen

RATE = 15.0


def twisting(period=5.0, n=8, twist_s=1.0, deg=45.0):
    """Upright body; in every cycle the shoulders turn by deg against the hips for twist_s."""
    t = np.arange(int(period * n * RATE)) / RATE
    prep = prepared_from_wrists(t, (0.3 + 0 * t, -0.4 + 0 * t), (-0.3 + 0 * t, -0.4 + 0 * t))
    on = (t % period) < twist_s
    a = np.radians(np.where(on, deg, 0.0))
    for name, sign in (("left_shoulder", -1), ("right_shoulder", 1)):
        k = prep.names.index(name)
        prep.rel[:, k, 0] = sign * 0.35 * np.cos(a)
        prep.rel[:, k, 2] = sign * 0.35 * np.sin(a)
    return prep


def test_twist_angle():
    prep = twisting(deg=45.0)
    ang = twist_angle(prep)
    assert np.nanmax(np.abs(ang)) == pytest.approx(45.0, abs=1e-6)
    assert np.nanmin(np.abs(ang)) == pytest.approx(0.0, abs=1e-6)


def test_twist_share_and_per_cycle():
    prep = twisting(period=5.0, n=8, twist_s=1.0)
    anteil, pro_zyklus = analyse_twist(prep, zyklen(5.0, 0.05, 500, 1.0, n=8))
    assert anteil.wert == pytest.approx(0.2, abs=0.02) and anteil.belastbar
    assert pro_zyklus.wert == pytest.approx(1.0)


def test_short_and_small_twists_do_not_count():
    assert analyse_twist(twisting(deg=20.0), None)[0].wert == 0.0
    # 0.15 s (2 to 3 frames) is shorter than min_twist_s
    assert analyse_twist(twisting(twist_s=0.15), None)[0].wert == 0.0


def test_twist_without_cycle_or_person():
    prep = twisting()
    _, pro_zyklus = analyse_twist(prep, kein_zyklus())
    assert pro_zyklus.wert is None and pro_zyklus.grund == "Kein wiederkehrender Zyklus erkannt"
    prep.rel[:] = np.nan
    object.__setattr__(prep, "valid", np.zeros(len(prep.t), dtype=bool))
    anteil, _ = analyse_twist(prep, None)
    assert anteil.wert is None and not anteil.belastbar


def test_from_result():
    r = from_result({
        "reba_score": 6.4,
        "critical_frames": [{"reba": 9.1}, {"reba": 8.2}],
        "movements": {"bending": {"pct": 12.5}, "overhead": {"pct": 4.0}, "neutral": {"pct": 83.5}},
    })
    assert r["reba_mittel"].wert == 6.4 and r["reba_max"].wert == 9.1
    assert r["buecken_anteil"].wert == pytest.approx(0.125) and r["ueberkopf_anteil"].wert == pytest.approx(0.04)
    empty = from_result({})
    assert all(not k.belastbar for k in empty.values())


def test_analyse_belastung_without_pose():
    b = analyse_belastung({"reba_score": 5.0}, None, None)
    assert b.reba_mittel.wert == 5.0 and b.drehung_anteil.wert is None and b.drehung_anteil.grund == "Keine Pose-Daten"
