"""Economics (STECKBRIEF_MODUL §5.5), checked against hand calculations."""
import pytest

from backend.app.services.workplace import scoring_config, steckbrief
from backend.app.services.workplace.wirtschaft import Ablauf, Betrieb, automatisieren, verbessern, wirtschaftlichkeit
from backend.tests.profiles import PROFILE, module_results

CFG = scoring_config.get()
PICK = next(r for r in CFG.automatisierungstypen.regeln if r.id == "pick_and_place")

# 40 s per cycle, 600 cycles per shift; 10 % searching, 10 % walking
ABLAUF = Ablauf(verschwendung_anteile={"Suchen": 0.1, "Gehen": 0.1}, mittel_zyklus_s=40.0, zykluszeit_median_s=40.0, zyklen_pro_schicht=600)
BETRIEB = Betrieb(schichten_pro_tag=2, arbeitstage_pro_jahr=220, stundensatz=50.0)


def test_improve_minutes_and_euro():
    v = verbessern(CFG, ABLAUF, BETRIEB)
    # waste per type: 0.1 * 40 s * 600 / 60 = 40 min; avoidable: 40 * 0.8 + 40 * 0.5 = 52 min
    assert v["je_typ"]["Suchen"] == {"min_schicht": 40.0, "vermeidbarer_anteil": 0.8, "vermeidbar_min_schicht": 32.0}
    assert v["je_typ"]["Gehen"]["vermeidbar_min_schicht"] == 20.0
    assert v["verschwendung_min_schicht"] == 80.0
    assert v["verbesserung_min_schicht"] == 52.0
    assert v["vermeidbar_anteil_zyklus"] == pytest.approx(0.13)
    # 52 min * 2 shifts * 220 days / 60 * 50 euro
    assert v["euro_jahr"] == round(52 * 2 * 220 / 60 * 50)


def test_improve_without_cost_inputs_names_them():
    v = verbessern(CFG, ABLAUF, Betrieb())
    assert v["verbesserung_min_schicht"] == 52.0 and v["euro_jahr"] is None
    assert v["fehlende_angaben"] == ["Schichten pro Tag", "Arbeitstage pro Jahr", "Vollkosten pro Stunde"]


def test_type_without_avoidable_share_counts_zero():
    # the expert classified "Prüfen" as waste: in the waste minutes, but not avoidable by default
    a = Ablauf({"Prüfen": 0.1, "Suchen": 0.1}, 40.0, 40.0, 600)
    v = verbessern(CFG, a, BETRIEB)
    assert v["verschwendung_min_schicht"] == 80.0 and v["verbesserung_min_schicht"] == 32.0


def test_automate_current_process():
    a = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), BETRIEB, verbessert=False)
    stunden = 40 * 600 * 2 * 220 / 3600  # 2933.3 h in cycles per year
    assert a["basis"] == "aktueller Ablauf" and a["zykluszeit_basis_s"] == 40.0 and a["vermeidbar_s"] == 0
    assert a["stunden_jahr"] == [round(stunden * 0.6, 1), round(stunden * 0.85, 1)]
    brutto = (stunden * 0.6 * 50, stunden * 0.85 * 50)
    assert a["euro_jahr_brutto"] == [round(brutto[0]), round(brutto[1])]
    # running costs of pick and place: 15 to 25 % of the gross savings
    assert a["betriebskosten_anteil"] == [0.15, 0.25]
    assert a["betriebskosten_euro_jahr"] == [round(brutto[0] * 0.15), round(brutto[1] * 0.25)]
    netto = (brutto[0] * 0.75, brutto[1] * 0.85)
    assert a["euro_jahr_netto"] == [round(netto[0]), round(netto[1])]
    # default investment of the type: 60,000 to 120,000 euro, paid back from the net savings
    assert a["investition_euro"] == [60000, 120000] and a["investition_quelle"] == "Standardwert für Pick and Place"
    assert a["amortisation_jahre"] == [round(60000 / netto[1], 1), round(120000 / netto[0], 1)]


def test_running_costs_lengthen_payback():
    ohne = PICK.model_copy(update={"betriebskosten_anteil": (0.0, 0.0)})
    a0 = automatisieren(CFG, ohne, ABLAUF, (40.0, 600), BETRIEB, verbessert=False)
    a = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), BETRIEB, verbessert=False)
    assert a0["euro_jahr_netto"] == a0["euro_jahr_brutto"] and a0["betriebskosten_euro_jahr"] == [0, 0]
    assert a["amortisation_jahre"][0] > a0["amortisation_jahre"][0] and a["amortisation_jahre"][1] > a0["amortisation_jahre"][1]
    # cautious bound: 1 / (1 - 0.25) times longer
    assert a["amortisation_jahre"][1] == pytest.approx(a0["amortisation_jahre"][1] / 0.75, abs=0.1)


