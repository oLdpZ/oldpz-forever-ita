"""The Italian lint's hard rules: a glossary name of a place, faction, class or race kept in English fails the
row (`glossary_term`, an error); an item or spell name only warns; a player token of the English
(`{name}` / `{class}` / `{race}`) the Italian drops fails it (`placeholder_lost`)."""

import json

from wfj.dev import glossary_it as gl
from wfj.dev import translate_batch as tb
from wfj.dev import translate_lint as tl
from wfj.io.jsonl_store import Store


def _lint(tmp_path, row, it):
    batch, draft = tmp_path / "b.jsonl", tmp_path / "d.jsonl"
    tb.write_jsonl(batch, [row])
    tb.write_jsonl(draft, [{"ref": row["ref"], "it": it}])
    ok, failures = tl.lint(batch, draft, set())
    return ok, failures, tl.warnings(batch, draft)


def _row(en, glossary=None):
    row = {"ref": "r1", "kind": "progress", "en": en, "targets": [[1, "progress"]]}
    if glossary is not None:
        row["glossary"] = glossary
    return row


def test_a_zone_kept_in_english_is_an_error(tmp_path):
    row = _row("Go to Stormwind City.", [["Stormwind City", "Roccavento", "zona"]])
    ok, failures, _ = _lint(tmp_path, row, "Vai a Stormwind City.")
    assert ok == []
    assert failures == {"r1": ["glossary_term:Stormwind City→Roccavento"]}
    ok, failures, warned = _lint(tmp_path, row, "Vai a Roccavento.")
    assert failures == {} and len(ok) == 1 and warned == {}


def test_every_name_kind_is_an_error():
    for kind in ("zona", "fazione", "classe", "razza"):
        row = _row("Ask the Priest.", [["Priest", "Sacerdote", kind]])
        assert tl.glossary_errors(row, "Chiedi al Priest.") == ["glossary_term:Priest→Sacerdote"], kind


def test_an_item_or_spell_kept_in_english_only_warns(tmp_path):
    for kind in ("oggetto", "abilita"):
        row = _row("Bring me a Linen Cloth.", [["Linen Cloth", "Stoffa di Lino", kind]])
        ok, failures, warned = _lint(tmp_path, row, "Portami una Linen Cloth.")
        assert failures == {} and len(ok) == 1, kind
        assert warned == {"r1": ["glossary_term:Linen Cloth→Stoffa di Lino"]}, kind


def test_an_untyped_glossary_pair_still_only_warns(tmp_path):
    ok, failures, warned = _lint(tmp_path, _row("Go to Stormwind City.", [["Stormwind City", "Roccavento"]]),
                                 "Vai a Stormwind City.")
    assert failures == {} and warned == {"r1": ["glossary_term:Stormwind City→Roccavento"]}


def test_either_form_of_a_class_word_will_do():
    row = _row("Ask a Priest.", [["Priest", "Sacerdote", "classe"], ["Priest", "Sacerdotessa", "classe"]])
    assert tl.glossary_errors(row, "Chiedi a una sacerdotessa.") == []


def test_a_class_word_inside_a_longer_proper_name_only_warns(tmp_path):
    row = _row("Go to the Mage Quarter.", [["Mage", "Mago", "classe"]])
    ok, failures, warned = _lint(tmp_path, row, "Vai al Quartiere dei Maghi.")
    assert failures == {} and len(ok) == 1
    assert warned == {"r1": ["glossary_term:Mage→Mago"]}
    shadow = _row("Speak to Shadow Priest Sarvis.", [["Priest", "Sacerdote", "classe"]])
    assert tl.glossary_errors(shadow, "Parla con Sarvis, Sacerdote dell'Ombra.") == []
    assert tl.glossary_errors(_row("Join the Night Watch Mage Guild.", [["Mage", "Mago", "razza"]]),
                              "Unisciti alla Gilda.") == []


def test_a_class_word_on_its_own_is_still_an_error():
    for en in ("Speak to the mage.", "You are a brave Mage.", "Mage, come here."):
        row = _row(en, [["Mage", "Mago", "classe"], ["Mage", "Maga", "classe"]])
        assert tl.glossary_errors(row, "Parla con lo stregone.") == ["glossary_term:Mage→Mago/Maga"], en


def test_a_zone_word_inside_a_creature_name_only_warns(tmp_path):
    row = _row("Kill 10 Redridge Mongrels.", [["Redridge", "Crestarossa", "zona"]])
    ok, failures, warned = _lint(tmp_path, row, "Uccidi 10 Redridge Mongrel.")
    assert failures == {} and len(ok) == 1
    assert warned == {"r1": ["glossary_term:Redridge→Crestarossa"]}


def test_a_zone_on_its_own_is_still_an_error():
    row = _row("Go to Redridge.", [["Redridge", "Crestarossa", "zona"]])
    assert tl.glossary_errors(row, "Vai a Redridge.") == ["glossary_term:Redridge→Crestarossa"]


