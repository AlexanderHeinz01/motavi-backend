"""Scores, recommendation, priority and automation type (STECKBRIEF_MODUL §5, S4)."""
import copy
import json

import pytest
from pydantic import ValidationError

from backend.app.services.workplace import scoring, scoring_config, steckbrief
from backend.app.services.workplace.scoring_config import Rampe, ScoringConfig
from backend.app.services.workplace.segments import STEP_TYPES
from backend.tests.profiles import PROFILE, module_results

CFG = scoring_config.get()
RAW = json.loads(scoring_config.DEFAULT_PATH.read_text(encoding="utf-8"))


def build(name, **override):
    return steckbrief.build(CFG, "job", **module_results(name, **override))


# ── configuration ────────────────────────────────────────────────────────────


def test_config_is_the_only_source():
    assert STEP_TYPES == CFG.schritt_typen
    for s in (CFG.verbesserungs_score, CFG.automatisierungs_score):
        assert sum(k.gewicht for k in s.kriterien.values()) == pytest.approx(1.0)
    assert CFG.vermeidbarer_anteil == {"Suchen": 0.8, "Gehen": 0.5, "Warten": 0.5, "Umgreifen": 0.7}
    assert CFG.empfehlung.schwelle_verbesserung == 50 and CFG.empfehlung.schwelle_automatisierung == 60
    assert CFG.vorrang.reba_mittel_ab == 8


def test_weights_as_in_the_plan():
    v = {k: c.gewicht for k, c in CFG.verbesserungs_score.kriterien.items()}
    a = {k: c.gewicht for k, c in CFG.automatisierungs_score.kriterien.items()}
    assert v == {"verschwendung": 0.35, "greifraum": 0.2, "belastung": 0.3, "zyklusschwankung": 0.15}
    assert a == {"wiederholungen": 0.2, "gleichfoermigkeit": 0.2, "varianten": 0.15, "handhabbarkeit": 0.1,
                 "belastung": 0.15, "zeitanteil_zyklen": 0.1, "stellenbesetzung": 0.1}


@pytest.mark.parametrize("change, message", [
    (lambda c: c["verbesserungs_score"]["kriterien"]["greifraum"].update(gewicht=0.3), "Gewichte ergeben"),
    (lambda c: c["empfehlung"]["regeln"].pop(), "jede Kombination"),
    (lambda c: c["vermeidbarer_anteil"].update(Trödeln=0.5), "unbekannter Typ"),
    (lambda c: c["vermeidbarer_anteil"].update(Suchen=1.5), "nicht zwischen 0 und 1"),
    (lambda c: c["automatisierungstypen"]["regeln"][0]["bedingungen"][0].update(ab=None), "ab oder bis"),
    (lambda c: c["automatisierungstypen"]["regeln"][0].update(automatisierbarer_anteil=[0.9, 0.5]), "automatisierbarer_anteil"),
    (lambda c: c["automatisierungstypen"]["regeln"][0].update(betriebskosten_anteil=[0.2, 1.0]), "betriebskosten_anteil"),
    (lambda c: c["automatisierungstypen"]["regeln"][0].pop("betriebskosten_anteil"), "betriebskosten_anteil"),
])
def test_invalid_config_is_rejected(change, message):
    raw = copy.deepcopy(RAW)
    change(raw)
    with pytest.raises(ValidationError, match=message):
        ScoringConfig.model_validate(raw)


def test_ramp_linear_clamped_and_inverse():
    r = Rampe(null_bei=0.1, voll_bei=0.3)
    assert [r(0.0), r(0.1), r(0.2), r(0.3), r(1.0)] == pytest.approx([0, 0, 0.5, 1, 1])
    inv = Rampe(null_bei=20, voll_bei=1)
    assert [inv(1), inv(10.5), inv(20), inv(40)] == pytest.approx([1, 0.5, 0, 0])


# ── scores ───────────────────────────────────────────────────────────────────


def test_improvement_score_by_hand():
    werte = {"verschwendung_anteil": 0.15, "griffe_ausserhalb": 0.35, "belastung_index": 0.5, "zykluszeit_vk": 0.05}
    s = scoring.score(CFG.verbesserungs_score, werte)
    # 0.35 * 0.5 + 0.2 * 1 + 0.3 * 0.5 + 0.15 * 0 = 0.525
    assert s.wert == 53 and s.belastbar and s.vollstaendig
    assert sum(k.beitrag for k in s.kriterien) == pytest.approx(52.5)


def test_automation_score_extremes():
    voll = {"zyklen_pro_schicht": 600, "zykluszeit_vk": 0.08, "anzahl_varianten": 1, "handhabbarkeit_index": 1,
            "belastung_index": 1, "zeitanteil_in_zyklen": 0.9, "besetzung_schwierigkeit": 5}
    null = {"zyklen_pro_schicht": 60, "zykluszeit_vk": 0.35, "anzahl_varianten": 20, "handhabbarkeit_index": 0,
            "belastung_index": 0, "zeitanteil_in_zyklen": 0.4, "besetzung_schwierigkeit": 1}
    assert scoring.score(CFG.automatisierungs_score, voll).wert == 100
    assert scoring.score(CFG.automatisierungs_score, null).wert == 0


