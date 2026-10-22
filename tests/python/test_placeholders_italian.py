"""Italian gender pairs (`<il/la>`, `<è/é>`) and the class / race words the addon picks by the player's sex."""

from wfj.core import placeholders
from wfj.dev import translate_lint


def test_a_pair_of_accented_italian_words_is_a_pair():
    assert placeholders.split_pairs("<è/é>") == [("è", "é")]
    assert placeholders.split_pairs("<il/la> più <caro/cara>") == [("il", "la"), ("caro", "cara")]
    assert placeholders.tokens("Sei un<o/a> coraggios<o/a>.") == ["<a/b>", "<a/b>"]
    assert placeholders.unknown("<il/la> più <caro/cara> <è/é>") == []
    # digits, punctuation and spaces are not words: the addon would show both forms, so validate refuses them
    assert placeholders.unknown("<1/2> <Mr./Ms.>") == ["<1/2>", "<Mr./Ms.>"]


def test_a_gender_pair_is_not_a_leftover_in_the_draft_lint():
    row = {"ref": "r", "kind": "completion", "en": "Thanks, sir.", "targets": [[1, "completion"]]}
    reasons = translate_lint.check_row(row, "Grazie, <signore/signora>.", set())
    assert not any(r.startswith("leftover") for r in reasons), reasons


def test_the_seed_names_have_both_forms_for_every_playable_class_and_race():
    names = placeholders.PLACEHOLDER_NAMES
    assert names["CLASS"]["PRIEST"] == ("Sacerdote", "Sacerdotessa")
    assert names["RACE"]["NightElf"] == ("Elfo della Notte", "Elfa della Notte")
    assert set(names["CLASS"]) == {"WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "SHAMAN", "MAGE", "WARLOCK",
                                   "DRUID"}
    assert set(names["RACE"]) == {"Human", "Orc", "Dwarf", "NightElf", "Scourge", "Tauren", "Gnome", "Troll"}


def test_generate_emits_data_placeholders_lua(it_planned):
    from wfj.cmd import generate

    planned = it_planned
    text = planned["Data/Placeholders.lua"]
    assert 'PRIEST = { m = "Sacerdote", f = "Sacerdotessa" }' in text
    assert 'NightElf = { m = "Elfo della Notte", f = "Elfa della Notte" }' in text
    assert "WFJ.PlaceholderNames = {" in text
    assert generate.toc_files(planned)[:3] == ["Data/Meta.lua", "Data/Vectors.lua", "Data/Placeholders.lua"]
