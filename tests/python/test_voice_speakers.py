"""Who speaks each voiced line: the quest giver and taker, the creature whose menu holds a gossip line, the
signer of a book page; `wfj voice speakers` over a scope, and the `wfj validate` rule over data/voice."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import voice_fixture as vf

from wfj.cmd import validate
from wfj.cmd import voice as cmd
from wfj.core import voice

TODAY = "2026-10-23"
G = voice.gossip_key


# ---- pure rules ------------------------------------------------------------------------------------------


def test_the_giver_offers_the_taker_answers_and_an_object_is_the_narrator():
    keys = ["1-description", "1-progress", "1-completion", "2-description", "3-completion"]
    got, problems = voice.quest_speakers(keys, {1: [10]}, {2}, {1: [20]})
    assert got == {"1-description": 10, "1-progress": 20, "1-completion": 20,
                   "2-description": voice.NARRATOR, "3-completion": voice.NARRATOR}
    # an object start is expected; a quest no creature takes back is reported
    assert problems == ["3-completion: no creature in the database, narrator"]


def test_several_creatures_the_lowest_speaks_and_the_rest_are_others():
    others: dict[str, list[int]] = {}
    got, problems = voice.quest_speakers(["1-description"], {1: [30, 10, 20]}, set(), {}, others)
    assert got == {"1-description": 10} and others == {"1-description": [20, 30]}
    assert problems == ["1-description: creatures [30, 10, 20], took 10"]


def test_a_capture_names_the_most_seen_speaker():
    assert voice.captured_speaker([]) is None
    assert voice.captured_speaker([5, 7, 7]) == 7
    assert voice.captured_speaker([None, None, 5]) == voice.NARRATOR
    assert voice.captured_speaker([None, 9, 5]) == 5  # a tie: a creature, then the lowest id


def test_gossip_comes_from_the_creature_menu_and_the_collector_wins():
    a, b, c = (voice.gossip_id(t) for t in ("Hi.", "Bye.", "Gone."))
    lines = [(10, "Hi."), (11, "Hi."), (12, "Bye."), (13, "Gone.")]
    others: dict[str, list[int]] = {}
    got, report = voice.gossip_speakers(lines, {a: [11], b: [99]}, {a, b}, others)
    assert got == {G(a): 11, G(b): 99}  # what the client served beats the database
    assert others == {G(a): [10], G(b): [12]}
    assert report["missing"] == [f"g-{c} (creature 13)"]


def test_a_book_page_is_read_by_its_single_signer_among_the_speakers():
    assert voice.book_signature("Dear friend,$B$B-Baelog") == "Baelog"
    assert voice.book_signature("Your friend,\nThrall") == "Thrall"
    assert voice.book_signature("A page.\nThe End") is None
    assert voice.book_signature("Baelog") is None  # a page that is only a name is a label
    pages = {"b-1": "Hi.\n-Baelog", "b-2": "Hi.\n-Twin Name", "b-3": "No signature.", "b-4": "Hi.\n- Nobody"}
    names = {"Baelog": [5, 6], "Twin Name": [7, 8]}
    got = voice.book_speakers(pages, names, cast={6, 7, 8})
    # Baelog: one of the two creatures so named speaks; the twins both speak, so nobody knows which signed
    assert got == {"b-1": 6, "b-2": voice.BOOK_NARRATOR, "b-3": voice.BOOK_NARRATOR, "b-4": voice.BOOK_NARRATOR}


def _row(key, speaker, **kw):
    return {"key": key, "speaker": speaker, **kw, "provenance": {"source": "vmangos@abc", "imported": TODAY}}


def test_speaker_problems():
    good = [_row("1-description", 10), _row("2-progress", voice.NARRATOR), _row(f"b-{'a' * 16}", voice.BOOK_NARRATOR),
            _row(G("f" * 16), 11, others=[12])]
    assert voice.speaker_problems(good, []) == []  # nothing cast yet: no voice is owed
    bad = [_row("1-description", 10), _row("1-description", 10), _row("x", 10), _row("3-progress", "someone"),
           _row("4-progress", voice.BOOK_NARRATOR), _row("5-progress", 10, others=[10]),
           {"key": "6-progress", "speaker": 10}]
    problems = voice.speaker_problems(bad, [])
    assert "voice speakers 1-description: duplicate" in problems
    assert "voice speakers: bad key 'x'" in problems
    assert any(p.startswith("voice speakers 3-progress: speaker must be") for p in problems)
    assert "voice speakers 4-progress: only a book page has the book narrator" in problems
    assert any(p.startswith("voice speakers 5-progress: others") for p in problems)
    assert "voice speakers 6-progress: provenance must be an object" in problems


def test_once_cast_every_speaking_creature_needs_a_voice():
    voices = [{"creature": 10, "voice": "undeadmale", "row": "undead",
               "provenance": {"source": "cast@voice.toml", "imported": TODAY}}]
    problems = voice.speaker_problems([_row("1-description", 10, others=[11])], voices)
    assert problems == ["voice speakers 1-description: creature 11 has no voice row"]
    bad = [{"creature": 10, "voice": "Not An Id", "row": "", "provenance": {}}]
    problems = voice.speaker_problems([], bad)
    assert "voice voices 10: voice must be a roster voice id" in problems
    assert "voice voices 10: row must name the cast row that chose the voice" in problems


# ---- wfj voice speakers ----------------------------------------------------------------------------------


@pytest.fixture
def world(tmp_path, monkeypatch):
    data = vf.make_data(tmp_path)
    db = vf.make_speaker_db(tmp_path / "mangos.sqlite")
    monkeypatch.setattr(cmd, "data_root", lambda: data)
    return SimpleNamespace(data=data, db=db, tmp=tmp_path)


def _by_key(rows):
    return {r["key"]: (r["speaker"], r["provenance"]["source"]) for r in rows}


SCOPE = ((456, 457, 458, 459), (vf.SIGNED, vf.UNSIGNED))


def test_a_scope_reads_its_quests_their_npcs_talk_and_its_books(world):
    cap = vf.make_captures(world.tmp / "fvo", {"event": "accept", "questID": 459, "npc": 1992})
    rows, report = cmd.build_tables(world.data, world.db, "sha", SCOPE, TODAY, (cap, "abc"))
    assert _by_key(rows) == {
        "456-completion": (2079, "vmangos@sha"),
        "456-description": (2079, "vmangos@sha"),
        "457-completion": (1992, "vmangos@sha"),
        "457-description": (2079, "vmangos@sha"),
        "459-description": (1992, "forever-vo@abc"),  # the database lacks the quest; a capture names its giver
        f"b-{vf.SIGNED}": (6906, "book-signature@sha"),
        f"b-{vf.UNSIGNED}": (voice.BOOK_NARRATOR, "book@narrator"),
        G(voice.gossip_id(vf.GREETING)): (1992, "vmangos@sha"),
        G(voice.gossip_id(vf.HELLO)): (3597, vf.COLLECTOR),  # in 2079's menu, but the client served it from 3597
        G(voice.gossip_id(vf.CAPTURED)): (1992, vf.COLLECTOR),  # only the collector heard it
    }
    assert [r["key"] for r in rows] == sorted(r["key"] for r in rows)
    assert all(r["provenance"]["imported"] == TODAY for r in rows)
    assert report["quest"] == []
    assert report["missing"] == ["458-description"]  # English in scope, no Italian shipped
    # the unscoped creature's gossip and the far book page are not read
    assert G(voice.gossip_id(vf.STRANGER)) not in _by_key(rows) and f"b-{vf.FAR}" not in _by_key(rows)


def test_without_captures_a_quest_the_database_lacks_is_the_narrator_and_reported(world):
    rows, report = cmd.build_tables(world.data, world.db, "sha", SCOPE, TODAY)
    assert _by_key(rows)["459-description"] == (voice.NARRATOR, "vmangos@sha")
    assert report["quest"] == ["459-description: no creature in the database, narrator"]


def test_speakers_writes_the_table_and_keeps_dates_on_a_rerun(world, capsys):
    scope = world.tmp / voice.SCOPES["tirisfal"]
    scope.parent.mkdir(parents=True)
    scope.write_text("456\n457\n458\n459\nb " + vf.SIGNED + "\nb " + vf.UNSIGNED + "\n")
    argv = ["speakers", "--vmangos", str(world.db), "--commit", "sha", "--scope", "tirisfal"]
    assert cmd.run(argv) == 0
    path = world.data / "voice" / "speakers.jsonl"
    first = path.read_text(encoding="utf-8")
    assert '"key": "456-description", "speaker": 2079' in first
    out = capsys.readouterr().out
    assert "voice speakers: 10 lines, 4 creatures" in out and "missing: 458-description" in out
    old = first.replace(f'"imported": "{cmd.today()}"', '"imported": "2026-01-01"')
    path.write_text(old, encoding="utf-8")
    assert cmd.run(argv) == 0
    assert path.read_text(encoding="utf-8") == old  # same rows, old dates: a re-run writes the same bytes


def test_the_dispatcher_hands_verbs_on_and_refuses_the_dropped_ones(monkeypatch):
    from wfj.cmd import voice_cast

    seen = []
    monkeypatch.setattr(voice_cast, "run_profiles", lambda argv: seen.append(("profiles", list(argv))) or 0)
    monkeypatch.setattr(voice_cast, "run_cast", lambda argv: seen.append(("cast", list(argv))) or 0)
    assert cmd.run(["profiles", "export", "--out", "x"]) == 0
    assert cmd.run(["cast", "--scope", "tirisfal"]) == 0
    assert seen == [("profiles", ["export", "--out", "x"]), ("cast", ["--scope", "tirisfal"])]
    for dropped in ("audition", "levels", "store-sync", "release"):
        with pytest.raises(SystemExit):
            cmd.run([dropped])


def test_the_cli_knows_voice():
    from wfj import cli

    assert cli.VERBS["voice"][1] is cmd.run


# ---- wfj validate over data/voice ------------------------------------------------------------------------


def test_validate_reads_data_voice(world):
    vf.write_rows(world.data / "voice" / "speakers.jsonl", [_row("1-description", 10)])
    problems = validate.rule_voice(world.data, Path("absent.toml"))
    assert problems == ["voice speakers 1-description: creature 10 has no voice row"]
