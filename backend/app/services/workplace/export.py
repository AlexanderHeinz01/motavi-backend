"""JSON export of the Steckbrief (STECKBRIEF_MODUL §6.3), format in
docs/steckbrief_schema.json.

Vendor-neutral and flat: the keys of the demo format (STECKBRIEF_MODUL §7)
at the top, values that are not reliably measurable are null and their
reason is in "qualitaet". No person data: the workplace only, no worker,
no e-mail address of the consultant.
"""
from __future__ import annotations

FORMAT = "motavi-arbeitsplatz-steckbrief"
SCHEMA_VERSION = "1.0"
PFLICHTHINWEIS = "Grobe Abschätzung, ersetzt kein Angebot."
HINWEIS_2D = "Relative Werte aus 2D-Video. Für Zentimeterangaben ist eine Referenzmessung vor Ort nötig."

# metrics without validation against manual measurements (STECKBRIEF_MODUL §8)
PILOTPHASE = [
    "zykluszeit_median_s", "zykluszeit_vk", "zyklen_pro_schicht", "zeitanteil_in_zyklen", "ablaufschritte",
    "hoehenzonen", "griffe_ausserhalb_greifraum", "drehung_anteil", "drehungen_pro_zyklus",
    "verbesserungs_score", "automatisierungs_score",
]

_KUNDE = (
    "teilegewicht_kg", "abmessungen_cm", "anzahl_varianten", "stueck_pro_schicht", "schichten_pro_tag",
    "schichtdauer_min", "arbeitstage_pro_jahr", "vollkosten_euro_pro_stunde", "besetzung_schwierigkeit", "investition_euro",
)


def _w(k: dict | None):
    return None if not k or not k.get("belastbar") else k.get("wert")


def _q(k: dict | None) -> dict | None:
    if not k:
        return None
    return {"belastbar": bool(k.get("belastbar")), "qualitaet": k.get("qualitaet", 0.0), "grund": k.get("grund")}


def to_export(doc: dict) -> dict:
    """Export document from the Steckbrief (steckbrief.build)."""
    e = doc["empfehlung"]
    z = doc["zyklen"]
    b = doc["belastung"]
    g = doc.get("greifraum") or {}
    zonen = g.get("hoehenzonen") or {}
    ab = doc["ablauf"]
    t = doc["automatisierungstyp"]
    w = doc["wirtschaftlichkeit"]
    wv, wa = w["verbessern"], w["automatisieren"]

    qualitaet = {
        "zykluszeit_median_s": _q(z.get("zykluszeit_median_s")),
        "zykluszeit_vk": _q(z.get("zykluszeit_vk")),
        "zyklen_pro_schicht": _q(z.get("zyklen_pro_schicht")),
        "zeitanteil_in_zyklen": _q(z.get("zeitanteil_in_zyklen")),
        "griffe_ausserhalb_greifraum": _q(g.get("griffe_ausserhalb")),
        **{f"hoehenzone_{name}": _q(k) for name, k in zonen.items()},
        **{key: _q(b.get(key)) for key in ("reba_mittel", "reba_max", "buecken_anteil", "ueberkopf_anteil", "drehung_anteil", "drehungen_pro_zyklus")},
    }
    automatisierung = None
    if wa.get("berechnet"):
        automatisierung = {k: wa.get(k) for k in (
            "basis", "zykluszeit_aktuell_s", "zykluszeit_basis_s", "automatisierbarer_anteil", "investition_euro",
            "investition_quelle", "betriebskosten_anteil", "stunden_jahr", "euro_jahr_brutto", "euro_jahr_netto",
            "amortisation_jahre",
        )}

    return {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "beispiel": False,
        "erstellt_am": doc.get("erstellt_am"),
        "job_id": doc.get("job_id"),
        "arbeitsplatz": doc.get("arbeitsplatz"),
        "empfehlung_id": e["id"],
        "empfehlung": e["text"] if e["id"] else None,
        "empfehlung_status": e["status"],
        "empfehlung_vorschlag_id": e["vorschlag_id"],
        "gruende": e.get("gruende", []),
        "vorrangig": e["vorrangig"],
        "vorrang_grund": e.get("vorrang_grund"),
        "verbesserungs_score": doc["verbesserungs_score"]["wert"],
        "automatisierungs_score": doc["automatisierungs_score"]["wert"],
        "zyklus_erkannt": z["erkannt"],
        "zyklus_hinweis": z.get("hinweis"),
        "anzahl_zyklen": z.get("anzahl_gueltig", 0),
        "zykluszeit_median_s": _w(z.get("zykluszeit_median_s")),
        "zykluszeit_vk": _w(z.get("zykluszeit_vk")),
        "zyklen_pro_schicht": _w(z.get("zyklen_pro_schicht")),
        "zeitanteil_in_zyklen": _w(z.get("zeitanteil_in_zyklen")),
        "ablauf_bestaetigt": ab["bestaetigt"],
        "anteile_ablauf": ab.get("anteile_ablauf"),
        "ablaufschritte": [{"typ": s["typ"], "anteil": s["anteil"], "klasse": s["klasse"]} for s in ab.get("ablaufschritte") or []],
        "hoehenzonen": {name: _w(zonen.get(name)) for name in ("unter_knie", "knie_huefte", "huefte_schulter", "ueber_schulter")},
        "griffe_ausserhalb_greifraum": _w(g.get("griffe_ausserhalb")),
        "reba_mittel": _w(b.get("reba_mittel")),
        "reba_max": _w(b.get("reba_max")),
        "buecken_anteil": _w(b.get("buecken_anteil")),
        "ueberkopf_anteil": _w(b.get("ueberkopf_anteil")),
        "drehung_anteil": _w(b.get("drehung_anteil")),
        "drehungen_pro_zyklus": _w(b.get("drehungen_pro_zyklus")),
        "verschwendung_min_schicht": wv.get("verschwendung_min_schicht"),
        "verbesserung_min_schicht": wv.get("verbesserung_min_schicht"),
        "verbesserung_euro_jahr": wv.get("euro_jahr"),
        "typ_id": t.get("id"),
        "typ_vorschlag": t.get("name"),
        "stunden_auto_jahr_bandbreite": wa.get("stunden_jahr") if wa.get("berechnet") else None,
        "automatisierung": automatisierung,
        "kundenangaben": {k: v for k, v in (doc.get("kundenangaben") or {}).items() if k in _KUNDE},
        "qualitaet": {k: v for k, v in qualitaet.items() if v is not None},
        "pilotphase": PILOTPHASE,
        "hinweise": [*doc.get("hinweise", []), HINWEIS_2D],
        "pflichthinweis": PFLICHTHINWEIS,
        "konfiguration_version": doc.get("konfiguration_version"),
    }
