"""PDF Steckbrief, 2 pages (STECKBRIEF_MODUL §6.2), complements the 4-page report.

Page 1  recommendation, reasons, both scores, automation type, key metrics
Page 2  process steps, reach and heights, economics, notes

Print-friendly data sheet on white. All four recommendations share one
colour: they are equal results, none is "good" or "bad".
"""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .texte import euro, prozent, zahl

INK = colors.HexColor("#1a2744")
MUTED = colors.HexColor("#5b6478")
LINE = colors.HexColor("#d9dde5")
SUBTLE = colors.HexColor("#f2f4f7")
DATA = colors.HexColor("#0077b6")
DATA_MID = colors.HexColor("#7cc4e4")
WASTE = colors.HexColor("#c8102e")
KLASSE_FARBE = {"wertschoepfend": DATA, "notwendig": DATA_MID, "verschwendung": WASTE}
KLASSE_TEXT = {"wertschoepfend": "wertschöpfend", "notwendig": "notwendig", "verschwendung": "Verschwendung"}
ZONE_TEXT = {"ueber_schulter": "über Schulter", "huefte_schulter": "Hüfte bis Schulter", "knie_huefte": "Knie bis Hüfte", "unter_knie": "unter Knie"}
NB = "nicht belastbar messbar"

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm
FRAME_PAD = 6  # reportlab's default frame padding
W = PAGE_W - 2 * MARGIN - 2 * FRAME_PAD


