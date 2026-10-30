"""4-page ergonomics report: every text style readable on the page background."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.services import pdf

RESULT = json.loads((Path(__file__).parent / "golden" / "testvideo_result.json").read_text(encoding="utf-8"))


def _luminance(c) -> float:
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red) + 0.7152 * ch(c.green) + 0.0722 * ch(c.blue)


def contrast(a, b) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_every_page_gets_the_dark_background():
    canvas = MagicMock()
    pdf._footer(canvas, MagicMock(page=1))
    canvas.setFillColor.assert_any_call(pdf._PAGE_BG)
    x, y, w, h = canvas.rect.call_args_list[0].args
    assert (x, y, w, h) == (0, 0, pdf._PAGE_W, pdf._PAGE_H)
    assert canvas.rect.call_args_list[0].kwargs == {"stroke": 0, "fill": 1}


@pytest.mark.parametrize("name", ["title", "subtitle", "meta_key", "meta_val", "section", "body", "critical_hdr", "medium_hdr"])
def test_text_styles_readable_on_background(name):
    # WCAG AA for normal text: 4.5:1 (was white on white before the background)
    assert contrast(pdf._styles()[name].textColor, pdf._PAGE_BG) >= 4.5


def test_report_has_four_pages():
    import re
    data = pdf.generate_report_pdf(RESULT)
    assert len(re.findall(rb"/Type /Page[^s]", data)) == 4
