"""Economics, rough (STECKBRIEF_MODUL §5.5).

    # improve
    min_verbesserung       = verschwendung_min_schicht * vermeidbarer_anteil   (per waste type, summed)
    euro_verbesserung_jahr = min_verbesserung * schichten * tage / 60 * stundensatz

    # automate
    stunden_auto_jahr = zykluszeit_s * zyklen_schicht * schichten * tage / 3600 * automatisierbarer_anteil
    euro_auto_brutto  = stunden_auto_jahr * stundensatz
    euro_auto_netto   = euro_auto_brutto * (1 - betriebskosten_anteil)   (maintenance, energy, programming)
    amortisation      = investition / euro_auto_netto       (years, as a range)

For "Erst verbessern, dann automatisieren" the automation is computed on the
improved process: cycle time minus the avoidable waste. The number of cycles
per shift stays (same output). schichten = shifts per day, tage = working
days per year. Every range is (low, high).
"""
from __future__ import annotations

from dataclasses import dataclass

from .scoring_config import ScoringConfig, TypRegel


@dataclass(frozen=True)
class Ablauf:
    """Inputs from the process steps (expert review) and the cycles."""

    verschwendung_anteile: dict[str, float]  # waste type -> share of the cycle time
    mittel_zyklus_s: float  # mean duration of the valid cycles
    zykluszeit_median_s: float | None
    zyklen_pro_schicht: float | None


@dataclass(frozen=True)
class Betrieb:
    """Customer inputs for the money values (§4.5)."""

    schichten_pro_tag: float | None = None
    arbeitstage_pro_jahr: float | None = None
    stundensatz: float | None = None  # full cost per hour in euro
    investition_euro: tuple[float, float] | None = None


def _bereich(lo: float, hi: float, nd: int = 1) -> list[float]:
    return [round(min(lo, hi), nd), round(max(lo, hi), nd)]


def verbessern(cfg: ScoringConfig, ablauf: Ablauf | None, betrieb: Betrieb) -> dict:
    if ablauf is None or not ablauf.zyklen_pro_schicht:
        return {"berechnet": False, "grund": "Ablaufschritte nicht bestätigt oder kein Zyklus erkannt."}
    je_typ = {}
    vermeidbar_anteil = 0.0
    for typ, anteil in sorted(ablauf.verschwendung_anteile.items()):
        minuten = anteil * ablauf.mittel_zyklus_s * ablauf.zyklen_pro_schicht / 60
        quote = cfg.vermeidbarer_anteil.get(typ, 0.0)
        vermeidbar_anteil += anteil * quote
        je_typ[typ] = {"min_schicht": round(minuten, 1), "vermeidbarer_anteil": quote, "vermeidbar_min_schicht": round(minuten * quote, 1)}
    min_verbesserung = vermeidbar_anteil * ablauf.mittel_zyklus_s * ablauf.zyklen_pro_schicht / 60
    out = {
        "berechnet": True,
        "verschwendung_min_schicht": round(sum(v["min_schicht"] for v in je_typ.values()), 1),
        "verbesserung_min_schicht": round(min_verbesserung, 1),
        "vermeidbar_anteil_zyklus": round(vermeidbar_anteil, 4),
        "je_typ": je_typ,
        "euro_jahr": None,
        "fehlende_angaben": [],
    }
    fehlt = _fehlend(betrieb, stundensatz=True)
    if fehlt:
        out["fehlende_angaben"] = fehlt
    else:
        out["euro_jahr"] = round(min_verbesserung * betrieb.schichten_pro_tag * betrieb.arbeitstage_pro_jahr / 60 * betrieb.stundensatz)
    return out


def _fehlend(b: Betrieb, stundensatz: bool) -> list[str]:
    fehlt = []
    if not b.schichten_pro_tag:
        fehlt.append("Schichten pro Tag")
    if not b.arbeitstage_pro_jahr:
        fehlt.append("Arbeitstage pro Jahr")
    if stundensatz and not b.stundensatz:
        fehlt.append("Vollkosten pro Stunde")
    return fehlt