def test_missing_criterion_spreads_its_weight():
    werte = {"griffe_ausserhalb": 0.35, "belastung_index": 0.5, "zykluszeit_vk": 0.05}
    s = scoring.score(CFG.verbesserungs_score, werte)
    # (0.2 * 1 + 0.3 * 0.5) / 0.65
    assert s.wert == 54 and s.belastbar and not s.vollstaendig
    assert s.fehlend == ["Zeitanteil Verschwendung"] and s.vorhanden == pytest.approx(0.65)


def test_too_few_criteria_not_reliable():
    s = scoring.score(CFG.automatisierungs_score, {"anzahl_varianten": 1, "besetzung_schwierigkeit": 5})
    assert s.wert is None and not s.belastbar and s.anzeige == "nicht belastbar messbar"
    e = scoring.empfehlung(CFG, scoring.score(CFG.verbesserungs_score, {"griffe_ausserhalb": 0.1, "belastung_index": 0.2}), s)
    assert e.id is None and "Automatisierungs-Score" in e.text


def test_load_index_spreads_missing_twist():
    # REBA 5.5 -> 0.5, bending 0.3 -> 1, overhead 0 -> 0, twist missing
    i = scoring.index(CFG.belastung, {"reba_mittel": 5.5, "buecken_anteil": 0.3, "ueberkopf_anteil": 0.0})
    assert i.wert == pytest.approx((0.5 * 0.5 + 0.2 * 1) / 0.9)
    assert i.teile["drehung_anteil"] is None


def test_handling_index_from_weight_and_size():
    i = scoring.index(CFG.handhabbarkeit, {"teilegewicht_kg": 22.5, "groesste_kante_cm": 60})
    assert i.wert == pytest.approx(0.6 * 0.5 + 0.4 * 1)
    assert scoring.index(CFG.handhabbarkeit, {}).wert is None


# ── recommendation ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", list(PROFILE))
def test_four_profiles_give_the_four_recommendations(name):
    doc = build(name)
    e = doc["empfehlung"]
    assert e["id"] == name, (doc["verbesserungs_score"]["wert"], doc["automatisierungs_score"]["wert"])
    assert e["text"] == CFG.empfehlung.texte[name]
    assert e["status"] == "vorschlag" and not e["vorlaeufig"]
    assert doc["verbesserungs_score"]["vollstaendig"] and doc["automatisierungs_score"]["vollstaendig"]


def test_profile_scores():
    scores = {n: (build(n)["verbesserungs_score"]["wert"], build(n)["automatisierungs_score"]["wert"]) for n in PROFILE}
    assert scores == {"improve-then-automate": (55, 81), "improve": (91, 31), "automate": (13, 88), "keep": (23, 20)}


@pytest.mark.parametrize("v, a, expected", [
    (50, 60, "improve-then-automate"), (50, 59, "improve"), (49, 60, "automate"), (49, 59, "keep"),
])
def test_thresholds_inclusive(v, a, expected):
    sv = scoring.ScoreErgebnis(v, True, 1.0, [], [])
    sa = scoring.ScoreErgebnis(a, True, 1.0, [], [])
    assert scoring.empfehlung(CFG, sv, sa).id == expected


def test_without_review_provisional():
    doc = build("improve-then-automate", schritte=None)
    assert doc["empfehlung"]["vorlaeufig"]
    assert doc["verbesserungs_score"]["fehlend"] == ["Zeitanteil Verschwendung"]
    assert any("noch nicht vom Experten bestätigt" in h for h in doc["hinweise"])


def test_no_cycle_is_a_result_and_never_automation():
    doc = build("automate", zyklen=None)
    a = doc["automatisierungs_score"]
    # repetitions, uniformity and time in cycles count as 0 instead of dropping out
    crit = {c["id"]: c for c in a["kriterien"]}
    assert crit["wiederholungen"]["teilwert"] == 0 and crit["gleichfoermigkeit"]["teilwert"] == 0
    assert a["belastbar"] and a["wert"] < CFG.empfehlung.schwelle_automatisierung
    assert doc["empfehlung"]["id"] in ("improve", "keep")
    assert doc["verbesserungs_score"]["belastbar"]  # from reach and load


# ── priority ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("reba, vorrangig", [(7.99, False), (8.0, True), (11.0, True)])
def test_priority_threshold(reba, vorrangig):
    v = scoring.vorrang(CFG, reba)
    assert v.vorrangig is vorrangig
    assert (v.text == CFG.vorrang.text) is vorrangig


