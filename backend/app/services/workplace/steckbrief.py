"""Assembles the Arbeitsplatz-Steckbrief (STECKBRIEF_MODUL §4 and §5).

Pure function of the module results: cycles, reach, process steps (after the
expert review), load, customer inputs. The router stores the dict as
results/{job_id}/workplace.json.
"""
from __future__ import annotations

from dataclasses import asdict

from . import scoring
from .belastung import BelastungErgebnis
from .cycles import KEIN_ZYKLUS, ZyklusErgebnis
from .quality import Kennzahl
from .reach import GreifraumErgebnis
from .scoring_config import ScoringConfig
from .segments import AblaufErgebnis, BewerteterSchritt
from .wirtschaft import Ablauf, Betrieb, wirtschaftlichkeit


def _w(k: Kennzahl | None) -> float | None:
    """Value of a metric only if it is reliable."""
    return k.wert if k is not None and k.belastbar else None


def _k(k: Kennzahl | None, nd: int = 4) -> dict | None:
    if k is None:
        return None
    return {
        "wert": None if k.wert is None else round(k.wert, nd),
        "qualitaet": round(k.qualitaet, 3),
        "belastbar": k.belastbar,
        "grund": k.grund,
    }


def typ_anteile(schritte: list[BewerteterSchritt]) -> dict[str, float]:
    """Share of each step type of the cycle."""
    out: dict[str, float] = {}
    for s in schritte:
        out[s.typ] = out.get(s.typ, 0.0) + (s.ende_phase - s.start_phase)
    return out


def verschwendung_anteile(schritte: list[BewerteterSchritt]) -> dict[str, float]:
    """Share per type of the steps classified as waste (the expert's class counts)."""
    out: dict[str, float] = {}
    for s in schritte:
        if s.klasse == "verschwendung":
            out[s.typ] = out.get(s.typ, 0.0) + (s.ende_phase - s.start_phase)
    return out


def groesste_kante(kunde: dict) -> float | None:
    a = kunde.get("abmessungen_cm") or {}
    werte = [v for v in (a.get("laenge"), a.get("breite"), a.get("hoehe")) if v]
    return max(werte) if werte else None


def kennzahlen(cfg: ScoringConfig, zyklen: ZyklusErgebnis, greifraum: GreifraumErgebnis | None,
               ablauf: AblaufErgebnis | None, belastung: BelastungErgebnis, kunde: dict) -> dict[str, float | None]:
    """All metric values the scores and type rules use (None = missing or not reliable)."""
    zonen = greifraum.hoehenzonen if greifraum else {}
    kb = [_w(zonen.get("knie_huefte")), _w(zonen.get("huefte_schulter"))]
    werte: dict[str, float | None] = {
        "verschwendung_anteil": ablauf.anteile_ablauf["verschwendung"] if ablauf else None,
        "griffe_ausserhalb": _w(greifraum.griffe_ausserhalb) if greifraum else None,
        "zykluszeit_vk": _w(zyklen.zykluszeit_vk),
        "zyklen_pro_schicht": _w(zyklen.zyklen_pro_schicht),
        "zeitanteil_in_zyklen": _w(zyklen.zeitanteil_in_zyklen),
        "reba_mittel": _w(belastung.reba_mittel),
        "buecken_anteil": _w(belastung.buecken_anteil),
        "ueberkopf_anteil": _w(belastung.ueberkopf_anteil),
        "drehung_anteil": _w(belastung.drehung_anteil),
        "zone_knie_bis_schulter": None if None in kb else sum(kb),
        "anzahl_varianten": kunde.get("anzahl_varianten"),
        "besetzung_schwierigkeit": kunde.get("besetzung_schwierigkeit"),
        "teilegewicht_kg": kunde.get("teilegewicht_kg"),
        "groesste_kante_cm": groesste_kante(kunde),
    }
    werte["belastung_index"] = scoring.index(cfg.belastung, werte).wert
    werte["handhabbarkeit_index"] = scoring.index(cfg.handhabbarkeit, werte).wert
    return werte


def plausibilitaet(cfg: ScoringConfig, zyklen_pro_schicht: float | None, stueck: float | None) -> str | None:
    """Hint if the customer's pieces per shift differ from the measured cycles (§4.5)."""
    if not zyklen_pro_schicht or not stueck:
        return None
    abw = (zyklen_pro_schicht - stueck) / stueck
    if abs(abw) < cfg.kundenangaben.plausibilitaet_toleranz:
        return None
    return (
        f"Angabe {stueck:g} Stück pro Schicht weicht um {abs(abw) * 100:.0f} % von den hochgerechneten "
        f"{zyklen_pro_schicht:.0f} Zyklen ab. Mögliche Gründe: mehrere Teile je Zyklus, Pausen oder Nebentätigkeiten, "
        "Aufnahme nicht repräsentativ für die Schicht."
    )


def _score_dict(s: scoring.ScoreErgebnis) -> dict:
    return {
        "wert": s.wert,
        "belastbar": s.belastbar,
        "anzeige": s.anzeige,
        "vollstaendig": s.vollstaendig,
        "vorhanden": s.vorhanden,
        "fehlend": s.fehlend,
        "kriterien": [asdict(k) for k in s.kriterien],
    }