def automatisieren(cfg: ScoringConfig, typ: TypRegel | None, ablauf: Ablauf | None, zyklus: tuple[float | None, float | None],
                   betrieb: Betrieb, verbessert: bool) -> dict:
    """zyklus: (median cycle time s, cycles per shift); verbessert: compute on the improved process."""
    zykluszeit, zyklen = zyklus
    if not zykluszeit or not zyklen:
        return {"berechnet": False, "grund": "Kein wiederkehrender Zyklus erkannt."}
    if typ is None:
        return {"berechnet": False, "grund": "Kein Automatisierungstyp festgelegt."}
    basis_s = zykluszeit
    abzug_s = 0.0
    if verbessert:
        if ablauf is None:
            return {"berechnet": False, "grund": "Verbesserter Ablauf braucht bestätigte Ablaufschritte."}
        anteil = sum(a * cfg.vermeidbarer_anteil.get(t, 0.0) for t, a in ablauf.verschwendung_anteile.items())
        abzug_s = zykluszeit * anteil
        basis_s = zykluszeit - abzug_s
    lo, hi = typ.automatisierbarer_anteil
    if betrieb.investition_euro:
        inv, inv_quelle = betrieb.investition_euro, "Kundenangabe"
    else:
        inv, inv_quelle = typ.investition_euro, f"Standardwert für {typ.name}"
    out = {
        "berechnet": True,
        "basis": "verbesserter Ablauf" if verbessert else "aktueller Ablauf",
        "typ": typ.name,
        "zykluszeit_aktuell_s": round(zykluszeit, 2),
        "vermeidbar_s": round(abzug_s, 2),
        "zykluszeit_basis_s": round(basis_s, 2),
        "zyklen_pro_schicht": round(zyklen, 1),
        "automatisierbarer_anteil": [lo, hi],
        "investition_euro": [inv[0], inv[1]],
        "investition_quelle": inv_quelle,
        "betriebskosten_anteil": [typ.betriebskosten_anteil[0], typ.betriebskosten_anteil[1]],
        "stunden_jahr": None,
        "euro_jahr_brutto": None,
        "betriebskosten_euro_jahr": None,
        "euro_jahr_netto": None,
        "amortisation_jahre": None,
        "fehlende_angaben": [],
    }
    if _fehlend(betrieb, stundensatz=False):
        out["fehlende_angaben"] = _fehlend(betrieb, stundensatz=True)
        return out
    stunden_voll = basis_s * zyklen * betrieb.schichten_pro_tag * betrieb.arbeitstage_pro_jahr / 3600
    stunden = (stunden_voll * lo, stunden_voll * hi)
    out["stunden_jahr"] = _bereich(*stunden)
    if not betrieb.stundensatz:
        out["fehlende_angaben"] = ["Vollkosten pro Stunde"]
        return out
    brutto = (stunden[0] * betrieb.stundensatz, stunden[1] * betrieb.stundensatz)
    bk_lo, bk_hi = typ.betriebskosten_anteil
    # cautious bound: low savings with high running costs; optimistic: the other way round
    netto = (brutto[0] * (1 - bk_hi), brutto[1] * (1 - bk_lo))
    out["euro_jahr_brutto"] = _bereich(*brutto, nd=0)
    out["betriebskosten_euro_jahr"] = _bereich(brutto[0] * bk_lo, brutto[1] * bk_hi, nd=0)
    out["euro_jahr_netto"] = _bereich(*netto, nd=0)
    # fastest: low investment with high net savings; slowest: high investment with low net savings
    out["amortisation_jahre"] = _bereich(inv[0] / netto[1], inv[1] / netto[0])
    return out


def wirtschaftlichkeit(cfg: ScoringConfig, empfehlung_id: str | None, typ: TypRegel | None, ablauf: Ablauf | None,
                       zyklus: tuple[float | None, float | None], betrieb: Betrieb) -> dict:
    """Both parts; automation only for a recommendation with automation."""
    mit_auto = empfehlung_id in cfg.empfehlung.mit_automatisierung
    auto = (
        automatisieren(cfg, typ, ablauf, zyklus, betrieb, verbessert=empfehlung_id == "improve-then-automate")
        if mit_auto
        else {"berechnet": False, "grund": "Nur bei einer Empfehlung mit Automatisierung."}
    )
    return {
        "verbessern": verbessern(cfg, ablauf, betrieb),
        "automatisieren": auto,
        "hinweis": cfg.wirtschaftlichkeit.hinweis,
    }
