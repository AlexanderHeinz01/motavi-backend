"""4-page ergonomics report: print layout on white, readable colours, German numbers."""
import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from reportlab import rl_config

from backend.app.services import pdf

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
    (1.0, "Vernachlässigbar"), (1.99, "Vernachlässigbar"), (2.0, "Niedrig"), (3.9, "Niedrig"), (4.0, "Mittel"),
    (7.64, "Mittel"), (7.99, "Mittel"), (8.0, "Hoch"), (10.9, "Hoch"), (11.0, "Sehr hoch"), (15.0, "Sehr hoch"),
])
def test_reba_levels_as_on_the_website(score, stufe):
    # bounds of rebaStufe in the motavi repo (src/lib/steckbrief.ts): below 2, 4, 8, 11
    assert pdf.reba_stufe(score)[0] == stufe


def test_report_uses_score_not_old_level(monkeypatch):
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    # result.json says HIGH (old bounds); 7.6 is "mittel" on the REBA scale
    data = pdf.generate_report_pdf({**RESULT, "reba_level": "HIGH"})
    assert b"(Mittel: Ma" in data  # umlauts are escaped in the PDF stream
    assert b"Korrekturma" not in data and b"(Hoch: " not in data


def test_no_unchecked_legal_claim(monkeypatch):
    # "DSGVO-konform" only after a legal check (decision of 30.10.2026)
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    data = pdf.generate_report_pdf(RESULT)
    assert b"DSGVO" not in data and b"Server in Deutschland" in data  # parentheses are escaped in the PDF
