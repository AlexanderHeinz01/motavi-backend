"""4-page PDF report generator (reportlab).

Structure
─────────
Page 1  Cover         Workplace, date, posture index based on REBA (large, traffic-light colour)
Page 2  Movements     Table: %, min/shift, 8 h extrapolation
Page 3  Body regions  Table: region score + traffic-light indicator
Page 4  Action fields CRITICAL (red bar) then MEDIUM (amber bar)
Footer  (every page)  "Erstellt durch Motavi · Analyse auf Servern in Deutschland (Frankfurt)"

Print-friendly data sheet on white, like the 2-page Steckbrief
(workplace/pdf_steckbrief.py), German number format (decimal comma).
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Colours (same palette as the Steckbrief PDF) ──────────────────────────────
_INK      = colors.HexColor("#1a2744")
_MUTED    = colors.HexColor("#5b6478")
_LINE     = colors.HexColor("#d9dde5")
_SUBTLE   = colors.HexColor("#f2f4f7")
_DATA     = colors.HexColor("#0077b6")
# traffic light, dark enough for white paper (at least 4.5:1)
_RED      = colors.HexColor("#c8102e")
_AMBER    = colors.HexColor("#a15c00")
_GREEN    = colors.HexColor("#15803d")
_PAGE_BG  = colors.white

_PAGE_W, _PAGE_H = A4
_MARGIN = 2 * cm
_FRAME_PAD = 6  # reportlab's default frame padding
_CONTENT_W = _PAGE_W - 2 * _MARGIN - 2 * _FRAME_PAD
_SEITEN = 4


# ── Helpers ───────────────────────────────────────────────────────────────────

def _de(x: float, nd: int = 1) -> str:
    """German number format: decimal comma, dot for thousands."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# Levels of the posture index based on REBA (1 to 10), the same everywhere
# (docs/HALTUNGSINDEX.md; analyzer.stufe, website src/lib/steckbrief.ts,
# dashboard frontend/src/lib/rebaStufe.ts).
REBA_STUFEN = (
    # (index below, level, action, colour)
    (4.0, "Niedrig", "derzeit kein Handlungsbedarf", _GREEN),
    (6.0, "Mittel", "Gestaltung prüfen", _AMBER),
    (8.0, "Hoch", "Gestaltung bald verbessern", _RED),
    (float("inf"), "Sehr hoch", "Gestaltung vorrangig verbessern", _RED),
)


def reba_stufe(score: float) -> tuple[str, str, colors.HexColor]:
    """(level, action, colour) of a posture index."""
    for grenze, stufe, massnahme, farbe in REBA_STUFEN:
        if score < grenze:
            return stufe, massnahme, farbe
    raise AssertionError("unreachable")


def _region_colour(normalised: float) -> colors.HexColor:
    """Traffic light of the normalised body region subscore (1 to 10 scale)."""
    if normalised <= 4:
        return _GREEN
    if normalised <= 6:
        return _AMBER
    return _RED


