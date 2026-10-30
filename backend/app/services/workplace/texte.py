"""German number formats and the reasons for the recommendation, shared by
the Steckbrief (dashboard), the PDF and the export."""
from __future__ import annotations

from .scoring import KENNZAHL_TEXT, ScoreErgebnis

PROZENT = {
    "verschwendung_anteil", "griffe_ausserhalb", "zeitanteil_in_zyklen", "zykluszeit_vk",
    "buecken_anteil", "ueberkopf_anteil", "drehung_anteil", "zone_knie_bis_schulter",
}


def zahl(x: float, nd: int = 0) -> str:
    """German format: 1.234,5 (thin grouping as in DIN 5008 is not needed here)."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def prozent(x: float) -> str:
    return f"{zahl(100 * x)} %"


def euro(x: float) -> str:
    """Rounded to hundreds: a rough estimate has no exact euros."""
    return f"{zahl(round(x / 100) * 100)} €"


def wert(kennzahl: str, x: float | None) -> str:
    if x is None:
        return "nicht belastbar messbar"
    if kennzahl in PROZENT:
        return prozent(x)
    if kennzahl == "besetzung_schwierigkeit":
        return f"{zahl(x)} von 5"
    if kennzahl in ("belastung_index", "handhabbarkeit_index"):
        return f"{zahl(x, 2)} von 1"
    if kennzahl == "reba_mittel":
        return zahl(x, 1)
    return zahl(x)


def _zeile(k, werte: dict) -> str:
    """One reason as a plain statement with the measured value behind it;
    the composite indices show their most telling input."""
    if k.messwert is None:
        return "kein wiederkehrender Zyklus erkannt"
    m = k.messwert
    saetze = {
        "verschwendung_anteil": lambda: f"{prozent(m)} der Zykluszeit sind Verschwendung",
        "griffe_ausserhalb": lambda: f"{prozent(m)} der Griffe außerhalb des günstigen Greifraums",
        "zykluszeit_vk": lambda: f"Zykluszeit schwankt um {prozent(m)}",
        "zyklen_pro_schicht": lambda: f"{zahl(m)} Zyklen pro Schicht",
        "zeitanteil_in_zyklen": lambda: f"{prozent(m)} der Zeit in wiederkehrenden Zyklen",
        "anzahl_varianten": lambda: f"{zahl(m)} Variante" + ("" if m == 1 else "n"),
        "besetzung_schwierigkeit": lambda: f"Stellenbesetzung: Schwierigkeit {zahl(m)} von 5",
    }
    if k.kennzahl == "belastung_index" and werte.get("reba_mittel") is not None:
        return f"Belastung: REBA-Mittel {zahl(werte['reba_mittel'], 1)}"
    if k.kennzahl == "handhabbarkeit_index" and werte.get("teilegewicht_kg") is not None:
        return f"Teilegewicht {zahl(werte['teilegewicht_kg'], 1)}\u00a0kg"
    if k.kennzahl in saetze:
        return saetze[k.kennzahl]()
    return f"{k.text}: {wert(k.kennzahl, m)}"


def _hoch(s: ScoreErgebnis) -> list:
    ks = [k for k in s.kriterien if k.beitrag is not None]
    return sorted(ks, key=lambda k: -k.beitrag)


def _niedrig(s: ScoreErgebnis) -> list:
    ks = [k for k in s.kriterien if k.teilwert is not None]
    return sorted(ks, key=lambda k: (k.teilwert, -k.gewicht))


def gruende(empfehlung_id: str | None, v: ScoreErgebnis, a: ScoreErgebnis, werte: dict | None = None) -> list[str]:
    """Up to three measured values that decide the recommendation: the
    criteria that raise a high score most, and the weakest ones of a low
    score. The same statement appears only once (the cycle variation counts
    in both scores)."""
    if empfehlung_id is None:
        return []
    plan = {
        "improve-then-automate": [(_hoch, v, 2), (_hoch, a, 1)],
        "improve": [(_hoch, v, 2), (_niedrig, a, 1)],
        "automate": [(_hoch, a, 2), (_niedrig, v, 1)],
        "keep": [(_niedrig, v, 2), (_niedrig, a, 1)],
    }[empfehlung_id]
    out: list[str] = []
    for f, s, n in plan:
        if not s.belastbar:
            continue
        neu = 0
        for k in f(s):
            z = _zeile(k, werte or {})
            if z in out:
                continue
            out.append(z)
            neu += 1
            if neu == n:
                break
    return out


__all__ = ["KENNZAHL_TEXT", "euro", "gruende", "prozent", "wert", "zahl"]