def build(cfg: ScoringConfig, job_id: str, zyklen: ZyklusErgebnis, greifraum: GreifraumErgebnis | None,
          schritte: list[BewerteterSchritt] | None, ablauf: AblaufErgebnis | None, belastung: BelastungErgebnis,
          kunde: dict | None, review: dict | None = None) -> dict:
    kunde = kunde or {}
    werte = kennzahlen(cfg, zyklen, greifraum, ablauf, belastung, kunde)
    kein_zyklus = not zyklen.erkannt and zyklen.hinweis == KEIN_ZYKLUS
    v = scoring.score(cfg.verbesserungs_score, werte, kein_zyklus)
    a = scoring.score(cfg.automatisierungs_score, werte, kein_zyklus)
    emp = scoring.empfehlung(cfg, v, a)
    vor = scoring.vorrang(cfg, werte["reba_mittel"])

    anteile = typ_anteile(schritte) if schritte else None
    typ = scoring.automatisierungstyp(cfg, werte, anteile)
    if emp.mit_automatisierung:
        typ_regel, typ_text = typ.vorschlag, typ.text
    else:
        typ_regel, typ_text = None, "Nur bei einer Empfehlung mit Automatisierung."

    ablauf_w = None
    if ablauf and schritte:
        ablauf_w = Ablauf(
            verschwendung_anteile=verschwendung_anteile(schritte),
            # unrounded mean of the valid cycles (sekunden_je_zyklus is rounded per class)
            mittel_zyklus_s=sum(r["dauer_s"] for r in ablauf.je_zyklus) / len(ablauf.je_zyklus),
            zykluszeit_median_s=_w(zyklen.zykluszeit_median),
            zyklen_pro_schicht=_w(zyklen.zyklen_pro_schicht),
        )
    inv = kunde.get("investition_euro")
    betrieb = Betrieb(
        schichten_pro_tag=kunde.get("schichten_pro_tag"),
        arbeitstage_pro_jahr=kunde.get("arbeitstage_pro_jahr"),
        stundensatz=kunde.get("vollkosten_euro_pro_stunde"),
        investition_euro=tuple(inv) if inv else None,
    )
    wirt = wirtschaftlichkeit(cfg, emp.id, typ_regel, ablauf_w,
                              (_w(zyklen.zykluszeit_median), _w(zyklen.zyklen_pro_schicht)), betrieb)

    hinweise = []
    if not schritte:
        hinweise.append("Ablaufschritte noch nicht vom Experten bestätigt: Verschwendung fehlt im Verbesserungs-Score.")
    p = plausibilitaet(cfg, _w(zyklen.zyklen_pro_schicht), kunde.get("stueck_pro_schicht"))
    if p:
        hinweise.append(p)
    hinweise.append(belastung.hinweis)

    return {
        "job_id": job_id,
        "konfiguration_version": cfg.version,
        "empfehlung": {**asdict(emp), "vorrangig": vor.vorrangig, "vorrang_text": vor.text, "vorrang_grund": vor.grund},
        "verbesserungs_score": _score_dict(v),
        "automatisierungs_score": _score_dict(a),
        "automatisierungstyp": {
            "vorschlag": typ_regel.name if typ_regel else None,
            "id": typ_regel.id if typ_regel else None,
            "text": typ_text,
            "regeln": [asdict(r) for r in typ.regeln] if emp.mit_automatisierung else [],
        },
        "zyklen": {
            "erkannt": zyklen.erkannt,
            "hinweis": zyklen.hinweis,
            "konfidenz": round(zyklen.konfidenz, 3),
            "anzahl_gueltig": zyklen.anzahl_gueltig,
            "zykluszeit_median_s": _k(zyklen.zykluszeit_median, 2),
            "zykluszeit_vk": _k(zyklen.zykluszeit_vk),
            "zyklen_pro_schicht": _k(zyklen.zyklen_pro_schicht, 1),
            "zeitanteil_in_zyklen": _k(zyklen.zeitanteil_in_zyklen),
        },
        "ablauf": {
            "bestaetigt": bool(schritte),
            "bestaetigt_von": (review or {}).get("bestaetigt_von"),
            "bestaetigt_am": (review or {}).get("bestaetigt_am"),
            "ablaufschritte": ablauf.ablaufschritte if ablauf else [],
            "anteile_ablauf": ablauf.anteile_ablauf if ablauf else None,
            "minuten_pro_schicht": ablauf.minuten_pro_schicht if ablauf else None,
        },
        "greifraum": {
            "hoehenzonen": {z: _k(k) for z, k in greifraum.hoehenzonen.items()},
            "griffe_ausserhalb": _k(greifraum.griffe_ausserhalb),
            "anzahl_griffe": greifraum.anzahl_griffe,
            "hinweis": greifraum.hinweis,
        } if greifraum else None,
        "belastung": {
            "reba_mittel": _k(belastung.reba_mittel, 2),
            "reba_max": _k(belastung.reba_max, 2),
            "buecken_anteil": _k(belastung.buecken_anteil),
            "ueberkopf_anteil": _k(belastung.ueberkopf_anteil),
            "drehung_anteil": _k(belastung.drehung_anteil),
            "drehungen_pro_zyklus": _k(belastung.drehungen_pro_zyklus, 1),
            "index": None if werte["belastung_index"] is None else round(werte["belastung_index"], 4),
        },
        "kundenangaben": kunde,
        "wirtschaftlichkeit": wirt,
        "hinweise": hinweise,
    }
