"""`make coverage`: docs/operations/coverage.md measures what ships from the served English."""

from pathlib import Path

from wfj.dev import coverage


def test_nothing_to_translate_classes():
    why = coverage.nothing_to_translate("quest", "Kill 10 boars.", "<UNUSED> Test")
    assert why == "placeholder quest (never shown)"
    assert coverage.nothing_to_translate("quest", "Kill 10 boars.", "The Boar Hunt") is None
    assert coverage.nothing_to_translate("book", "Missing Text", None)
    assert coverage.nothing_to_translate("book", '<HTML><BODY><IMG src="x"/></BODY></HTML>', None)
    assert coverage.nothing_to_translate("book", "01101 10010", None)
    assert coverage.nothing_to_translate("book", "A page of prose.", None) is None


def test_the_committed_report_is_current(root: Path):
    # every data change re-runs `make coverage`: the committed doc matches the store (the date line aside)
    committed = (root / "docs" / "operations" / "coverage.md").read_text(encoding="utf-8")
    fresh = coverage.render(coverage.measure(root / "data"), "X")
    strip = lambda text: [ln for ln in text.splitlines() if not ln.startswith("> **Generated**")]  # noqa: E731
    assert strip(committed) == strip(fresh), "run `make coverage` and commit docs/operations/coverage.md"


def _store(tmp_path: Path):
    from wfj.io.jsonl_store import Store

    data = tmp_path / "data"
    (tmp_path / "pipeline").mkdir()
    for names in ("objective_names.txt", "area_names.txt"):
        (tmp_path / "pipeline" / names).write_text("", encoding="utf-8")
    english = [
        {"id": 133, "field": "description", "en": "Hurls a fireball.", "hash": "a", "src": "db2@1.60.1.70170"},
        # an aura nothing in a player's spellbook grants (a world buff): still served, still counted
        {"id": 7353, "field": "aura", "en": "Increased Spirit.", "hash": "b", "src": "db2@1.60.1.70170"},
        {"id": 9000, "field": "aura", "en": "Old English.", "hash": "c", "src": "wago@1.15.9.69722"},
    ]
    Store(data, english=True).save("spell", english)
    it = {"id": 133, "field": "description", "it": "火の玉を投げつけます。", "status": "unaligned"}
    Store(data).save("spell", [it])
    return data, Store


def test_every_served_spell_line_counts_and_an_uncounted_one_is_a_gap(tmp_path: Path):
    data, _ = _store(tmp_path)
    m = coverage.measure(data)
    spell = m["types"]["spell"]
    assert spell["english"] == 3  # no list narrows the denominator
    assert spell["shipped"] == 1
    # the world-buff aura has no Italian and no reason: a gap; the Classic Era line waits on a re-pull
    assert coverage.gaps(m) == {"spell": 1}


def test_a_stated_reason_is_not_a_gap(tmp_path: Path):
    data, store = _store(tmp_path)
    rejected = {"id": 7353, "field": "aura", "it": "x", "status": "rejected", "reasons": ["ruled_reject"]}
    store(data).save("spell", [*store(data).load("spell"), rejected])
    assert coverage.gaps(coverage.measure(data)) == {}


def test_make_coverage_refuses_an_inventory_from_another_build(capsys):
    assert coverage.main(["--build", "0.0.0.0"]) == 1
    assert "run `make served-columns`" in capsys.readouterr().out


def test_an_interface_line_off_the_key_list_needs_a_reason():
    keys, excluded = {"QUEST_LOG", "CustomizationChoice:1"}, {"CAA_SAMPLE_SPELLNAME"}
    assert coverage.ui_left_out("CAA_SAMPLE_SPELLNAME", keys, excluded) == coverage.UI_EXCLUDED
    assert coverage.ui_left_out("CustomizationChoice:54525", keys, excluded) == coverage.UI_FAMILY_LEFT_OUT
    # a GlobalString neither shipped nor excluded is a gap
    assert coverage.ui_left_out("NEW_STRING_THIS_BUILD", keys, excluded) is None


def test_a_template_that_prints_nothing_is_nothing_to_translate():
    assert coverage.nothing_to_translate("spell", "$@null\r\n$@null", None, "description")
    assert coverage.nothing_to_translate("spell", "$@null $@spelldesc5", None, "description") is None
    assert coverage.nothing_to_translate("item", "$@nullify", None, "description") is None