def test_priority_independent_of_recommendation():
    doc = build("automate", belastung=(8.5, 0.05, 0.0, 0.05))
    assert doc["empfehlung"]["id"] == "automate" and doc["empfehlung"]["vorrangig"]
    assert "REBA-Mittel 8.5" in doc["empfehlung"]["vorrang_grund"]
    assert not build("keep")["empfehlung"]["vorrangig"]
    assert scoring.vorrang(CFG, None).vorrangig is False


# ── automation type ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("werte, anteile, expected", [
    ({"teilegewicht_kg": 12, "zone_knie_bis_schulter": 0.8, "zykluszeit_vk": 0.1},
     {"Greifen": 0.2, "Bringen": 0.1, "Platzieren": 0.2, "Fügen": 0.5}, "palettieren"),
    ({"teilegewicht_kg": 2, "zykluszeit_vk": 0.3}, {"Gehen": 0.1, "Warten": 0.15, "Bearbeiten": 0.75}, "maschinenbeladung"),
    ({"teilegewicht_kg": 2, "zykluszeit_vk": 0.3}, {"Prüfen": 0.3, "Fügen": 0.7}, "pruefautomatisierung"),
    ({"teilegewicht_kg": 2, "zone_knie_bis_schulter": 0.9, "zykluszeit_vk": 0.1},
     {"Greifen": 0.2, "Bringen": 0.1, "Platzieren": 0.2, "Fügen": 0.5}, "pick_and_place"),
])
def test_type_rules(werte, anteile, expected):
    t = scoring.automatisierungstyp(CFG, werte, anteile)
    assert t.vorschlag.id == expected
    assert next(r for r in t.regeln if r.id == expected).passt is True


def test_type_rules_order_more_specific_first():
    # heavy parts: palletising and pick and place both hold, the first rule wins
    t = scoring.automatisierungstyp(CFG, {"teilegewicht_kg": 12, "zone_knie_bis_schulter": 0.8, "zykluszeit_vk": 0.1},
                                    {"Greifen": 0.5, "Fügen": 0.5})
    passt = [r.id for r in t.regeln if r.passt]
    assert passt == ["palettieren", "pick_and_place"] and t.vorschlag.id == "palettieren"


def test_type_rule_with_missing_value_stays_open():
    t = scoring.automatisierungstyp(CFG, {"zykluszeit_vk": 0.1}, {"Greifen": 0.5, "Fügen": 0.5})
    palett = next(r for r in t.regeln if r.id == "palettieren")
    assert palett.passt is None and palett.bedingungen[0].erfuellt is None
    assert t.vorschlag.id == "pick_and_place"


def test_no_type_matches():
    t = scoring.automatisierungstyp(CFG, {"teilegewicht_kg": 2, "zykluszeit_vk": 0.3}, {"Fügen": 0.9, "Greifen": 0.1})
    assert t.vorschlag is None and t.text == CFG.automatisierungstypen.kein_typ
    t = scoring.automatisierungstyp(CFG, {"teilegewicht_kg": 2}, None)
    assert t.vorschlag is None and "noch nicht vom Experten bestätigt" in t.text


def test_type_only_with_automation_recommendation():
    assert build("improve-then-automate")["automatisierungstyp"]["vorschlag"] == "Pick and Place"
    assert build("automate")["automatisierungstyp"]["vorschlag"] == "Pick and Place"
    for name in ("improve", "keep"):
        t = build(name)["automatisierungstyp"]
        assert t["vorschlag"] is None and t["regeln"] == [] and "Nur bei einer Empfehlung mit Automatisierung" in t["text"]


def test_type_uses_expert_class_change_not_type():
    # the expert classifies "Prüfen" as waste: the type share still counts for the rule
    t = scoring.automatisierungstyp(CFG, {"zykluszeit_vk": 0.3}, steckbrief.typ_anteile(
        module_results("improve", schritte=[("Prüfen", 0.3, "verschwendung"), ("Fügen", 0.7)])["schritte"]))
    assert t.vorschlag.id == "pruefautomatisierung"


# ── customer inputs ──────────────────────────────────────────────────────────


def test_plausibility_pieces_per_shift():
    assert steckbrief.plausibilitaet(CFG, 690, 680) is None
    hint = steckbrief.plausibilitaet(CFG, 690, 500)
    assert "500 Stück pro Schicht weicht um 38 %" in hint
    assert steckbrief.plausibilitaet(CFG, None, 500) is None
    doc = build("improve-then-automate", kunde={**PROFILE["improve-then-automate"]["kunde"], "stueck_pro_schicht": 300})
    assert any("weicht um" in h for h in doc["hinweise"])


def test_largest_edge_and_zone_metric():
    werte = steckbrief.kennzahlen(CFG, **{k: v for k, v in module_results("keep").items() if k != "schritte"})
    assert werte["groesste_kante_cm"] == 120
    assert werte["zone_knie_bis_schulter"] == pytest.approx(0.95)
    assert werte["verschwendung_anteil"] == pytest.approx(0.05)
