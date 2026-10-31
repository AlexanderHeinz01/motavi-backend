"""4-page ergonomics report: print layout on white, readable colours, German numbers."""
import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from reportlab import rl_config

from backend.app.services import analyzer, pdf

RESULT = json.loads((Path(__file__).parent / "golden" / "testvideo_result.json").read_text(encoding="utf-8"))


def _luminance(c) -> float:
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red) + 0.7152 * ch(c.green) + 0.0722 * ch(c.blue)


def contrast(a, b) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_pages_are_white():
    canvas = MagicMock()
    pdf._footer(canvas, MagicMock(page=1))
    canvas.setFillColor.assert_any_call(pdf._PAGE_BG)
    assert pdf._PAGE_BG == pdf.colors.white


@pytest.mark.parametrize("name", list(pdf._styles()))
def test_text_styles_readable_on_white(name):
    # WCAG AA for normal text: 4.5:1 (the report was white on white once)
    assert contrast(pdf._styles()[name].textColor, pdf._PAGE_BG) >= 4.5


@pytest.mark.parametrize("farbe", [pdf._RED, pdf._AMBER, pdf._GREEN])
def test_traffic_light_readable_on_white(farbe):
    assert contrast(farbe, pdf._PAGE_BG) >= 4.5


def test_german_number_format():
    assert pdf._de(7.64) == "7,6" and pdf._de(46.2) == "46,2" and pdf._de(1234.5, 0) == "1.234"


def test_report_has_four_pages_and_decimal_commas(monkeypatch):
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    data = pdf.generate_report_pdf(RESULT)
    assert len(re.findall(rb"/Type /Page[^s]", data)) == 4
    assert b"(7,6)" in data and b"46,2 %" in data  # REBA score and overhead share
    assert b"(7.6)" not in data and b"46.2 %" not in data


@pytest.mark.parametrize("score, stufe", [
    (1.0, "Niedrig"), (3.99, "Niedrig"), (4.0, "Mittel"), (5.99, "Mittel"), (6.0, "Hoch"),
    (7.64, "Hoch"), (7.99, "Hoch"), (8.0, "Sehr hoch"), (10.0, "Sehr hoch"),
])
def test_index_levels_as_everywhere(score, stufe):
    # posture index 1 to 10, bounds 4, 6, 8 (docs/HALTUNGSINDEX.md), same as analyzer.stufe
    assert pdf.reba_stufe(score)[0] == stufe
    assert analyzer.stufe(score) == {"Niedrig": "LOW", "Mittel": "MEDIUM", "Hoch": "HIGH", "Sehr hoch": "VERY_HIGH"}[stufe]


def test_report_uses_score_not_old_level(monkeypatch):
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    # the level comes from the index, not from reba_level in result.json
    data = pdf.generate_report_pdf({**RESULT, "reba_level": "LOW"})
    assert b"(Hoch: Gestaltung bald verbessern)" in data
    assert b"(Niedrig: " not in data


def test_no_unchecked_legal_claim(monkeypatch):
    # "DSGVO-konform" only after a legal check (decision of 30.10.2026)
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    data = pdf.generate_report_pdf(RESULT)
    assert b"DSGVO" not in data and b"Analyse auf Servern in Deutschland" in data  # parentheses are escaped in the PDF


def test_report_with_cycle_and_reach_still_four_pages(monkeypatch):
    """Decision P1 (31.10.2026): the Video-Check delivers cycle time and reach
    in the ergonomics report."""
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    ablauf = {
        "zykluszeit_s": 38.4, "zyklen_pro_schicht": 690, "hinweis": None, "griffe_ausserhalb": 0.21,
        "hoehenzonen": {"unter_knie": 0.08, "knie_huefte": 0.29, "huefte_schulter": 0.56, "ueber_schulter": None},
        "zonen_text": {"unter_knie": "unter Knie", "knie_huefte": "Knie bis Hüfte", "huefte_schulter": "Hüfte bis Schulter", "ueber_schulter": "über Schulter"},
    }
    data = pdf.generate_report_pdf(RESULT, ablauf)
    assert len(re.findall(rb"/Type /Page[^s]", data)) == 4
    assert b"(38,4 s)" in data and b"(21 %)" in data and b"nicht belastbar messbar" in data


def test_report_route_uses_pose_data_when_present():
    from unittest.mock import patch

    from backend.app.routers import report
    from backend.tests.workcycle import prepared_work

    with patch.object(report.gcs, "download_bytes", return_value=b"npz"), \
         patch.object(report, "load_npz", side_effect=lambda b: b), \
         patch.object(report, "prepare", return_value=prepared_work()):
        k = report.ablauf_kennzahlen("job", 450)
    assert k["zykluszeit_s"] == pytest.approx(10.0, rel=0.05) and k["griffe_ausserhalb"] is not None
    with patch.object(report.gcs, "download_bytes", side_effect=FileNotFoundError):
        assert report.ablauf_kennzahlen("job", 450) is None