def _styles() -> dict[str, ParagraphStyle]:
    def mk(name, **kw):
        base = dict(fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "kicker": mk("kicker", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=MUTED),
        "titel": mk("titel", fontName="Helvetica-Bold", fontSize=17, leading=21),
        "meta": mk("meta", fontSize=8, leading=10, textColor=MUTED),
        "empfehlung": mk("empfehlung", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.white),
        "auf_dunkel": mk("auf_dunkel", fontSize=9.5, leading=13, textColor=colors.white),
        "auf_dunkel_klein": mk("auf_dunkel_klein", fontSize=7.5, leading=10, textColor=colors.HexColor("#c9d2e3")),
        "h2": mk("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=10, spaceAfter=5),
        "body": mk("body"),
        "klein": mk("klein", fontSize=7.5, leading=10, textColor=MUTED),
        "zelle": mk("zelle", fontSize=8.5, leading=11),
        "zelle_r": mk("zelle_r", fontSize=8.5, leading=11, alignment=2),
        "wert_gross": mk("wert_gross", fontName="Helvetica-Bold", fontSize=13, leading=16),
        "pflicht": mk("pflicht", fontName="Helvetica-Bold", fontSize=8.5, leading=11),
        "vorrang": mk("vorrang", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white),
    }


def _datum(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except ValueError:
        return iso[:10]


def _k(k: dict | None, fmt) -> str:
    if not k or not k.get("belastbar") or k.get("wert") is None:
        return NB
    return fmt(k["wert"])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN + FRAME_PAD, 1.3 * cm, PAGE_W - MARGIN - FRAME_PAD, 1.3 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN + FRAME_PAD, 0.9 * cm, "Motavi Arbeitsplatz-Steckbrief · Pilotphase · keine Personendaten, nur der Arbeitsplatz")
    canvas.drawRightString(PAGE_W - MARGIN - FRAME_PAD, 0.9 * cm, f"Seite {doc.page} von 2")
    canvas.restoreState()


# ── drawings ─────────────────────────────────────────────────────────────────


def _score_balken(name: str, wert: int | None, schwelle: float, hoch: str) -> Drawing:
    """Bar 0 to 100 with the threshold mark."""
    bw, h = W - 4.6 * cm, 30
    d = Drawing(W, h)
    d.add(String(0, 17, name, fontName="Helvetica-Bold", fontSize=9, fillColor=INK))
    d.add(String(0, 5, f"hoch ab {zahl(schwelle)}: {hoch}", fontName="Helvetica", fontSize=7, fillColor=MUTED))
    x0 = 4.6 * cm
    d.add(Rect(x0, 8, bw, 10, fillColor=SUBTLE, strokeColor=None))
    if wert is not None:
        d.add(Rect(x0, 8, bw * wert / 100, 10, fillColor=INK, strokeColor=None))
    xs = x0 + bw * schwelle / 100
    d.add(Line(xs, 4, xs, 22, strokeColor=WASTE, strokeWidth=1.2))
    d.add(String(xs + 2, 22, zahl(schwelle), fontName="Helvetica", fontSize=6.5, fillColor=WASTE))
    label = NB if wert is None else str(wert)
    d.add(String(W, 22, label, fontName="Helvetica-Bold", fontSize=11 if wert is not None else 7.5, fillColor=INK, textAnchor="end"))
    return d


def _ablauf_balken(schritte: list[dict]) -> Drawing:
    h = 34
    d = Drawing(W, h)
    x = 0.0
    for s in schritte:
        w = W * s["anteil"]
        d.add(Rect(x, 14, w, 16, fillColor=KLASSE_FARBE[s["klasse"]], strokeColor=colors.white, strokeWidth=1))
        if w > 34:
            txt_col = colors.white if s["klasse"] != "notwendig" else INK
            d.add(String(x + 3, 19, s["typ"], fontName="Helvetica", fontSize=7, fillColor=txt_col))
        x += w
    # legend
    lx = 0.0
    for k in ("wertschoepfend", "notwendig", "verschwendung"):
        d.add(Rect(lx, 1, 7, 7, fillColor=KLASSE_FARBE[k], strokeColor=None))
        d.add(String(lx + 10, 1.5, KLASSE_TEXT[k], fontName="Helvetica", fontSize=7, fillColor=MUTED))
        lx += 80
    return d


def _zonen(zonen: dict, breite: float) -> Drawing:
    rows = ["ueber_schulter", "huefte_schulter", "knie_huefte", "unter_knie"]
    h = 4 * 16
    d = Drawing(breite, h)
    bw = breite - 4.2 * cm
    for i, z in enumerate(rows):
        y = h - (i + 1) * 16 + 3
        d.add(String(0, y + 2, ZONE_TEXT[z], fontName="Helvetica", fontSize=8, fillColor=INK))
        k = zonen.get(z) or {}
        d.add(Rect(3.2 * cm, y, bw, 9, fillColor=SUBTLE, strokeColor=None))
        if k.get("belastbar") and k.get("wert") is not None:
            col = DATA if z == "huefte_schulter" else DATA_MID
            d.add(Rect(3.2 * cm, y, bw * k["wert"], 9, fillColor=col, strokeColor=None))
            d.add(String(breite, y + 2, prozent(k["wert"]), fontName="Helvetica-Bold", fontSize=8, fillColor=INK, textAnchor="end"))
        else:
            d.add(String(breite, y + 2, NB, fontName="Helvetica", fontSize=7, fillColor=MUTED, textAnchor="end"))
    return d


# ── tables ───────────────────────────────────────────────────────────────────


def _tabelle(rows: list[list], st: dict, widths: list[float], kopf: bool = False) -> Table:
    data = [[Paragraph(str(c), st["zelle_r"] if j == len(r) - 1 and j else st["zelle"]) for j, c in enumerate(r)] for r in rows]
    t = Table(data, colWidths=widths)
    style = [
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if kopf:
        style += [("LINEBELOW", (0, 0), (-1, 0), 0.8, INK), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def _zwei_spalten(links: list, rechts: list, gap: float = 0.8 * cm) -> Table:
    half = (W - gap) / 2
    t = Table([[links, "", rechts]], colWidths=[half, gap, half])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


# ── pages ────────────────────────────────────────────────────────────────────


def _seite1(doc: dict, st: dict) -> list:
    e = doc["empfehlung"]
    out: list = [
        Paragraph("ARBEITSPLATZ-STECKBRIEF", st["kicker"]),
        Spacer(1, 2),
        Paragraph(doc.get("arbeitsplatz") or "", st["titel"]),
        Paragraph(f"Erstellt am {_datum(doc.get('erstellt_am'))} · Analyse {doc['job_id'][:8]}", st["meta"]),
        Spacer(1, 10),
    ]

    # recommendation block
    if e["status"] == "bestaetigt":
        status = f"Vom Experten bestätigt am {_datum(e.get('bestaetigt_am'))}"
        if e.get("geaendert"):
            status += f" (Vorschlag des Tools: {e['vorschlag_text']})"
    else:
        status = "Vorschlag des Tools, noch nicht vom Experten bestätigt"
        if e.get("vorlaeufig"):
            status += "; vorläufig, weil Angaben fehlen"
    inner = [
        Paragraph("EMPFEHLUNG", st["auf_dunkel_klein"]),
        Spacer(1, 3),
        Paragraph(e["text"], st["empfehlung"]),
        Spacer(1, 4),
    ]
    if e.get("erklaerung"):
        inner.append(Paragraph(e["erklaerung"], st["auf_dunkel"]))
    inner += [Spacer(1, 6), Paragraph(status, st["auf_dunkel_klein"])]
    box = Table([[inner]], colWidths=[W])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    out.append(box)
    if e.get("vorrangig"):
        badge = Table([[Paragraph(f"{e['vorrang_text']} ({e['vorrang_grund']})", st["vorrang"])]], colWidths=[W])
        badge.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WASTE), ("LEFTPADDING", (0, 0), (-1, -1), 14),
                                   ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        out.append(badge)

    if e.get("gruende"):
        out += [Paragraph("Ausschlaggebend", st["h2"])]
        out += [Paragraph(f"•&nbsp;&nbsp;{g}", st["body"]) for g in e["gruende"]]

    out.append(Paragraph("Bewertung", st["h2"]))
    v, a = doc["verbesserungs_score"], doc["automatisierungs_score"]
    sv = doc.get("_schwellen", (50, 60))
    out += [
        _score_balken("Verbesserungs-Score", v["wert"], sv[0], "Verbessern lohnt sich"),
        Spacer(1, 4),
        _score_balken("Automatisierungs-Score", a["wert"], sv[1], "Automatisieren lohnt sich"),
    ]
    fehlend = sorted(set(v.get("fehlend", []) + a.get("fehlend", [])))
    if fehlend:
        out.append(Paragraph(f"Ohne Wert, Gewicht auf die übrigen Kriterien verteilt: {', '.join(fehlend)}.", st["klein"]))

    t = doc["automatisierungstyp"]
    if e.get("mit_automatisierung"):
        out.append(Paragraph("Automatisierungstyp", st["h2"]))
        txt = t["name"] or t["text"]
        if t.get("geaendert") and t.get("vorschlag"):
            txt += f" (Vorschlag des Tools: {t['vorschlag']})"
        out.append(Paragraph(f"<b>{txt}</b>", st["body"]))
        out.append(Paragraph("Nur der Typ, keine Herstellerempfehlung.", st["klein"]))

    z, b = doc["zyklen"], doc["belastung"]
    s1 = lambda x: zahl(x, 1)  # noqa: E731
    zyklus_rows = [
        ["Zyklus", ""],
        ["Zykluszeit (Median)", _k(z.get("zykluszeit_median_s"), lambda x: f"{s1(x)} s")],
        ["Schwankung (Variationskoeffizient)", _k(z.get("zykluszeit_vk"), prozent)],
        ["Zyklen pro Schicht", _k(z.get("zyklen_pro_schicht"), zahl)],
        ["Zeitanteil in Zyklen", _k(z.get("zeitanteil_in_zyklen"), prozent)],
        ["Erkannte Zyklen im Video", str(z.get("anzahl_gueltig", 0)) if z["erkannt"] else (z.get("hinweis") or "keine")],
    ]
    belastung_rows = [
        ["Belastung", ""],
        ["Haltungsindex Mittelwert (1 bis 10)", _k(b.get("reba_mittel"), s1)],
        ["Haltungsindex Maximum", _k(b.get("reba_max"), s1)],
        ["Zeitanteil Bücken", _k(b.get("buecken_anteil"), prozent)],
        ["Zeitanteil Überkopf", _k(b.get("ueberkopf_anteil"), prozent)],
        ["Zeitanteil Drehung", _k(b.get("drehung_anteil"), prozent)],
        ["Drehungen pro Zyklus", _k(b.get("drehungen_pro_zyklus"), s1)],
    ]
    half = (W - 0.8 * cm) / 2
    out += [
        Paragraph("Kennzahlen", st["h2"]),
        _zwei_spalten(
            [_tabelle(zyklus_rows, st, [half * 0.62, half * 0.38], kopf=True)],
            [_tabelle(belastung_rows, st, [half * 0.62, half * 0.38], kopf=True)],
        ),
        Spacer(1, 6),
        Paragraph(
            "Pilotphase: Zyklen, Ablaufschritte, Greifraum, Drehung und Haltungsindex (auf REBA-Basis, kein REBA-Wert) sind noch nicht gegen manuelle Messungen und Bewertungen validiert. "
            "„nicht belastbar messbar“ steht, wo die Messqualität unter der Schwelle liegt.",
            st["klein"],
        ),
    ]
    return out


def _seite2(doc: dict, st: dict) -> list:
    out: list = [Paragraph("Ablaufschritte im Zyklus", st["h2"])]
    ab = doc["ablauf"]
    if ab["bestaetigt"] and ab.get("ablaufschritte"):
        out += [_ablauf_balken(ab["ablaufschritte"]), Spacer(1, 6)]
        rows = [["Schritt", "Einstufung", "Sekunden je Zyklus", "Anteil"]]
        rows += [[s["typ"], KLASSE_TEXT[s["klasse"]], zahl(s["dauer_s"], 1), prozent(s["anteil"])] for s in ab["ablaufschritte"]]
        out.append(_tabelle(rows, st, [W * 0.3, W * 0.3, W * 0.22, W * 0.18], kopf=True))
        an, mn = ab["anteile_ablauf"], ab.get("minuten_pro_schicht") or {}
        summe = " · ".join(
            f"{KLASSE_TEXT[k]} {prozent(an[k])}" + (f" ({zahl(mn[k])} min pro Schicht)" if mn.get(k) is not None else "")
            for k in ("wertschoepfend", "notwendig", "verschwendung")
        )
        out += [Spacer(1, 3), Paragraph(summe, st["body"])]
        if ab.get("bestaetigt_am"):
            out.append(Paragraph(f"Ablaufschritte vom Experten bestätigt am {_datum(ab['bestaetigt_am'])}, auf alle gültigen Zyklen übertragen.", st["klein"]))
    else:
        out.append(Paragraph("Die Ablaufschritte sind noch nicht vom Experten bestätigt. Ohne sie fehlt die Verschwendung in der Bewertung.", st["body"]))

    # reach
    g = doc.get("greifraum")
    half = (W - 0.8 * cm) / 2
    if g:
        links = [Paragraph("Arbeitshöhen der Hände", st["h2"]), _zonen(g["hoehenzonen"], half)]
        ga = g.get("griffe_ausserhalb") or {}
        rechts = [
            Paragraph("Greifraum", st["h2"]),
            Paragraph(_k(ga, prozent), st["wert_gross"]),
            Paragraph("der Griffe außerhalb des günstigen Greifraums (Hüfte bis Schulter, körpernah)", st["body"]),
            Spacer(1, 4),
            Paragraph(f"{g.get('anzahl_griffe', 0)} Griffe erkannt. {g.get('hinweis', '')}", st["klein"]),
        ]
        out.append(_zwei_spalten(links, rechts))

    # economics
    w = doc["wirtschaftlichkeit"]
    wv, wa = w["verbessern"], w["automatisieren"]
    out.append(Paragraph("Wirtschaftlichkeit", st["h2"]))
    links: list = [Paragraph("<b>Verbessern</b>", st["body"])]
    if wv.get("berechnet"):
        rows = [
            ["Verschwendung pro Schicht", f"{zahl(wv['verschwendung_min_schicht'])} min"],
            ["davon vermeidbar", f"{zahl(wv['verbesserung_min_schicht'])} min"],
            ["Wert pro Jahr", euro(wv["euro_jahr"]) if wv.get("euro_jahr") is not None else "Angaben fehlen"],
        ]
        links.append(_tabelle(rows, st, [half * 0.6, half * 0.4]))
        if wv.get("fehlende_angaben"):
            links.append(Paragraph(f"Für Euro fehlt: {', '.join(wv['fehlende_angaben'])}.", st["klein"]))
    else:
        links.append(Paragraph(wv.get("grund", ""), st["klein"]))
    rechts: list = [Paragraph("<b>Automatisieren</b>", st["body"])]
    if wa.get("berechnet"):
        rng = lambda r, f: "Angaben fehlen" if r is None else f"{f(r[0])} bis {f(r[1])}"  # noqa: E731
        rows = [
            ["Typ", wa["typ"]],
            ["Grundlage", f"{wa['basis']}, {zahl(wa['zykluszeit_basis_s'], 1)} s je Zyklus"],
            ["Stunden pro Jahr", rng(wa.get("stunden_jahr"), zahl)],
            ["Ersparnis brutto", rng(wa.get("euro_jahr_brutto"), euro)],
            ["Betriebskosten", rng(wa.get("betriebskosten_anteil"), prozent)],
            ["Ersparnis netto", rng(wa.get("euro_jahr_netto"), euro)],
            ["Investition", f"{rng(wa['investition_euro'], euro)} ({wa['investition_quelle']})"],
            ["Amortisation", rng(wa.get("amortisation_jahre"), lambda x: zahl(x, 1)) + (" Jahre" if wa.get("amortisation_jahre") else "")],
        ]
        rechts.append(_tabelle(rows, st, [half * 0.38, half * 0.62]))
    else:
        rechts.append(Paragraph(wa.get("grund", ""), st["klein"]))
    out += [_zwei_spalten(links, rechts), Spacer(1, 6), Paragraph(w["hinweis"], st["pflicht"])]

    hinweise = doc.get("hinweise") or []
    if hinweise:
        out.append(KeepTogether([Paragraph("Hinweise", st["h2"]), *[Paragraph(f"•&nbsp;&nbsp;{h}", st["klein"]) for h in hinweise]]))
    return out


def generate(doc: dict, schwellen: tuple[float, float] = (50, 60)) -> bytes:
    """PDF bytes of the Steckbrief dict (steckbrief.build)."""
    st = _styles()
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=1.5 * cm, bottomMargin=1.8 * cm,
        title=f"Arbeitsplatz-Steckbrief {doc.get('arbeitsplatz', '')}", author="Motavi",
    )
    d = {**doc, "_schwellen": schwellen}
    pdf.build([*_seite1(d, st), PageBreak(), *_seite2(d, st)], onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
