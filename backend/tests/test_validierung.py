"""S6: validation script (manual time stamps against detected cycles) and the
cycle detection with a short repeated motion inside a step."""
import json

import pytest

from backend.app.services.workplace.cycles import detect_cycles
from backend.app.services.workplace.pose_store import load_npz
from backend.app.services.workplace.preprocess import prepare
from backend.scripts import validate_steckbrief as v
from backend.tests.profiles import kein_zyklus, zyklen
from backend.tests.synth_videos import arbeitszyklen, ohne_zyklus, szenarien, von_hand


def schreibe_csv(path, rows, kopf="video,start_s,ende_s,typ"):
    path.write_text(kopf + "\n" + "\n".join(",".join(map(str, r)) for r in rows) + "\n", encoding="utf-8")
    return path


# ── CSV ──────────────────────────────────────────────────────────────────────


def test_csv_read(tmp_path):
    p = schreibe_csv(tmp_path / "m.csv", [
        ("a.mp4", 10, 20, "Zyklus"), ("a.mp4", 0, 10, "zyklus"), ("a.mp4", 0, 2, "Gehen"), ("# Kommentar", "", "", ""),
        ("b.mp4", 0, 300, "kein Zyklus"),
    ])
    m = v.lese_csv(p)
    assert m["a.mp4"].zyklen == [(0, 10), (10, 20)] and m["a.mp4"].segmente == [(0, 2, "Gehen")]
    assert m["b.mp4"].kein_zyklus and m["b.mp4"].zyklen == []


@pytest.mark.parametrize("rows, kopf, meldung", [
    ([("a.mp4", 1, 2, "Zyklus")], "video;start;ende;typ", "Erste Zeile"),
    ([("a.mp4", "x", 2, "Zyklus")], None, "Zeile 2: start_s und ende_s"),
    ([("a.mp4", 5, 2, "Zyklus")], None, "Zeile 2: ende_s muss nach start_s"),
    ([("a.mp4", 1, 2, "Kaffee")], None, "unbekannter Typ"),
    ([("a.mp4", 1, 2, "Gehen")], None, "keine Zyklen erfasst"),
    ([("a.mp4", 1, 2, "Zyklus"), ("a.mp4", 0, 9, "kein Zyklus")], None, "zugleich"),
])
def test_csv_errors_name_the_problem(tmp_path, rows, kopf, meldung):
    p = schreibe_csv(tmp_path / "m.csv", rows, kopf or "video,start_s,ende_s,typ")
    with pytest.raises(v.CsvFehler, match=meldung):
        v.lese_csv(p)


# ── comparison ───────────────────────────────────────────────────────────────


def test_iou_and_one_to_one_matching():
    assert v.iou((0, 10), (5, 15)) == pytest.approx(5 / 15)
    manuell = [(0, 10), (10, 20), (20, 30)]
    erkannt = [(1, 11), (11, 21), (40, 50), (10.5, 20.5)]
    paare = v.zuordnen(manuell, erkannt)
    assert [(i, j) for i, j, _ in paare] == [(0, 0), (1, 3)]  # the better of two candidates, each only once


def test_waste_share_only_inside_manual_cycles():
    m = v.Manuell(zyklen=[(0, 10), (10, 20)], segmente=[(0, 2, "Gehen"), (2, 10, "Fügen"), (18, 25, "Warten")])
    # Gehen 2 s + Warten 2 s inside the cycles, of 20 s
    assert v.verschwendung_manuell(m) == pytest.approx(0.2)
    assert v.verschwendung_manuell(v.Manuell(zyklen=[(0, 10)])) is None


def test_compare_exact_and_shifted_detection():
    z = zyklen(10.0, 0.05, 480, 0.9, n=10)  # detected: 0..10, 10..20, ...
    m = v.Manuell(zyklen=[(i * 10 + 1, i * 10 + 11) for i in range(9)] + [(200, 211)])
    e = v.vergleiche("a", m, z, None)
    assert e.anzahl_manuell == 10 and e.anzahl_erkannt == 10
    assert e.abw_median == pytest.approx(0.0) and e.abw_anzahl == 0
    # 9 matched (IoU 9/11); the detected cycle 90..100 and the manual 200..211 are unmatched
    assert e.falsch_erkannt == 1 and e.verpasst == 1 and e.anteil_falsch == pytest.approx(0.1)
    assert e.grenzabweichung_s == pytest.approx(1.0)
    assert e.zyklus_richtig


def test_compare_no_cycle_both_ways():
    e = v.vergleiche("a", v.Manuell(kein_zyklus=True), kein_zyklus(), None)
    assert e.zyklus_richtig and e.anzahl_erkannt == 0
    e = v.vergleiche("a", v.Manuell(zyklen=[(0, 10), (10, 20)]), kein_zyklus(), None)
    assert not e.zyklus_richtig and e.abw_median is None and e.verpasst == 2


