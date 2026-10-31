"""Arbeitsplatz-Check of the website (WEBSITE_PLAN §4.2) in the shared
configuration: answers set metrics, the Steckbrief scores and rules decide.
The website computes the same in TypeScript (src/lib/scoring.ts); the
expected values here are the reference for its tests."""
import copy
import itertools
import json
import os
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.services.workplace import scoring, scoring_config
from backend.app.services.workplace.scoring_config import ScoringConfig

CFG = scoring_config.get()
RAW = json.loads(scoring_config.DEFAULT_PATH.read_text(encoding="utf-8"))
ROOT = Path(__file__).resolve().parents[2]
WEBSITE = Path(os.environ.get("MOTAVI_WEBSITE_REPO", ROOT.parent / "motavi"))

# WEBSITE_PLAN Phase 3 acceptance: four profiles, four different recommendations
PROFILE = {
    # values set anew on 31.10.2026 (posture index 1 to 10, docs/HALTUNGSINDEX.md)
    "verschwendungsreich": ([1, 1, 2, 1, 3, 2, 1, 1], (83, 41, "improve")),
    "repetitiv_und_bereinigt": ([3, 3, 0, 0, 0, 1, 3, 2], (21, 87, "automate")),
    "repetitiv_mit_verschwendung": ([2, 2, 1, 0, 2, 2, 2, 2], (65, 78, "improve-then-automate")),
    "hochvariabel": ([0, 0, 3, 2, 1, 0, 0, 0], (30, 7, "keep")),
}


def check(cfg: ScoringConfig, auswahl: list[int]):
    werte: dict = {}
    for frage, i in zip(cfg.arbeitsplatz_check.fragen, auswahl):
        werte.update(frage.antworten[i].werte)
    werte["belastung_index"] = scoring.index(cfg.belastung, werte).wert
    werte["handhabbarkeit_index"] = scoring.index(cfg.handhabbarkeit, werte).wert
    v = scoring.score(cfg.verbesserungs_score, werte)
    a = scoring.score(cfg.automatisierungs_score, werte)
    return v, a, scoring.empfehlung(cfg, v, a), scoring.vorrang(cfg, werte["reba_mittel"])


def test_eight_questions_with_four_answers():
    assert [f.id for f in CFG.arbeitsplatz_check.fragen] == [
        "wiederholung", "gleichfoermigkeit", "varianten", "teile", "verschwendung", "haltung", "zeitanteil", "besetzung"]
    assert all(len(f.antworten) == 4 for f in CFG.arbeitsplatz_check.fragen)


@pytest.mark.parametrize("name", list(PROFILE))
def test_four_profiles_four_recommendations(name):
    auswahl, (v_soll, a_soll, emp_soll) = PROFILE[name]
    v, a, e, _ = check(CFG, auswahl)
    assert (v.wert, a.wert, e.id) == (v_soll, a_soll, emp_soll)
    assert v.vollstaendig and a.vollstaendig  # every criterion answered


def test_priority_from_posture_answer():
    *_, vor = check(CFG, [1, 1, 1, 1, 1, 3, 1, 1])  # "ständig" gebückt, über Kopf oder gedreht
    assert vor.vorrangig
    *_, vor = check(CFG, [1, 1, 1, 1, 1, 2, 1, 1])  # "häufig": index 7, stage high
    assert vor.vorrangig
    *_, vor = check(CFG, [1, 1, 1, 1, 1, 1, 1, 1])  # "gelegentlich": index 5
    assert not vor.vorrangig


def test_no_bias_towards_automation():
    """Leitplanke 4: over all 65,536 answer combinations every recommendation occurs,
    and automation does not dominate."""
    n = Counter(check(CFG, list(p))[2].id for p in itertools.product(range(4), repeat=8))
    assert set(n) == {"improve-then-automate", "improve", "automate", "keep"}
    mit_auto = n["improve-then-automate"] + n["automate"]
    assert mit_auto / sum(n.values()) < 0.5


@pytest.mark.parametrize("change, message", [
    (lambda c: c["arbeitsplatz_check"]["fragen"][0]["antworten"][0]["werte"].update(stundensatz=50), "unbekannte Kennzahl"),
    (lambda c: c["arbeitsplatz_check"]["fragen"].pop(0), "keine Frage liefert zyklen_pro_schicht"),
    (lambda c: c["arbeitsplatz_check"]["fragen"][1].update(id="wiederholung"), "Frage-ids doppelt"),
    (lambda c: c["arbeitsplatz_check"]["fragen"][0]["antworten"][1].update(id="unter_50"), "Antwort-ids doppelt"),
])
def test_invalid_check_rejected(change, message):
    raw = copy.deepcopy(RAW)
    change(raw)
    with pytest.raises(ValidationError, match=message):
        ScoringConfig.model_validate(raw)


@pytest.mark.skipif(not (WEBSITE / "config" / "workplace_scoring.json").exists(), reason="Repo motavi nicht ausgecheckt")
def test_website_copy_is_identical():
    """The website reads a copy (motavi: config/workplace_scoring.json, npm run sync:scoring)."""
    kopie = (WEBSITE / "config" / "workplace_scoring.json").read_bytes()
    assert kopie == scoring_config.DEFAULT_PATH.read_bytes(), "Website-Kopie veraltet: im Repo motavi `npm run sync:scoring` ausführen"
