"""Module results for the scoring tests, built directly (no pose data).

Four workplace profiles that lead to the four recommendations
(STECKBRIEF_MODUL S4 acceptance). Values are invented and plausible.
"""
from __future__ import annotations

from backend.app.services.workplace.belastung import BelastungErgebnis
from backend.app.services.workplace.cycles import KEIN_ZYKLUS, Zyklus, ZyklusErgebnis
from backend.app.services.workplace.quality import Kennzahl
from backend.app.services.workplace.reach import ZONEN, GreifraumErgebnis
from backend.app.services.workplace.segments import STEP_TYPES, BewerteterSchritt, transfer


def k(v: float) -> Kennzahl:
    return Kennzahl(float(v), 0.9, True)


def zyklen(median_s: float, vk: float, pro_schicht: float, zeitanteil: float, n: int = 10) -> ZyklusErgebnis:
    zs = [Zyklus(i * median_s, (i + 1) * median_s, median_s, 0.9, True) for i in range(n)]
    return ZyklusErgebnis(
        erkannt=True, hinweis=None, periode_s=median_s, periodizitaet=0.8, konfidenz=0.85, anzahl_gueltig=n, zyklen=zs,
        zykluszeit_median=k(median_s), zykluszeit_mittel=k(median_s), zykluszeit_std=k(vk * median_s),
        zykluszeit_vk=k(vk), zyklen_pro_schicht=k(pro_schicht), zeitanteil_in_zyklen=k(zeitanteil),
    )


def kein_zyklus() -> ZyklusErgebnis:
    f = Kennzahl.fehlt(KEIN_ZYKLUS)
    return ZyklusErgebnis(
        erkannt=False, hinweis=KEIN_ZYKLUS, periode_s=None, periodizitaet=0.1, konfidenz=0.0, anzahl_gueltig=0, zyklen=[],
        zykluszeit_median=f, zykluszeit_mittel=f, zykluszeit_std=f, zykluszeit_vk=f, zyklen_pro_schicht=f, zeitanteil_in_zyklen=f,
    )


def greifraum(ausserhalb: float, zonen=(0.05, 0.25, 0.65, 0.05)) -> GreifraumErgebnis:
    return GreifraumErgebnis(
        hoehenzonen={z: k(v) for z, v in zip(ZONEN, zonen)}, griffe_ausserhalb=k(ausserhalb),
        anzahl_griffe=50, griffe=[], abdeckung=0.9,
    )


def belastung(reba: float, buecken: float, ueberkopf: float, drehung: float, reba_max: float | None = None) -> BelastungErgebnis:
    return BelastungErgebnis(
        reba_mittel=k(reba), reba_max=k(reba_max or reba + 2), buecken_anteil=k(buecken),
        ueberkopf_anteil=k(ueberkopf), drehung_anteil=k(drehung), drehungen_pro_zyklus=k(1),
    )


def schritte(anteile: list[tuple], ) -> list[BewerteterSchritt]:
    """[(typ, anteil) or (typ, anteil, klasse)] in cycle order -> contiguous steps 0..1."""
    out, start = [], 0.0
    for i, item in enumerate(anteile):
        typ, anteil = item[0], item[1]
        klasse = item[2] if len(item) > 2 else STEP_TYPES[typ]
        ende = 1.0 if i == len(anteile) - 1 else start + anteil
        out.append(BewerteterSchritt(start, ende, typ, klasse))
        start = ende
    return out


PROFILE = {
    # assembly workplace like the demo in STECKBRIEF_MODUL §7: waste and repetition
    "improve-then-automate": dict(
        schritte=[("Greifen", 0.18), ("Suchen", 0.09), ("Bringen", 0.14), ("Fügen", 0.34), ("Gehen", 0.13), ("Platzieren", 0.12)],
        zyklen=(38.4, 0.14, 690, 0.82), griffe=0.21, zonen=(0.08, 0.29, 0.56, 0.07), belastung=(5.8, 0.1, 0.05, 0.1),
        kunde={"teilegewicht_kg": 1.2, "abmessungen_cm": {"laenge": 30, "breite": 20, "hoehe": 10}, "anzahl_varianten": 3,
               "stueck_pro_schicht": 680, "schichten_pro_tag": 2, "schichtdauer_min": 480, "arbeitstage_pro_jahr": 220,
               "vollkosten_euro_pro_stunde": 48, "besetzung_schwierigkeit": 4},
    ),
    # set-up place: searching and walking, many variants, few long cycles
    "improve": dict(
        schritte=[("Greifen", 0.15), ("Suchen", 0.2), ("Gehen", 0.15), ("Bearbeiten", 0.3), ("Prüfen", 0.1), ("Platzieren", 0.1)],
        zyklen=(150.0, 0.35, 120, 0.7), griffe=0.35, zonen=(0.15, 0.3, 0.45, 0.1), belastung=(7.0, 0.25, 0.1, 0.2),
        kunde={"teilegewicht_kg": 5, "abmessungen_cm": {"laenge": 50}, "anzahl_varianten": 40, "besetzung_schwierigkeit": 2,
               "schichten_pro_tag": 1, "arbeitstage_pro_jahr": 220, "vollkosten_euro_pro_stunde": 45},
    ),
    # lean, short, uniform cycle with one variant
    "automate": dict(
        schritte=[("Greifen", 0.25), ("Bringen", 0.15), ("Fügen", 0.45), ("Platzieren", 0.12), ("Warten", 0.03)],
        zyklen=(20.0, 0.06, 1300, 0.92), griffe=0.05, zonen=(0.0, 0.2, 0.8, 0.0), belastung=(4.0, 0.05, 0.0, 0.05),
        kunde={"teilegewicht_kg": 0.5, "abmessungen_cm": {"laenge": 15}, "anzahl_varianten": 1, "besetzung_schwierigkeit": 5,
               "schichten_pro_tag": 3, "arbeitstage_pro_jahr": 250, "vollkosten_euro_pro_stunde": 52},
    ),
    # long, varied work with little waste and low load
    "keep": dict(
        schritte=[("Bearbeiten", 0.7), ("Prüfen", 0.15), ("Greifen", 0.1), ("Gehen", 0.05)],
        zyklen=(600.0, 0.25, 40, 0.6), griffe=0.08, zonen=(0.02, 0.3, 0.65, 0.03), belastung=(3.0, 0.02, 0.0, 0.02),
        kunde={"teilegewicht_kg": 15, "abmessungen_cm": {"laenge": 120, "breite": 80, "hoehe": 60}, "anzahl_varianten": 30,
               "besetzung_schwierigkeit": 1},
    ),
}


def module_results(name: str, **override) -> dict:
    """Keyword arguments for steckbrief.build of a profile (job_id and cfg excluded)."""
    p = {**PROFILE[name], **override}
    z = zyklen(*p["zyklen"]) if p["zyklen"] else kein_zyklus()
    st = schritte(p["schritte"]) if p["schritte"] and z.erkannt else None
    return dict(
        zyklen=z,
        greifraum=greifraum(p["griffe"], p["zonen"]),
        schritte=st,
        ablauf=transfer(st, z) if st else None,
        belastung=belastung(*p["belastung"]),
        kunde=p["kunde"],
    )
