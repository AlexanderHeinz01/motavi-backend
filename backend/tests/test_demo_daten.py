"""Demo data of the website (repo motavi, src/content/demo/*.json) against the
export schema (docs/steckbrief_schema.json) and the shared configuration
(config/workplace_scoring.json): automation types and the rules of the tool.

The website repo is expected next to this one (../motavi) or under
MOTAVI_WEBSITE_REPO; without it the tests are skipped.
"""
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from backend.app.services.workplace import scoring_config

ROOT = Path(__file__).resolve().parents[2]
WEBSITE = Path(os.environ.get("MOTAVI_WEBSITE_REPO", ROOT.parent / "motavi"))
DEMO_DIR = WEBSITE / "src" / "content" / "demo"
SCHEMA = json.loads((ROOT / "docs" / "steckbrief_schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
CFG = scoring_config.get()
TYPEN = {r.id: r.name for r in CFG.automatisierungstypen.regeln}

DATEIEN = sorted(DEMO_DIR.glob("*.json")) if DEMO_DIR.exists() else []
pytestmark = pytest.mark.skipif(not DATEIEN, reason=f"Demo-Daten der Website nicht gefunden ({DEMO_DIR})")


def lade(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_all_four_recommendations_present():
    assert sorted(lade(p)["empfehlung_id"] for p in DATEIEN) == sorted(["improve-then-automate", "improve", "automate", "keep"])


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: p.name)
def test_valid_against_schema(datei):
    fehler = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in VALIDATOR.iter_errors(lade(datei))]
    assert fehler == []


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: p.name)
def test_marked_as_example(datei):
    d = lade(datei)
    assert d["beispiel"] is True and d["arbeitsplatz"].startswith("Beispiel")


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: p.name)
def test_automation_type_from_the_configuration(datei):
    """Only types of the shared configuration, and only with a recommendation with automation."""
    d = lade(datei)
    if d["empfehlung_id"] in CFG.empfehlung.mit_automatisierung:
        assert d["typ_vorschlag"] in TYPEN.values(), f"{d['typ_vorschlag']!r} ist kein Typ aus {sorted(TYPEN.values())}"
        if d.get("typ_id") is not None:
            assert TYPEN[d["typ_id"]] == d["typ_vorschlag"]
    else:
        assert d["typ_vorschlag"] is None and d.get("typ_id") is None
        assert d["stunden_auto_jahr_bandbreite"] is None


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: p.name)
def test_like_the_tool_without_cycle(datei):
    """Without a recurring cycle the tool has no process steps and nothing derived from them."""
    d = lade(datei)
    if d["zykluszeit_median_s"] is None:
        assert d["ablaufschritte"] == [] and d["anteile_ablauf"] is None
        assert d["zeitanteil_in_zyklen"] is None and d["zyklen_pro_schicht"] is None
        assert d["verbesserung_min_schicht"] is None
    else:
        assert d["ablaufschritte"] and d["anteile_ablauf"] is not None


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: p.name)
def test_step_types_and_classes_from_the_configuration(datei):
    for s in lade(datei)["ablaufschritte"]:
        assert s["typ"] in CFG.schritt_typen
        assert s["klasse"] == CFG.schritt_typen[s["typ"]], f"{s['typ']}: Standardeinstufung ist {CFG.schritt_typen[s['typ']]}"


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: p.name)
def test_recommendation_follows_the_thresholds(datei):
    d = lade(datei)
    e = CFG.empfehlung
    hv = "hoch" if d["verbesserungs_score"] >= e.schwelle_verbesserung else "niedrig"
    ha = "hoch" if d["automatisierungs_score"] >= e.schwelle_automatisierung else "niedrig"
    regel = next(r for r in e.regeln if r.verbesserung == hv and r.automatisierung == ha)
    assert d["empfehlung_id"] == regel.empfehlung and d["empfehlung"] == e.texte[regel.empfehlung]
    assert d["vorrangig"] == (d["reba_mittel"] >= CFG.vorrang.reba_mittel_ab)