def _footer(canvas, doc):
    """Footer of every page; called when a page begins, before its content."""
    canvas.saveState()
    canvas.setFillColor(_PAGE_BG)
    canvas.rect(0, 0, _PAGE_W, _PAGE_H, stroke=0, fill=1)
    x0, x1 = _MARGIN + _FRAME_PAD, _PAGE_W - _MARGIN - _FRAME_PAD
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(x0, 1.5 * cm, x1, 1.5 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawString(x0, 1.1 * cm, "Erstellt durch Motavi · Analyse auf Servern in Deutschland (Frankfurt)")
    canvas.drawRightString(x1, 1.1 * cm, f"Seite {doc.page} von {_SEITEN}")
    canvas.restoreState()


# ── Style factory ─────────────────────────────────────────────────────────────

def _styles():
    def mk(name, **kw):
        base = dict(fontName="Helvetica", fontSize=9.5, leading=13, textColor=_INK)
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "kicker": mk("MKicker", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=_MUTED),
        "title": mk("MTitle", fontName="Helvetica-Bold", fontSize=24, leading=29, spaceAfter=2),
        "subtitle": mk("MSub", fontSize=10, leading=13, textColor=_MUTED),
        "meta_key": mk("MMetaK", fontName="Helvetica-Bold", fontSize=9.5, textColor=_MUTED),
        "meta_val": mk("MMetaV", fontSize=9.5),
        "section": mk("MSection", fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=4, spaceAfter=6),
        "body": mk("MBody", spaceAfter=4),
        "note": mk("MNote", fontSize=8, leading=11, textColor=_MUTED),
        "cell": mk("MCell", fontSize=9.5),
        "cell_r": mk("MCellR", fontSize=9.5, alignment=TA_RIGHT),
        "head": mk("MHead", fontName="Helvetica-Bold", fontSize=9, textColor=_INK),
        "head_r": mk("MHeadR", fontName="Helvetica-Bold", fontSize=9, textColor=_INK, alignment=TA_RIGHT),
        "critical_hdr": mk("MCritHdr", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=_RED, spaceBefore=10, spaceAfter=5),
        "medium_hdr": mk("MMedHdr", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=_AMBER, spaceBefore=10, spaceAfter=5),
        "disclaimer": mk("MDisc", fontSize=8, leading=11, textColor=_MUTED),
    }


# ── Table helper ──────────────────────────────────────────────────────────────

def _table(rows: list[list[str]], widths: list[float], S: dict, extra: list | None = None) -> Table:
    """Data-sheet table: bold head with a dark rule, light row lines, numbers right-aligned."""
    data = []
    for i, row in enumerate(rows):
        cells = []
        for j, c in enumerate(row):
            if i == 0:
                st = S["head_r"] if j else S["head"]
            else:
                st = S["cell_r"] if j else S["cell"]
            cells.append(c if isinstance(c, Paragraph) else Paragraph(str(c), st))
        data.append(cells)
    t = Table(data, colWidths=widths)
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 1, _INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, _LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _SUBTLE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style + (extra or [])))
    return t


# ── Public entry point ────────────────────────────────────────────────────────