def test_a_place_or_faction_inside_any_longer_name_only_warns_an_accepted_trade_off():
    # a name like "Ironforge Siege Brigade" may well want "Forgiardente": the lint cannot tell, so it warns
    for kind in ("zona", "fazione"):
        row = _row("Report to the Ironforge Siege Brigade.", [["Ironforge", "Forgiardente", kind]])
        assert tl.glossary_errors(row, "Fai rapporto alla Brigata d'Assedio.") == [], kind
        assert tl.glossary_warnings(row, "Fai rapporto alla Brigata d'Assedio.") == [
            "glossary_term:Ironforge→Forgiardente"], kind


def test_a_dropped_player_token_is_placeholder_lost():
    row = _row("Thank you, {name}.")
    assert "placeholder_lost:{name}" in tl.check_row(row, "Grazie.", set())
    assert tl.check_row(row, "Grazie, {name}.", set()) == []
    both = _row("A {race} {class}, {name}?")
    assert [r for r in tl.check_row(both, "Un {class}?", set()) if r.startswith("placeholder_lost")] == [
        "placeholder_lost:{race}", "placeholder_lost:{name}"]


def test_a_gender_choice_may_become_an_italian_pair_or_a_neutral_form():
    for en in ("Thank you, $Gsir:madam;.", "Thank you, <sir/madam>."):
        row = _row(en)
        for it in ("Grazie, <signore/signora>.", "Grazie davvero."):
            assert not [r for r in tl.check_row(row, it, set()) if r.startswith("placeholder_lost")], (en, it)


def test_cut_gives_each_glossary_term_its_kind(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    (tmp_path / "docs" / "content").mkdir(parents=True)
    (tmp_path / "docs" / "content" / "translation-style-guide.md").write_text("# guide\n\nversion: sg1\n")
    (tmp_path / "pipeline").mkdir()
    gl.write_glossary(tmp_path / "pipeline" / gl.GLOSSARY, [
        ("zona", 1519, "Stormwind City", "Roccavento"), ("oggetto", 2589, "Linen Cloth", "Stoffa di Lino")])
    Store(data, english=True).save("quest", [
        {"id": 1, "field": "progress", "en": "Bring Linen Cloth to Stormwind City.", "hash": "0" * 16,
         "src": "vmangos@13b49dc"},
    ])
    out = tmp_path / "batch.jsonl"
    (row,) = tb.cut(data, "progress", 10, out)
    assert row["glossary"] == [["Linen Cloth", "Stoffa di Lino", "oggetto"], ["Stormwind City", "Roccavento", "zona"]]
    assert json.loads(out.read_text(encoding="utf-8").splitlines()[0])["glossary"] == row["glossary"]


def test_plural_of_a_race_term_passes():
    row = _row("The Earthen are ancient.", [["Earthen", "Terrigeno", "razza"]])
    assert tl.glossary_errors(row, "I Terrigeni sono antichi.") == []


def test_plural_of_a_multiword_race_term_passes():
    row = _row("Night elves live here.", [["Night Elf", "Elfo della Notte", "razza"]])
    assert tl.glossary_errors(row, "Qui vivono gli elfi della notte.") == []


def test_feminine_plural_passes():
    row = _row("The Earthen are ancient.", [["Earthen", "Terrigeno", "razza"], ["Earthen", "Terrigena", "razza"]])
    assert tl.glossary_errors(row, "Le Terrigene sono antiche.") == []


def test_a_different_word_still_fails():
    row = _row("The Earthen are ancient.", [["Earthen", "Terrigeno", "razza"]])
    assert tl.glossary_errors(row, "I Terrestri sono antichi.") == ["glossary_term:Earthen→Terrigeno"]


def test_time_glued_to_pm_keeps_its_number(tmp_path):
    row = _row("Come back at 6PM.")
    for it, bad in (("Torna alle 18.", False), ("Torna alle 6 di sera.", False), ("Torna alle 7 di sera.", True)):
        _, failures, _ = _lint(tmp_path, row, it)
        assert any(r.startswith("numbers_changed") for r in failures.get("r1", [])) == bad, it


def test_a_plural_is_a_whole_word_not_a_substring():
    row = _row("Ask the Mage.", [["Mage", "Mago", "classe"]])
    assert tl.glossary_errors(row, "Una magia antica.") == ["glossary_term:Mage→Mago"]
    assert tl.glossary_errors(row, "Ecco i magi.") == []


def test_times_with_a_range_and_noon(tmp_path):
    for en, it, bad in (("Open 2pm-4pm.", "Dalle 14 alle 16.", False), ("Open 2pm-4pm.", "Dalle 2 alle 5.", True),
                        ("Meet at 12PM.", "Alle 12.", False), ("Meet at 12PM.", "Alle 13.", True)):
        _, failures, _ = _lint(tmp_path, _row(en), it)
        assert any(r.startswith("numbers_changed") for r in failures.get("r1", [])) == bad, (en, it)
