"""4-page PDF report generator (reportlab).

Structure
─────────
Page 1  Cover         Workplace, date, REBA-Score (large, traffic-light colour)
Page 2  Movements     Table: %, min/shift, 8 h extrapolation
Page 3  Body regions  Table: REBA subscore + traffic-light indicator
Page 4  Action fields CRITICAL (red border) then MEDIUM (yellow border)
Footer  (every page)  "Erstellt durch Motavi · DSGVO-konform · EU-Server (europe-west3)"
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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

# ── Brand colours ─────────────────────────────────────────────────────────────
_ACCENT   = colors.HexColor("#e63946")
_DATA     = colors.HexColor("#00b4d8")
_NEUTRAL  = colors.HexColor("#f4f4f6")
_DARK     = colors.HexColor("#1a2744")
_DARKEST  = colors.HexColor("#0f1830")
_LINE     = colors.HexColor("#1a2744")
_GREEN    = colors.HexColor("#22c55e")
_YELLOW   = colors.HexColor("#eab308")
_GREY_TXT = colors.HexColor("#888899")
# Page background: the report is designed dark (light text, dark tables);
# without it title, meta values and notes were white on white.
_PAGE_BG  = colors.HexColor("#0a0f1e")

_PAGE_W, _PAGE_H = A4
_CONTENT_W = _PAGE_W - 4 * cm  # left+right margin = 2 cm each


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reba_colour(score: float) -> colors.HexColor:
    if score <= 4:
        return _GREEN
    if score <= 6:
        return _YELLOW
    return _ACCENT


def _region_colour(normalised: float) -> colors.HexColor:
    """normalised is already on the 1-10 REBA scale."""
    return _reba_colour(normalised)


def _footer(canvas, doc):
    """Page background and footer; called when a page begins, before its content."""
    canvas.saveState()
    canvas.setFillColor(_PAGE_BG)
    canvas.rect(0, 0, _PAGE_W, _PAGE_H, stroke=0, fill=1)
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.5 * cm, _PAGE_W - 2 * cm, 1.5 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_GREY_TXT)
    canvas.drawCentredString(
        _PAGE_W / 2, 1.1 * cm,
        "Erstellt durch Motavi · DSGVO-konform · EU-Server (europe-west3)",
    )
    canvas.drawRightString(_PAGE_W - 2 * cm, 1.1 * cm, f"Seite {doc.page}")
    canvas.restoreState()


# ── Style factory ─────────────────────────────────────────────────────────────

def _styles():
    base = getSampleStyleSheet()

    def mk(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "title": mk(
            "MTitle",
            fontName="Helvetica-Bold", fontSize=32, leading=38,
            textColor=colors.white, alignment=TA_CENTER, spaceAfter=4,
        ),
        "subtitle": mk(
            "MSub",
            fontName="Helvetica", fontSize=13,
            textColor=_NEUTRAL, alignment=TA_CENTER, spaceAfter=6,
        ),
        "meta_key": mk(
            "MMetaK",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=_DATA,
        ),
        "meta_val": mk(
            "MMetaV",
            fontName="Helvetica", fontSize=10,
            textColor=_NEUTRAL,
        ),
        "section": mk(
            "MSection",
            fontName="Helvetica-Bold", fontSize=13,
            textColor=_DATA, spaceBefore=10, spaceAfter=6,
        ),
        "body": mk(
            "MBody",
            fontName="Helvetica", fontSize=9.5,
            textColor=_NEUTRAL, spaceAfter=4,
        ),
        "note": mk(
            "MNote",
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=_GREY_TXT, alignment=TA_CENTER, spaceAfter=4,
        ),
        "critical_hdr": mk(
            "MCritHdr",
            fontName="Helvetica-Bold", fontSize=11,
            textColor=_ACCENT, spaceBefore=10, spaceAfter=5,
        ),
        "medium_hdr": mk(
            "MMedHdr",
            fontName="Helvetica-Bold", fontSize=11,
            textColor=_YELLOW, spaceBefore=10, spaceAfter=5,
        ),
        "disclaimer": mk(
            "MDisc",
            fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=_GREY_TXT, alignment=TA_CENTER,
        ),
    }


# ── Table style helper ────────────────────────────────────────────────────────

def _base_table_style(header_bg=_DARK):
    return TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  header_bg),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  _DATA),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9.5),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR",     (0, 1), (-1, -1), _NEUTRAL),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_DARKEST, colors.HexColor("#111828")]),
        ("GRID",          (0, 0), (-1, -1), 0.25, _LINE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
    ])


# ── Public entry point ────────────────────────────────────────────────────────

def generate_report_pdf(result: dict) -> bytes:
    """Build the 4-page PDF and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )
    S = _styles()
    story = []

    reba_score = float(result.get("reba_score", 0))
    reba_level = result.get("reba_level", "UNKNOWN")
    job_id     = result.get("job_id", "")
    shift_min  = int(result.get("shift_duration_min", 480))
    now_str    = datetime.now().strftime("%d.%m.%Y %H:%M")
    reba_col   = _reba_colour(reba_score)

    _level_label = {
        "LOW":       "NIEDRIG — Geringes Risiko",
        "MEDIUM":    "MITTEL — Ergonomische Maßnahmen empfohlen",
        "HIGH":      "HOCH — Korrekturmaßnahmen erforderlich",
        "VERY_HIGH": "SEHR HOCH — Sofortiger Handlungsbedarf",
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Page 1 — Cover
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.8 * cm))
    story.append(Paragraph("MOTAVI", S["title"]))
    story.append(Paragraph("Ergonomie-Analysebericht", S["subtitle"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width=_CONTENT_W, color=_DATA, thickness=1))
    story.append(Spacer(1, 0.8 * cm))

    meta_rows = [
        [Paragraph("Analyse-ID:",    S["meta_key"]), Paragraph(job_id[:8] + "…", S["meta_val"])],
        [Paragraph("Erstellt:",      S["meta_key"]), Paragraph(now_str,           S["meta_val"])],
        [Paragraph("Schichtdauer:",  S["meta_key"]), Paragraph(f"{shift_min} min",S["meta_val"])],
    ]
    meta_tbl = Table(meta_rows, colWidths=[4.5 * cm, _CONTENT_W - 4.5 * cm])
    meta_tbl.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 1.2 * cm))

    # Big REBA score
    score_style = ParagraphStyle(
        "BigScore", parent=getSampleStyleSheet()["Normal"],
        fontName="Helvetica-Bold", fontSize=80,
        textColor=reba_col, alignment=TA_CENTER, leading=90,
    )
    level_style = ParagraphStyle(
        "LvlStyle", parent=getSampleStyleSheet()["Normal"],
        fontName="Helvetica-Bold", fontSize=15,
        textColor=reba_col, alignment=TA_CENTER, spaceAfter=8,
    )
    story.append(Paragraph("REBA-SCORE", S["subtitle"]))
    story.append(Paragraph(str(round(reba_score, 1)), score_style))
    story.append(Paragraph(_level_label.get(reba_level, reba_level), level_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width=_CONTENT_W, color=_LINE, thickness=0.4))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # Page 2 — Movement breakdown
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Bewegungsanteile", S["section"]))
    story.append(HRFlowable(width=_CONTENT_W, color=_DATA, thickness=0.5))
    story.append(Spacer(1, 0.4 * cm))

    movements = result.get("movements", {})
    _move_labels = {
        "bending":  "Bücken (Rumpfbeugen)",
        "overhead": "Überkopfarbeit",
        "neutral":  "Schulter neutral",
    }
    move_rows = [["Bewegungsklasse", "Anteil (%)", "Min. / Schicht", "Hochrechnung 8 h"]]
    for key, label in _move_labels.items():
        mv      = movements.get(key, {})
        pct     = mv.get("pct", 0)
        mins    = mv.get("minutes", 0)
        extrap  = round(pct / 100 * 480, 0)
        move_rows.append([label, f"{pct:.1f} %", f"{mins:.0f} min", f"{extrap:.0f} min"])

    cw = _CONTENT_W
    move_tbl = Table(
        move_rows,
        colWidths=[cw * 0.38, cw * 0.18, cw * 0.22, cw * 0.22],
    )
    move_tbl.setStyle(_base_table_style())
    story.append(move_tbl)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Hochrechnung auf 8-Stunden-Standardschicht. "
        f"Analysierte Dauer: {shift_min} Minuten.",
        S["body"],
    ))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # Page 3 — Body region subscores
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Körperregionen — REBA-Subscores", S["section"]))
    story.append(HRFlowable(width=_CONTENT_W, color=_DATA, thickness=0.5))
    story.append(Spacer(1, 0.4 * cm))

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
    _risk_label = {True: ("Gering", _GREEN), False: ("Mittel/Hoch", _ACCENT)}

    reg_rows  = [["Körperregion", "Subscore (1–10)", "Risikostufe"]]
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

        reg_rows.append([label, f"{norm:.1f}", risk_txt])
        reg_style_overrides += [
            ("TEXTCOLOR", (2, row_i), (2, row_i), rc),
            ("FONTNAME",  (2, row_i), (2, row_i), "Helvetica-Bold"),
        ]

    reg_tbl = Table(
        reg_rows,
        colWidths=[_CONTENT_W * 0.50, _CONTENT_W * 0.28, _CONTENT_W * 0.22],
    )
    ts = _base_table_style()
    for cmd in reg_style_overrides:
        ts.add(*cmd)
    reg_tbl.setStyle(ts)
    story.append(reg_tbl)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Subscores normiert auf REBA-Skala 1–10.  "
        "Ampel: Gering ≤ 4 | Mittel 5–6 | Hoch ≥ 7.",
        S["body"],
    ))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # Page 4 — Action fields
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Handlungsfelder & Maßnahmen", S["section"]))
    story.append(HRFlowable(width=_CONTENT_W, color=_DATA, thickness=0.5))
    story.append(Spacer(1, 0.4 * cm))

    action_items = result.get("action_items", [])
    critical = [a for a in action_items if a.get("priority") == "CRITICAL"]
    medium   = [a for a in action_items if a.get("priority") == "MEDIUM"]

    def _action_block(items, hdr_text, hdr_style, border_col):
        if not items:
            return
        story.append(Paragraph(hdr_text, hdr_style))
        for item in items:
            region    = item.get("region", "—")
            text      = item.get("text", "")
            reduction = item.get("reduction_pct")
            red_str   = f"−{reduction} %" if reduction else "—"

            region_p = Paragraph(
                f"<b>{region}</b>",
                ParagraphStyle("AR", parent=getSampleStyleSheet()["Normal"],
                               fontName="Helvetica-Bold", fontSize=9.5, textColor=border_col),
            )
            text_p = Paragraph(
                text,
                ParagraphStyle("AT", parent=getSampleStyleSheet()["Normal"],
                               fontName="Helvetica", fontSize=9.5, textColor=_NEUTRAL),
            )
            red_p = Paragraph(
                red_str,
                ParagraphStyle("AP", parent=getSampleStyleSheet()["Normal"],
                               fontName="Helvetica-Bold", fontSize=9.5,
                               textColor=_GREEN, alignment=TA_CENTER),
            )
            t = Table(
                [[region_p, text_p, red_p]],
                colWidths=[3.9 * cm, _CONTENT_W - 6.7 * cm, 2.8 * cm],  # "Lendenwirbelsäule" in one line
            )
            t.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND",   (0, 0), (-1, -1), _DARKEST),
                ("LEFTPADDING",  (0, 0), (0, -1),  8),
                ("RIGHTPADDING", (-1, 0), (-1, -1), 8),
                ("LINEAFTER",    (0, 0), (0, -1),  2, border_col),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
                ("TOPPADDING",   (0, 0), (-1, -1), 10),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.15 * cm))

    if not critical and not medium:
        story.append(Paragraph(
            "Keine kritischen Handlungsfelder. Ergonomische Situation ist zufriedenstellend.",
            S["body"],
        ))
    else:
        _action_block(critical, "KRITISCH — Sofortiger Handlungsbedarf", S["critical_hdr"], _ACCENT)
        _action_block(medium,   "MITTEL — Empfohlene Maßnahmen",          S["medium_hdr"],   _YELLOW)

    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width=_CONTENT_W, color=_LINE, thickness=0.4))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Dieser Bericht wurde automatisch durch die Motavi Ergonomie-KI erstellt. "
        "Die Ergebnisse ersetzen keine fachkundige ergonomische Beurteilung vor Ort.",
        S["disclaimer"],
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.read()