def test_automate_on_the_improved_process():
    akt = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), BETRIEB, verbessert=False)
    verb = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), BETRIEB, verbessert=True)
    # cycle time minus avoidable waste: 40 s * (1 - 0.1 * 0.8 - 0.1 * 0.5) = 34.8 s
    assert verb["basis"] == "verbesserter Ablauf"
    assert verb["vermeidbar_s"] == pytest.approx(5.2) and verb["zykluszeit_basis_s"] == pytest.approx(34.8)
    stunden = 34.8 * 600 * 2 * 220 / 3600
    assert verb["stunden_jahr"] == [round(stunden * 0.6, 1), round(stunden * 0.85, 1)]
    assert verb["stunden_jahr"][1] / akt["stunden_jahr"][1] == pytest.approx(0.87, abs=1e-3)
    # less to automate, so the payback takes longer
    assert verb["amortisation_jahre"][1] > akt["amortisation_jahre"][1]


def test_customer_investment_overrides_default():
    b = Betrieb(2, 220, 50.0, investition_euro=(30000, 40000))
    a = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), b, verbessert=False)
    assert a["investition_euro"] == [30000, 40000] and a["investition_quelle"] == "Kundenangabe"


def test_automate_without_cost_rate_gives_hours_only():
    a = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), Betrieb(2, 220), verbessert=False)
    assert a["stunden_jahr"] is not None and a["euro_jahr_netto"] is None and a["amortisation_jahre"] is None
    assert a["fehlende_angaben"] == ["Vollkosten pro Stunde"]
    a = automatisieren(CFG, PICK, ABLAUF, (40.0, 600), Betrieb(), verbessert=False)
    assert a["stunden_jahr"] is None and "Schichten pro Tag" in a["fehlende_angaben"]


def test_automate_needs_cycle_and_type():
    assert not automatisieren(CFG, PICK, ABLAUF, (None, None), BETRIEB, False)["berechnet"]
    assert automatisieren(CFG, None, ABLAUF, (40.0, 600), BETRIEB, False)["grund"] == "Kein Automatisierungstyp festgelegt."
    assert not automatisieren(CFG, PICK, None, (40.0, 600), BETRIEB, verbessert=True)["berechnet"]


def test_automation_part_only_with_automation_recommendation():
    for emp in ("improve", "keep", None):
        w = wirtschaftlichkeit(CFG, emp, PICK, ABLAUF, (40.0, 600), BETRIEB)
        assert not w["automatisieren"]["berechnet"] and w["verbessern"]["berechnet"]
    assert wirtschaftlichkeit(CFG, "automate", PICK, ABLAUF, (40.0, 600), BETRIEB)["automatisieren"]["basis"] == "aktueller Ablauf"
    assert wirtschaftlichkeit(CFG, "improve-then-automate", PICK, ABLAUF, (40.0, 600), BETRIEB)["automatisieren"]["basis"] == "verbesserter Ablauf"
    assert wirtschaftlichkeit(CFG, "keep", None, None, (None, None), Betrieb())["hinweis"] == "Grobe Abschätzung, ersetzt kein Angebot."


def test_steckbrief_improve_then_automate_end_to_end():
    """Demo profile: the automation is computed on the improved process."""
    m = module_results("improve-then-automate")
    doc = steckbrief.build(CFG, "job", **m)
    w = doc["wirtschaftlichkeit"]
    kunde = PROFILE["improve-then-automate"]["kunde"]
    # avoidable share of the cycle: searching 9 % * 0.8 + walking 13 % * 0.5 = 13.7 %
    assert w["verbessern"]["vermeidbar_anteil_zyklus"] == pytest.approx(0.137)
    minuten = 0.137 * 38.4 * 690 / 60
    assert w["verbessern"]["verbesserung_min_schicht"] == pytest.approx(round(minuten, 1))
    assert w["verbessern"]["euro_jahr"] == round(minuten * 2 * 220 / 60 * 48)
    a = w["automatisieren"]
    assert a["basis"] == "verbesserter Ablauf" and a["typ"] == "Pick and Place"
    assert a["zykluszeit_basis_s"] == pytest.approx(38.4 * (1 - 0.137), abs=0.01)
    stunden = 38.4 * (1 - 0.137) * 690 * kunde["schichten_pro_tag"] * kunde["arbeitstage_pro_jahr"] / 3600
    assert a["stunden_jahr"] == pytest.approx([stunden * 0.6, stunden * 0.85], abs=0.1)
    assert w["hinweis"] == "Grobe Abschätzung, ersetzt kein Angebot."


def test_steckbrief_automate_uses_current_process():
    w = steckbrief.build(CFG, "job", **module_results("automate"))["wirtschaftlichkeit"]["automatisieren"]
    assert w["basis"] == "aktueller Ablauf" and w["vermeidbar_s"] == 0 and w["zykluszeit_basis_s"] == 20.0