def test_the_lines_that_stay_english_are_counted_by_reason_class():
    plain = coverage.template_reason
    assert plain("missing_included_spell:407624") == plain("missing_included_spell:998")
    assert "Forever tables" in plain("missing_included_spell:998")
    assert plain("unsupported_code:$@auracaster") != plain("unsupported_code:$@spellaura")
    assert "optional parts" in plain("too_many_variants")
    for r in ("uncountable", "branches_indistinguishable", "unclosed_branch", "unsupported_code:$@other"):
        assert plain(r) and ":" not in plain(r) and "$" not in plain(r)


def test_every_ui_exclusion_has_one_reason_category(root: Path):
    """coverage.md counts the interface lines left English by the kind of reason: every reason in
    pipeline/ui_exclusions.txt falls in exactly one category (the first pattern that matches, in order), and
    one that falls in none fails here instead of vanishing from the count."""
    from wfj.dev import coverage

    counts, uncategorized = coverage.ui_exclusions_by_reason(root)
    assert uncategorized == []
    assert sum(counts.values()) > 2000
    assert counts["Not on Forever (a retail-era system, a gated addon, an empty client table)"] > 1000
    assert "A link label, or a line that is only a link" in counts
    # the committed report is the fresh render (test_the_committed_report_is_current): it carries the table
    rendered = (root / "docs/operations/coverage.md").read_text(encoding="utf-8")
    assert "### Interface lines left English, by reason" in rendered
    assert "| Not on Forever (a retail-era system, a gated addon, an empty client table) |" in rendered


def _quests(tmp_path: Path):
    """Quests 1-6: 1 and 5 fully Italian, 2 partly, 3 and 6 not at all, 4 with its title kept English on
    purpose; 1, 2, 3 and 4 have no level (`assente`), 5 and 6 one from pfQuest."""
    from wfj.io.jsonl_store import Store

    data = tmp_path / "data"
    (tmp_path / "pipeline").mkdir()
    for names in ("objective_names.txt", "area_names.txt"):
        (tmp_path / "pipeline" / names).write_text("", encoding="utf-8")
    (tmp_path / "pipeline" / "quest_levels.tsv").write_text(
        "id\tmin\tlvl\tfonte\n1\t\t\tassente\n2\t\t\tassente\n3\t\t\tassente\n4\t\t\tassente\n"
        "5\t1\t3\tpfquest@7786596\n6\t1\t3\tpfquest@7786596\n", encoding="utf-8")
    (tmp_path / "pipeline" / "keep_english.tsv").write_text(
        "tipo\tid\tcampo\thash\ten\nquest\t4\ttitle\th4title\tGoldtooth\n", encoding="utf-8")
    english, italian = [], []
    for q in range(1, 7):
        for f in ("title", "description"):
            english.append({"id": q, "field": f, "en": f"Quest {q} {f} text.", "hash": f"h{q}{f}",
                            "src": "wdb@1.60.1.70450"})
            if q in (1, 5) or (q == 2 and f == "title") or (q == 4 and f == "description"):
                italian.append({"id": q, "field": f, "it": f"Missione {q}.", "status": "trusted",
                                "english": {"hash": f"h{q}{f}", "src": "wdb@1.60.1.70450"}})
    Store(data, english=True).save("quest", english)
    Store(data).save("quest", italian)
    return data


def test_quests_without_a_level_and_partly_translated_quests_are_listed(tmp_path: Path):
    m = coverage.measure(_quests(tmp_path))
    assert m["quests"]["no_level"] == {"translated": [1, 4], "partial": [2], "untranslated": [3]}
    assert m["quests"]["partial"] == [2]
    text = coverage.render(m, "X")
    assert "### Quests without a level" in text
    assert "| Translated | 2 | 1, 4 |" in text
    assert "| Partly translated | 1 | 2 |" in text
    assert "| Not translated | 1 | 3 |" in text
    assert "### Partly translated quests" in text


def test_ids_are_listed_as_compact_ranges():
    assert coverage.ranges([7, 1, 2, 3, 10, 11, 5]) == "1-3, 5, 7, 10-11"
    assert coverage.ranges([]) == "none"
