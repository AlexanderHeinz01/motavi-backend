"""Process steps (S3, STECKBRIEF_MODUL §4.3): proposal in the median cycle,
walking, review validation, transfer to all cycles."""
import numpy as np
import pytest

from backend.app.services.workplace.cycles import detect_cycles
from backend.app.services.workplace.segments import (
    STEP_TYPES,
    BewerteterSchritt,
    median_cycle,
    propose_segments,
    transfer,
    validate_review,
)
from backend.tests.workcycle import prepared_work


def analyse(**kw):
    prep = prepared_work(**kw)
    z = detect_cycles(prep)
    m = median_cycle(prep, z)
    return prep, z, m, propose_segments(m)


def true_phase(z, phase):
    """Phase in the true cycle of a phase in the detected median cycle (template offset)."""
    offset = (z.zyklen[0].start_s % 10.0) / 10.0
    return (phase + offset) % 1.0


@pytest.mark.parametrize("noise", [0.01, 0.03])
def test_proposal_finds_walking_rest_and_movement(noise):
    _, z, m, seg = analyse(noise=noise)
    assert m.anzahl_zyklen >= 7 and m.dauer_s == pytest.approx(10.0, rel=0.02)
    # walking: 30 % of the cycle (out 0 to 15 %, back 85 to 100 %)
    walk = sum(s.ende_phase - s.start_phase for s in seg if s.art == "ortswechsel")
    assert walk == pytest.approx(0.30, abs=0.07)
    assert all(s.vorschlag_typ == "Gehen" for s in seg if s.art == "ortswechsel")
    # rest: 15 % before the reach, 25 % joining; the slow start and end of
    # each movement and the turning point add a little
    rest = sum(s.ende_phase - s.start_phase for s in seg if s.art == "ruhe")
    assert 0.36 <= rest <= 0.56
    # the joining phase (true phase 0.6 to 0.85) is one rest segment
    fuegen = [s for s in seg if s.art == "ruhe" and true_phase(z, (s.start_phase + s.ende_phase) / 2) > 0.6]
    assert fuegen and max(s.ende_phase - s.start_phase for s in fuegen) == pytest.approx(0.25, abs=0.06)
    # contiguous from 0 to 1
    assert seg[0].start_phase == 0 and seg[-1].ende_phase == 1
    assert all(a.ende_phase == b.start_phase for a, b in zip(seg, seg[1:]))


def test_reach_out_and_back_is_split_at_the_turn():
    _, z, m, seg = analyse(noise=0.03)
    moves = [s for s in seg if s.art == "bewegung" and 0.2 < true_phase(z, s.start_phase) < 0.6]
    assert len(moves) == 2  # out and back
    assert all(s.dauer(m.dauer_s) == pytest.approx(1.5, abs=0.5) for s in moves)


def test_no_walking_without_hip_movement():
    prep = prepared_work()
    object.__setattr__(prep, "hip", np.zeros_like(prep.hip))
    z = detect_cycles(prep)
    seg = propose_segments(median_cycle(prep, z))
    assert not any(s.art == "ortswechsel" for s in seg)


def test_short_segments_are_merged():
    _, _, m, seg = analyse()
    assert all(s.dauer(m.dauer_s) >= 0.4 - 1e-9 for s in seg)


def test_review_validation():
    ok = [BewerteterSchritt(0, 0.4, "Greifen", "notwendig"), BewerteterSchritt(0.4, 1, "Fügen", "wertschoepfend")]
    assert validate_review(ok) == []
    gap = [BewerteterSchritt(0, 0.4, "Greifen", "notwendig"), BewerteterSchritt(0.5, 1, "Fügen", "wertschoepfend")]
    assert any("Lücke" in e for e in validate_review(gap))
    bad = [BewerteterSchritt(0, 1, "Tanzen", "notwendig")]
    assert any("unbekannter Typ" in e for e in validate_review(bad))
    short = [BewerteterSchritt(0, 0.8, "Greifen", "notwendig")]
    assert any("bei 1 enden" in e for e in validate_review(short))


def test_transfer_scales_to_every_cycle():
    _, z, _, _ = analyse()
    schritte = [
        BewerteterSchritt(0.0, 0.3, "Gehen", "verschwendung"),
        BewerteterSchritt(0.3, 0.5, "Greifen", "notwendig"),
        BewerteterSchritt(0.5, 0.6, "Greifen", "notwendig"),
        BewerteterSchritt(0.6, 1.0, "Fügen", "wertschoepfend"),
    ]
    e = transfer(schritte, z)
    assert e.anzahl_zyklen == z.anzahl_gueltig
    assert e.anteile_ablauf == pytest.approx({"verschwendung": 0.3, "notwendig": 0.3, "wertschoepfend": 0.4}, abs=1e-6)
    for row in e.je_zyklus:
        assert row["verschwendung"] == pytest.approx(0.3 * row["dauer_s"])
    # two Greifen segments in a row are one step
    assert [s["typ"] for s in e.ablaufschritte] == ["Gehen", "Greifen", "Fügen"]
    assert e.ablaufschritte[1]["anteil"] == pytest.approx(0.3)
    # minutes per shift: seconds of waste per cycle times cycles per shift
    expected = e.sekunden_je_zyklus["verschwendung"] * z.zyklen_pro_schicht.wert / 60
    assert e.minuten_pro_schicht["verschwendung"] == pytest.approx(expected, rel=0.01)


def test_every_type_has_a_known_class():
    assert set(STEP_TYPES.values()) == {"wertschoepfend", "notwendig", "verschwendung"}