def generate_report_pdf(result: dict, ablauf: dict | None = None) -> bytes:
    """Build the 4-page PDF and return raw bytes.

    ablauf: cycle time and reach from the pose data (routers/report.py
    ablauf_kennzahlen), part of every package including the Video-Check
    (decision P1 on 31.10.2026); None when the pose data are gone.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=2 * cm,
        bottomMargin=2.2 * cm,
        title="Motavi Ergonomie-Analysebericht",
        author="Motavi",
    )
    S = _styles()
    story = []

    reba_score = float(result.get("reba_score", 0))
    job_id     = result.get("job_id", "")
    shift_min  = int(result.get("shift_duration_min", 480))
    now_str    = datetime.now().strftime("%d.%m.%Y, %H:%M Uhr")
    stufe, massnahme, reba_col = reba_stufe(reba_score)
    arbeitsplatz = " · ".join(result[k] for k in ("department", "task_description") if result.get(k))

    # ──────────────────────────────────────────────────────────────────────────
    # Page 1: cover
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("MOTAVI · ERGONOMIE-ANALYSEBERICHT", S["kicker"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(arbeitsplatz or "Ergonomie-Analyse", S["title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width=_CONTENT_W, color=_INK, thickness=1))
    story.append(Spacer(1, 0.4 * cm))

    meta_rows = [
        [Paragraph("Analyse-ID", S["meta_key"]), Paragraph(job_id[:8], S["meta_val"])],
        [Paragraph("Erstellt", S["meta_key"]), Paragraph(now_str, S["meta_val"])],
        [Paragraph("Analysierte Dauer", S["meta_key"]), Paragraph(f"{shift_min} min", S["meta_val"])],
    ]
    meta_tbl = Table(meta_rows, colWidths=[4.5 * cm, _CONTENT_W - 4.5 * cm])
    meta_tbl.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 1.4 * cm))

    # posture index block with a bar in the traffic-light colour
    score_style = ParagraphStyle("BigScore", fontName="Helvetica-Bold", fontSize=72, leading=78, textColor=reba_col)
    level_style = ParagraphStyle("LvlStyle", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=reba_col)
    block = Table(
        [[[
            Paragraph("HALTUNGSINDEX AUF REBA-BASIS (MITTELWERT, 1 BIS 10)", S["kicker"]),
            Spacer(1, 6),
            Paragraph(_de(reba_score), score_style),
            Spacer(1, 4),
            Paragraph(f"{stufe}: {massnahme}", level_style),
            Spacer(1, 8),
            Paragraph("Der Haltungsindex fasst die Haltung von Rumpf, Nacken, Oberarmen, Unterarmen und Knien nach den "
                      "Winkelbereichen von REBA (Rapid Entire Body Assessment) gewichtet zusammen, Skala 1 bis 10. "
                      "Er ist kein REBA-Wert: Last, Griffart und Handgelenke fließen nicht ein. "
                      "Stufen: unter 4 niedrig, 4 bis unter 6 mittel, 6 bis unter 8 hoch, ab 8 sehr hoch. "
                      "Pilotphase: noch nicht gegen manuelle Bewertungen geprüft.", S["note"]),
        ]]],
        colWidths=[_CONTENT_W],
    )
    block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _SUBTLE),
        ("LINEBEFORE", (0, 0), (0, -1), 5, reba_col),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(block)

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # Page 2: movement breakdown
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Bewegungsanteile", S["section"]))
    story.append(Spacer(1, 0.2 * cm))

    movements = result.get("movements", {})
    _move_labels = {
        "bending":  "Bücken (Rumpfbeugen)",
        "overhead": "Überkopfarbeit",
        "neutral":  "Schulter neutral",
    }
    move_rows = [["Bewegungsklasse", "Anteil", "Minuten pro Schicht"]]
    for key, label in _move_labels.items():
        mv      = movements.get(key, {})
        pct     = mv.get("pct", 0)
        mins    = mv.get("minutes", 0)
        move_rows.append([label, f"{_de(pct)} %", f"{_de(mins, 0)} min"])

    cw = _CONTENT_W
    story.append(_table(move_rows, [cw * 0.5, cw * 0.2, cw * 0.3], S))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Minuten hochgerechnet auf die Netto-Arbeitszeit je Schicht: {shift_min} Minuten.",
        S["note"],
    ))

    if ablauf:
        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph("Arbeitsablauf und Greifraum", S["section"]))
        story.append(Spacer(1, 0.2 * cm))

        def wert(v, fmt) -> str:
            return fmt(v) if v is not None else "nicht belastbar messbar"

        rows = [["Kennzahl", "Wert"],
                ["Zykluszeit (Median)", wert(ablauf.get("zykluszeit_s"), lambda v: f"{_de(v)} s")],
                ["Zyklen pro Schicht", wert(ablauf.get("zyklen_pro_schicht"), lambda v: _de(v, 0))],
                ["Griffe außerhalb des günstigen Greifraums", wert(ablauf.get("griffe_ausserhalb"), lambda v: f"{_de(v * 100, 0)} %")]]
        for name, text in ablauf.get("zonen_text", {}).items():
            rows.append([f"Handposition {text}", wert(ablauf.get("hoehenzonen", {}).get(name), lambda v: f"{_de(v * 100, 0)} %")])
        story.append(_table(rows, [cw * 0.62, cw * 0.38], S))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            "Pilotphase: automatisch gemessen, noch nicht gegen manuelle Messungen geprüft. "
            "Greifraum und Höhen sind relative Werte aus dem 2D-Video, bezogen auf die Körpermaße."
            + (f" {ablauf['hinweis']}" if ablauf.get("hinweis") else ""),
            S["note"],
        ))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # Page 3: body region subscores
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Körperregionen", S["section"]))
    story.append(Spacer(1, 0.2 * cm))

    body_regions = result.get("body_regions", {})
    _region_labels = {
        "lumbar":     "Lendenwirbelsäule",
        "shoulder_l": "Schulter links",
        "shoulder_r": "Schulter rechts",
        "neck":       "Nacken / HWS",
        "knee_l":     "Knie links",
        "knee_r":     "Knie rechts",
        "forearm":    "Unterarm",
    }
    _region_maxes = {
        "lumbar": 8.0, "shoulder_l": 7.2, "shoulder_r": 8.0,
        "neck": 6.5,   "knee_l": 6.175,   "knee_r": 6.5, "forearm": 4.5,
    }

    reg_rows  = [["Körperregion", "Subscore (1 bis 10)", "Risikostufe"]]
    reg_style_overrides = []

    for row_i, (key, label) in enumerate(_region_labels.items(), start=1):
        raw    = body_regions.get(key, 1.0)
        mx     = _region_maxes.get(key, 8.0)
        norm   = round(1.0 + (raw / mx) * 9.0, 1)
        rc     = _region_colour(norm)
        if norm <= 4:
            risk_txt = "Gering"
        elif norm <= 6:
            risk_txt = "Mittel"
        else:
            risk_txt = "Hoch"

        reg_rows.append([
            label, _de(norm),
            Paragraph(f'<font color="{rc.hexval().replace("0x", "#")}"><b>{risk_txt}</b></font>', S["cell_r"]),
        ])
        reg_style_overrides.append(("LINEAFTER", (2, row_i), (2, row_i), 3, rc))

    story.append(_table(reg_rows, [_CONTENT_W * 0.50, _CONTENT_W * 0.28, _CONTENT_W * 0.22], S, reg_style_overrides))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Werte je Körperregion auf die Skala 1 bis 10 umgerechnet. Ampel: gering bis 4, mittel über 4 bis 6, hoch über 6. Pilotphase.",
        S["note"],
    ))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # Page 4: action fields
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Handlungsfelder und Maßnahmen", S["section"]))
    story.append(Spacer(1, 0.2 * cm))

    action_items = result.get("action_items", [])
    critical = [a for a in action_items if a.get("priority") == "CRITICAL"]
    medium   = [a for a in action_items if a.get("priority") == "MEDIUM"]

    def _action_block(items, hdr_text, hdr_style, bar_col):
        if not items:
            return
        story.append(Paragraph(hdr_text, hdr_style))
        for item in items:
            region    = item.get("region", "")
            text      = item.get("text", "")

            t = Table(
                [[
                    Paragraph(f"<b>{region}</b>", S["cell"]),
                    Paragraph(text, S["cell"]),
                ]],
                colWidths=[3.9 * cm, _CONTENT_W - 3.9 * cm],  # "Lendenwirbelsäule" in one line
            )
            t.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND",    (0, 0), (-1, -1), _SUBTLE),
                ("LINEBEFORE",    (0, 0), (0, -1), 4, bar_col),
                ("LEFTPADDING",   (0, 0), (0, -1), 10),
                ("RIGHTPADDING",  (-1, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.15 * cm))

    if not critical and not medium:
        story.append(Paragraph(
            "Keine kritischen Handlungsfelder. Die ergonomische Situation ist zufriedenstellend.",
            S["body"],
        ))
    else:
        _action_block(critical, "Kritisch: sofortiger Handlungsbedarf", S["critical_hdr"], _RED)
        _action_block(medium,   "Mittel: empfohlene Maßnahmen",        S["medium_hdr"],   _AMBER)

    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width=_CONTENT_W, color=_LINE, thickness=0.5))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Dieser Bericht wurde automatisch aus dem Video erstellt (Pilotphase). "
        "Die Ergebnisse ersetzen keine fachkundige ergonomische Beurteilung vor Ort.",
        S["disclaimer"],
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.read()