def _ergebnis(abw_median=0.0, abw_anzahl=0.0, falsch=0.0, w_pp=None, kein=False):
    return v.VideoErgebnis("x", kein, not kein, None, 0 if kein else 10, 0 if kein else 10, 10, 10, None if kein else abw_median,
                           None if kein else abw_anzahl, 0, 0, None if kein else falsch, 0.0, 0.5, 0.1, 0.1, 0.4,
                           None if w_pp is None else 0.4 + w_pp / 100, w_pp, True)


def test_summary_decisions():
    z = v.Ziele()
    g = v.gesamt([_ergebnis(0.05), _ergebnis(-0.09), _ergebnis(0.02)], z)
    assert g["median"]["status"] == "Ziel erreicht" and g["median"]["im_ziel"] == 3
    g = v.gesamt([_ergebnis(0.05), _ergebnis(0.12), _ergebnis(0.02)], z)
    assert g["median"]["status"] == "Ziel nicht erreicht" and g["median"]["im_ziel"] == 2
    g = v.gesamt([_ergebnis(0.05), _ergebnis(0.02)], z)
    assert g["median"]["status"] == "zu wenige Videos"
    g = v.gesamt([_ergebnis(falsch=0.2), _ergebnis(), _ergebnis()], z)
    assert g["anzahl"]["status"] == "Ziel nicht erreicht"
    g = v.gesamt([_ergebnis(w_pp=4.0), _ergebnis(w_pp=-3.0), _ergebnis(w_pp=1.0), _ergebnis()], z)
    assert g["verschwendung"]["videos"] == 3 and g["verschwendung"]["status"] == "Ziel erreicht"


def test_report_pilot_label():
    erg = [_ergebnis(0.01), _ergebnis(0.02), _ergebnis(0.03)]
    g = v.gesamt(erg, v.Ziele())
    echt = v.bericht(erg, g, v.Ziele(), "m.csv")
    assert "| `zykluszeit_median_s` | kann entfallen |" in echt
    assert "| `hoehenzonen` | bleibt (mit diesem Skript nicht geprüft) |" in echt
    synth = v.bericht(erg, g, v.Ziele(), "m.csv", synthetisch=True)
    assert "keine Validierung" in synth and "kann entfallen" not in synth


# ── cycle detection: short repeated motion inside a step (found by S6) ───────


@pytest.mark.parametrize("seed", range(3))
def test_wiggle_inside_a_step_does_not_become_the_cycle(seed):
    """Joining with a small 2 s back-and-forth inside a 25 s cycle: the cycle is 25 s, not 2 s."""
    sv = arbeitszyklen("x", 25.0, 9, warten_vk=0.4, seed=seed + 2)
    z = detect_cycles(prepare(load_npz(sv.npz)))
    assert z.erkannt and z.zykluszeit_median.wert == pytest.approx(25.0, rel=0.1)


# ── end to end ───────────────────────────────────────────────────────────────


def test_script_end_to_end(tmp_path):
    daten = tmp_path / "daten"
    daten.mkdir()
    rows = []
    for sv in szenarien():
        stem = sv.name.rsplit(".", 1)[0]
        if stem.startswith("takt"):  # one in a folder like a bucket download
            (daten / sv.name).mkdir()
            (daten / sv.name / "pose.npz").write_bytes(sv.npz)
            (daten / sv.name / "review.json").write_text(json.dumps(sv.review))
        else:
            (daten / f"{stem}.npz").write_bytes(sv.npz)
            if sv.review:
                (daten / f"{stem}.review.json").write_text(json.dumps(sv.review))
        rows += von_hand(sv)
    csv_path = schreibe_csv(tmp_path / "manuell.csv", rows)
    out, js = tmp_path / "bericht.md", tmp_path / "bericht.json"
    assert v.main([str(csv_path), "--daten", str(daten), "--out", str(out), "--json", str(js), "--synthetisch"]) == 0
    g = json.loads(js.read_text())["gesamt"]
    assert g["median"]["status"] == "Ziel erreicht" and g["anzahl"]["status"] == "Ziel erreicht"
    assert g["kein_zyklus"]["im_ziel"] == 1
    assert g["verschwendung"]["status"] == "Ziel erreicht"
    assert "Prüflauf mit synthetischen Daten" in out.read_text()


def test_missing_data_is_reported(tmp_path):
    csv_path = schreibe_csv(tmp_path / "m.csv", [("fehlt.mp4", 0, 10, "Zyklus")])
    with pytest.raises(FileNotFoundError, match="fehlt.mp4"):
        v.main([str(csv_path), "--daten", str(tmp_path)])


def test_aperiodic_synthetic_video_has_no_cycle():
    assert not detect_cycles(prepare(load_npz(ohne_zyklus("x", seed=7).npz))).erkannt
