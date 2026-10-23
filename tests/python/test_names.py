"""Marked names (spec §8, "stile dei nomi"): the pipeline writes a glossary name the Italian carries as
`⟦<english>=<italian>⟧`, and the addon shows either form. `core/names` is the Python half; `Core/Names.lua`
the Lua twin (vectors/names_vectors.*)."""

import json

import pytest

from wfj.core import align, names
from wfj.dev import gen_names_vectors
from wfj.dev.glossary_it import Matcher

SW = ("Stormwind City", "Roccavento", "zona")


def test_mark_resolve_round_trip():
    marked = names.mark_names("Porta queste pelli a Roccavento.", [SW])
    assert marked == "Porta queste pelli a ⟦Stormwind City=Roccavento⟧."
    assert names.resolve(marked, "it") == "Porta queste pelli a Roccavento."
    assert names.resolve(marked, "en") == "Porta queste pelli a Stormwind City."
    assert names.strip_marks(marked) == "Porta queste pelli a Roccavento."


def test_longest_first_one_marker():
    glossary = [("Stormwind", "Roccavento", "fazione"), SW]
    assert names.mark_names("Vai a Roccavento.", glossary) == "Vai a ⟦Stormwind City=Roccavento⟧."
    # longest Italian first: the shorter form inside the longer one is never marked on its own
    g2 = [("Elwynn", "Elwynn", "zona"), ("Elwynn Forest", "Foresta di Elwynn", "zona")]
    assert names.mark_names("Nella Foresta di Elwynn.", g2) == "Nella ⟦Elwynn Forest=Foresta di Elwynn⟧."


def test_classes_and_races_are_never_marked():
    g = [("Priest", "Sacerdote", "classe"), ("Human", "Umano", "razza")]
    assert names.mark_names("Il Sacerdote umano e un Umano.", g) == "Il Sacerdote umano e un Umano."


def test_idempotent_and_whole_word():
    once = names.mark_names("Roccavento e Roccaventosa.", [SW])
    assert once == "⟦Stormwind City=Roccavento⟧ e Roccaventosa."
    assert names.mark_names(once, [SW]) == once


def test_a_term_with_the_marker_syntax_is_not_marked():
    assert names.mark_names("Vai a A=B.", [("X=Y", "A=B", "zona")]) == "Vai a A=B."
    assert names.mark_names("Vai a Roccavento.", [("Storm⟧", "Roccavento", "zona")]) == "Vai a Roccavento."


def test_mark_from_english_only_marks_terms_both_sides_hold():
    m = Matcher([("zona", 1, "Stormwind City", "Roccavento"), ("zona", 2, "Goldshire", "Borgodoro")])
    en = "Take these pelts to Stormwind City."
    assert names.mark_from_english("Porta le pelli a Roccavento, non a Borgodoro.", en, m) == (
        "Porta le pelli a ⟦Stormwind City=Roccavento⟧, non a Borgodoro."
    )
    assert names.mark_from_english("Testo.", en, None) == "Testo."
    assert names.mark_from_english("Roccavento", None, m) == "Roccavento"


def test_numbers_are_counted_on_the_resolved_text():
    # the plan's example, and one whose digit is a number run of its own (the marker holds it twice)
    cases = (("Vai al ⟦Sector 7G=Settore 7G⟧.", "Go to Sector 7G."), ("Al ⟦Sector 7=Settore 7⟧.", "To Sector 7."))
    for it, en in cases:
        assert align.check_numbers(it, en)[1] == []
        assert align.check_numbers(names.resolve(it, "en"), en)[1] == []


def test_names_vectors_match_regeneration(root, tmp_path):
    gen_names_vectors.write(tmp_path)
    for name in ("names_vectors.jsonl", "names_vectors.lua"):
        assert (tmp_path / name).read_text(encoding="utf-8") == (root / "vectors" / name).read_text(
            encoding="utf-8"
        ), name
    rows = [json.loads(x) for x in (root / "vectors/names_vectors.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) >= 6
    for r in rows:
        assert names.resolve(r["text"], "it") == r["it"]
        assert names.resolve(r["text"], "en") == r["en"]


THE_CASES = [
    ("la ⟦The Bulwark=Il Baluardo⟧", "la Bulwark"),
    ("Il ⟦The Great Sea=Mare Infinito⟧", "Il Great Sea"),
    ("verso ⟦The Barrens=Savane⟧", "verso The Barrens"),
    ("Nelle ⟦The Barrens=Savane⟧ e dall'⟦The Den=Antro del Tirocinio⟧.", "Nelle Barrens e dall'Den."),
    ("DELLA ⟦The Barrens=Savane⟧", "DELLA Barrens"),
    ("Isola ⟦The Barrens=Savane⟧", "Isola The Barrens"),  # "la" inside a word is no article
    ("le ⟦Thelsamar=Thelsamar⟧ e la ⟦the Barrens=Savane⟧", "le Thelsamar e la the Barrens"),
]


@pytest.mark.parametrize(("text", "en"), THE_CASES)
def test_english_style_drops_the_after_an_italian_article(text, en):
    """Style "en": an English name starting "The " right after an Italian article or articulated preposition
    loses its "The " ("la The Bulwark" → "la Bulwark"); the Italian style is untouched."""
    assert names.resolve(text, "en") == en
    assert names.resolve(text, "it") == names.MARK.sub(lambda m: m.group(2), text)


def test_english_kinds_mark_the_english_left_in_the_italian():
    """`english_kinds`: an NPC name the Italian left in English is marked too (the unit table's Italian as the
    form), longest first across both forms, and never inside a marker."""
    g = [("Defias Thug", "Brigante Defias", "creatura"), ("Defias Thug Leader", "Capo dei Briganti", "creatura"),
         SW]
    it = "Il Defias Thug Leader e un Brigante Defias a Stormwind City."
    assert names.mark_names(it, g, english_kinds={"creatura"}) == (
        "Il ⟦Defias Thug Leader=Capo dei Briganti⟧ e un ⟦Defias Thug=Brigante Defias⟧ a Stormwind City."
    )
    assert names.mark_names(it, g) == "Il Defias Thug Leader e un ⟦Defias Thug=Brigante Defias⟧ a Stormwind City."
    once = names.mark_names(it, g, english_kinds={"creatura"})
    assert names.mark_names(once, g, english_kinds={"creatura"}) == once
