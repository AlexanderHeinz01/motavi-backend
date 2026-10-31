"""Critical frames, detection and angles of the analysis (E.3.2, E.3.5 and
E.3.17 of the review on 31.10.2026)."""
import cv2
import numpy as np

from backend.app.services import analyzer, gcs
from backend.app.services.workplace.belastung import from_result
from backend.tests import golden_run
from backend.tests.pose_fixtures import FakeResult, body

W, H = 640, 480


def test_frame_without_person_is_dropped():
    frame = np.full((H, W, 3), 200, dtype=np.uint8)
    assert analyzer._schwaerzen(frame, [], []) is None


def test_head_box_generous_and_black():
    lm = body(W, H)
    x0, y0, x1, y1 = analyzer._kopfbox(lm, W, H)
    kopf = np.array([[p.x * W, p.y * H] for p in lm[0:11]])
    schultern = abs(lm[11].x - lm[12].x) * W
    # every head point well inside, box at least as wide as the shoulders
    assert (kopf[:, 0] > x0 + 10).all() and (kopf[:, 0] < x1 - 10).all()
    assert (kopf[:, 1] > y0 + 10).all() and (kopf[:, 1] < y1 - 10).all()
    assert x1 - x0 >= schultern
    frame = analyzer._schwaerzen(np.full((H, W, 3), 200, dtype=np.uint8), [lm], [])
    cx, cy = kopf.mean(axis=0).astype(int)
    assert (frame[cy - 5:cy + 5, cx - 5:cx + 5] == 0).all()


def test_all_persons_and_faces_blacked_out():
    links, rechts = body(W, H, dx_px=-200), body(W, H, dx_px=200)

    class Box:
        origin_x, origin_y, width, height = 300, 20, 40, 40

    gesicht = type("Det", (), {"bounding_box": Box()})()
    frame = analyzer._schwaerzen(np.full((H, W, 3), 200, dtype=np.uint8), [links, rechts], [gesicht])
    for lm in (links, rechts):
        cx, cy = int(lm[0].x * W), int(lm[0].y * H)
        assert (frame[cy, cx] == 0).all()
    assert (frame[40, 320] == 0).all()  # face box centre
    assert (frame[H - 5, 5] == 200).all()  # rest of the image untouched


def test_saved_frames_have_black_heads():
    _, store = golden_run.run(analyzer, gcs)
    bild = cv2.imdecode(np.frombuffer(store["results/golden/frames/critical_1.jpg"], np.uint8), cv2.IMREAD_COLOR)
    assert bild is not None and (bild < 30).all(axis=2).mean() > 0.02


def test_no_person_gives_an_error_not_low_risk(monkeypatch):
    monkeypatch.setattr(golden_run, "scripted_result", lambda *a: FakeResult([]))
    result, store = golden_run.run(analyzer, gcs)
    assert result == {"error": analyzer._erkennung_fehler(0.0)}
    assert not any("/frames/" in k for k in store)


def test_detection_share_messages():
    assert "keine Person" in analyzer._erkennung_fehler(0.0)
    assert "30 %" in analyzer._erkennung_fehler(0.3)
    assert analyzer._erkennung_fehler(0.9) is None


def test_detection_share_is_the_quality_in_the_steckbrief():
    base = {"reba_score": 5.0, "reba_max": 7.0, "movements": {"bending": {"pct": 10.0}, "overhead": {"pct": 0.0}}}
    assert from_result({**base, "erkennung_anteil": 0.9})["reba_mittel"].wert == 5.0
    k = from_result({**base, "erkennung_anteil": 0.4})["reba_mittel"]
    assert k.wert is None and not k.belastbar
    assert from_result(base)["reba_max"].wert == 7.0


def test_standing_upright_is_low():
    """E.3.17: hanging arms used to give the highest upper arm level (index
    4.6, medium); now as in the browser port about 3.1, low."""
    lm = body(W, H)
    scores = analyzer._reba_subscores(lm, W, H)
    assert scores["shoulder_r"] == 1.5 and scores["neck"] == 1.0
    index = analyzer._overall_reba(scores)
    assert index < 4 and analyzer.stufe(index) == "LOW"


def test_levels():
    assert [analyzer.stufe(v) for v in (3.99, 4.0, 5.99, 6.0, 7.99, 8.0)] == ["LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH", "VERY_HIGH"]
