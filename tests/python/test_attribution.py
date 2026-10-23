import re

from wfj.dev.gen_attribution import (
    FOREVER_VO,
    NO_TRANSLATORS,
    correctors_section,
    data_translators,
    english_sources,
    listed_translators,
    main,
    official_sources,
    render,
    with_correctors,
)

JAPANESE = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")


def test_every_translator_in_data_is_credited(root):
    """A hand-written line in data/, shipped or not, names its translator; the credits list every one. Run
    `python -m wfj.dev.gen_attribution` when this fails."""
    in_data = data_translators(root / "data")
    listed = set(listed_translators((root / "ATTRIBUTION.md").read_text(encoding="utf-8")))
    assert [t for t in in_data if t not in listed] == []


def test_committed_attribution_credits_the_upstream_code_and_no_japanese_translation(root):
    text = (root / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert text.startswith("# Attribution")
    upstream = text.split("## Translators")[0]
    for needle in ("WoW Forever Japanese", "Zyaga", "https://github.com/zyaga/wow-forever-japanese",
                   "GPL-2.0-or-later", "1578af4b", "no Japanese text ships"):
        assert needle in upstream, needle
    assert f"## Translators ({len(listed_translators(text))} tags" in text
    assert "## Lineage" in text and "## English source text" in text and "## This project" in text
    # the upstream corpus's translator list and its BSD notice went with the Japanese text
    assert not JAPANESE.search(text)
    assert "WoWJapanizer" not in text and "Redistribution and use in source" not in text


def test_render_sorted_casefold_and_an_empty_list_says_so():
    out = render(["zed", "Alpha", ""])
    assert out.index("- Alpha") < out.index("- zed")
    assert listed_translators(out) == ["Alpha", "zed"]
    empty = render([])
    assert "## Translators (0 tags" in empty and NO_TRANSLATORS in empty and listed_translators(empty) == []


def _store(tmp_path, lines):
    import json

    d = tmp_path / "data" / "quest"
    d.mkdir(parents=True)
    (d / "quest-0000.jsonl").write_text("".join(json.dumps(ln) + "\n" for ln in lines), encoding="utf-8")
    return tmp_path / "data"


def _line(id_, prov, conflicts=()):
    return {"id": id_, "field": "title", "it": "x", "status": "trusted", "provenance": prov, "conflicts": list(conflicts)}


def test_data_translators_read_every_hand_written_variant(tmp_path):
    human = {"class": "human", "translator": "Chiara", "source": "s", "imported": "d"}
    held_back = {"it": "y", "provenance": {"class": "human", "translator": "Luca", "source": "s", "imported": "d"}}
    machine = {"class": "machine", "model": "m", "source": "s", "imported": "d"}
    fix = {"class": "correction", "translator": "Player", "source": "s", "imported": "d", "report": 12}
    data = _store(tmp_path, [_line(1, human), _line(2, machine, [held_back]), _line(3, fix)])
    # the machine line has no translator; the player's credit belongs to the Correctors section
    assert data_translators(data) == ["Chiara", "Luca"]


def test_blizzards_official_text_names_no_translator(tmp_path):
    official = {"class": "official", "source": "wago-itit@12.1.5.70448", "imported": "2026-10-21"}
    human = {"class": "human", "translator": "Chiara", "source": "s", "imported": "d"}
    data = _store(tmp_path, [_line(1, official), _line(2, human, [{"it": "y", "provenance": official}])])
    assert data_translators(data) == ["Chiara"]


def test_a_regeneration_never_drops_a_credit(tmp_path):
    out = tmp_path / "ATTRIBUTION.md"
    out.write_text("# Attribution\n\n## Translators (1 tags, as recorded in data/)\n\n- Earlier\n\n## Lineage\n")
    human = {"class": "human", "translator": "Chiara", "source": "s", "imported": "d"}
    data = _store(tmp_path, [_line(1, human)])
    assert main(["--data", str(data), "--out", str(out)]) == 0
    listed = listed_translators(out.read_text(encoding="utf-8"))
    assert listed == ["Chiara", "Earlier"]


def test_regeneration_keeps_the_correctors_section(tmp_path):
    # `wfj report apply` writes the Correctors section from data/; regenerating the file keeps it, byte for
    # byte, before Lineage
    out = tmp_path / "ATTRIBUTION.md"
    data = _store(tmp_path, [])
    args = ["--data", str(data), "--out", str(out)]
    assert main(args) == 0
    first = out.read_text(encoding="utf-8")
    section = correctors_section({"Chiara": [12, 40]})
    out.write_text(with_correctors(first, {"Chiara": [12, 40]}), encoding="utf-8")
    assert main(args) == 0
    again = out.read_text(encoding="utf-8")
    assert section in again
    assert again.index(section) < again.index("## Lineage")
    assert again.replace(section, "") == first


def test_forever_vo_is_credited_exactly_while_its_lines_remain(root):
    """forever-vo's credit and license (ADR-055) stand in ATTRIBUTION.md exactly while some English line in
    data/english/ comes from it. When this fails, run `python -m wfj.dev.gen_attribution`: it adds or drops the
    credit to match the data."""
    text = (root / "ATTRIBUTION.md").read_text(encoding="utf-8")
    credited = "## forever-vo license" in text and "github.com/quinn-dougherty/forever-vo" in text
    assert credited == (FOREVER_VO in english_sources(root / "data"))


def test_without_forever_vo_lines_the_credit_leaves_no_trace():
    tags = ["A", "b"]
    without, with_ = render(tags), render(tags, {FOREVER_VO, "vmangos"})
    assert "forever-vo" not in without
    assert "\n\n## pfQuest license" in without and "\n\n## This project" in without
    assert "## forever-vo license" in with_ and "Copyright (c) 2026 Quinn Dougherty" in with_
    assert "\n\n## pfQuest license" in with_ and "\n\n## forever-vo license" in with_
    assert "\n\n## This project" in with_


def test_official_italian_is_credited_to_blizzard_with_its_build(root):
    # Blizzard's own Italian (`wfj import official`) has no translator: the credit names Blizzard and the
    # retail build the text was read from, and only while some official line is in data/
    out = render([], set(), {"wago-itit@12.1.5.70448"})
    section = out.split("## Blizzard's Italian text", 1)[1].split("\n## ", 1)[0]
    assert "Blizzard Entertainment (testi ufficiali itIT)" in section and "12.1.5.70448" in section
    assert "## Blizzard's Italian text" not in render([], set())
    committed = (root / "ATTRIBUTION.md").read_text(encoding="utf-8")
    for source in official_sources(root / "data"):
        assert source.split("@", 1)[1] in committed.split("## Blizzard's Italian text", 1)[-1], source
    assert ("## Blizzard's Italian text" in committed) == bool(official_sources(root / "data"))


def test_wowhead_npc_names_are_credited_apart_with_their_read_date():
    # ADR-103: Wowhead's Italian NPC names are dated reads, never listed as a retail build
    out = render([], set(), {"wago-itit@12.1.5.70448", "wowhead@2026-10-21"})
    section = out.split("## Blizzard's Italian text", 1)[1].split("\n## ", 1)[0]
    assert "Retail builds read: `12.1.5.70448`." in section
    assert "Wowhead" in section and "`2026-10-21`" in section
    assert "Wowhead" not in render([], set(), {"wago-itit@12.1.5.70448"})
