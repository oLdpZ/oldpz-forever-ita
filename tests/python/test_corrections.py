"""ADR-012: human decisions survive regeneration, a correction ranks first, and the correction shape."""

from wfj.core import decisions, paragraphs
from wfj.core.model import validate_line
from wfj.core.status import Scope, decide

DATE = "2026-09-13"

CORRECTION = {
    "class": "correction",
    "translator": "Tammy",
    "source": "correction@2026-09-14",
    "imported": "2026-09-14",
    "corrects": "cqjt@3446c82",
    "note": "a name spelled as the English spells it",
}
RULING = {"ruling": "accept", "by": "maintainer", "date": "2026-09-14"}


def test_carried_is_canonical_regardless_of_variant_order():
    a = {"class": "correction", "translator": "A", "source": "correction@2026-09-14", "imported": DATE}
    b = {"class": "human", "translator": "B", "source": "qjp@0.5.8", "imported": DATE}
    line = {"id": 7, "field": "title", "it": "x", "provenance": b, "ruling": RULING, "conflicts": [{"it": "y", "provenance": a}]}
    swapped = {"id": 7, "field": "title", "it": "y", "provenance": a, "conflicts": [{"it": "x", "provenance": b, "ruling": RULING}]}
    assert decisions.carried([line]) == decisions.carried([swapped])
    assert [v["it"] for _, _, v in decisions.carried([line])] == ["y", "x"]  # corrections first


# ---- ranking -----------------------------------------------------------------------------------------------

EN_RAW = "Greetings, $N. Kill the Thistle Boar.$B$BThe rains were heavy.$B$BJourney forth, young $c."
EN_NORM = EN_RAW.replace("$B$B", " ").replace("$N", "Reyn").replace("$c", "druid")
IT3 = "御機嫌よう、{name}。Thistle Boarを倒せ。\n\n今年の春は雨が多かった。\n\n若き{class}よ、行け。"
IT2 = "御機嫌よう、{name}。Thistle Boarを倒せ。\n\n今年の春は雨が多かった、若き{class}よ、行け。"


def _scope() -> Scope:
    return Scope(kind="quest", fields={"description": EN_NORM}, raw={"description": EN_RAW}, hashes={"description": "h"}, src="pfquest@7786596")


def _line(it: str, prov: dict, conflicts: list) -> dict:
    return {"id": 456, "field": "description", "it": it, "status": "pending", "checks": [], "provenance": prov,
            "english": None, "reasons": [], "conflicts": conflicts}


QJP_AZ = {"class": "human", "translator": "Az", "source": "qjp@0.5.8", "imported": DATE}
FIX = {"class": "correction", "translator": "Az", "source": "correction@2026-09-14", "imported": "2026-09-14",
       "corrects": "qjp@0.5.8", "note": "Thistle bore → Thistle Boar"}


def test_a_passing_correction_beats_a_passing_import_with_more_paragraphs():
    d = decide(_line(IT3 + "。", QJP_AZ, [{"it": IT2, "provenance": FIX}]), _scope(), set(), "h")
    assert d.status == "trusted" and d.winner == 1 and "tiebreak" in d.checks


def test_a_passing_correction_beats_an_equal_import_from_any_source():
    cqjt = {"class": "human", "translator": "Tammy", "source": "cqjt@3446c82", "imported": DATE}
    d = decide(_line(IT3 + "。", cqjt, [{"it": IT3, "provenance": FIX}]), _scope(), set(), "h")
    assert d.winner == 1


def test_a_failing_correction_does_not_ship_and_does_not_block_a_passing_import():
    wrong = IT3.replace("Thistle Boar", "3 Thistle Boar")  # a number the English does not have
    d = decide(_line(IT3, QJP_AZ, [{"it": wrong, "provenance": FIX}]), _scope(), set(), "h")
    assert d.status == "trusted" and d.winner == 0


# ---- shape -------------------------------------------------------------------------------------------------


def test_a_correction_needs_a_translator_and_corrects_even_inside_conflicts():
    no_translator = {k: v for k, v in FIX.items() if k != "translator"}
    no_corrects = {k: v for k, v in FIX.items() if k != "corrects"}
    assert any("correction provenance needs a translator" in p for p in validate_line("quest", _line(IT3, no_translator, [])))
    assert any("needs corrects" in p for p in validate_line("quest", _line(IT3, no_corrects, [])))
    # the documented authoring path puts the correction in `conflicts`, validated there too
    waiting = _line(IT3, QJP_AZ, [{"it": IT2, "provenance": no_translator}])
    assert any("correction provenance needs a translator" in p for p in validate_line("quest", waiting))
    assert validate_line("quest", _line(IT3, QJP_AZ, [{"it": IT2, "provenance": FIX}])) == []


def test_a_correction_is_judged_by_the_layer_it_corrects():
    wiki_fix = {"class": "correction", "translator": "questjapanizer-wiki", "source": "correction@2026-09-14",
                "imported": "2026-09-14", "corrects": "cqjt@3446c82"}
    assert paragraphs.first_paragraph_only(wiki_fix)
    assert not paragraphs.first_paragraph_only({**wiki_fix, "corrects": "qjp@0.5.8"})
    assert not paragraphs.first_paragraph_only({k: v for k, v in wiki_fix.items() if k != "corrects"})


