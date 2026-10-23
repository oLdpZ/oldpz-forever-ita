"""Voice casting: profiles from the client tables and the database, the casting pass, the roster of Gemini
voices with English director's notes, and the cast that gives each creature one voice."""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
import voice_fixture as vf

from wfj.cmd import voice_cast
from wfj.core import casting, voice
from wfj.io import client_tables, tables_stamp
from wfj.io.client_tables import Display
from wfj.io.gemini import GEMINI_VOICES

ROOT = Path(__file__).resolve().parents[2]
CLIENT, VM = "client@1.60.1.70450", "vmangos@13b49dc"
DISPLAYS = {
    1: Display("male", "tauren"), 2: Display("female", "tauren"), 3: Display("none", None),
    4: Display("male", "scourge"), 5: Display("none", None),
}
G = voice.gossip_key
RULED = {"source": "maintainer", "imported": "2026-10-01"}


def _creature(*displays: int, type_: int = 7, leader: bool = False) -> dict:
    return {"name": "x", "subname": "", "type": type_, "rank": 0, "leader": leader, "displays": list(displays)}


# ---- the client's display tables -------------------------------------------------------------------------


def test_display_tables_read_race_and_sex(tmp_path):
    (tmp_path / "CreatureDisplayInfo.csv").write_text(
        "ID,ModelID,ExtendedDisplayInfoID,Gender\n1,5,10,0\n2,6,0,2\n3,7,11,0\n")
    (tmp_path / "CreatureDisplayInfoExtra.csv").write_text("ID,DisplayRaceID,DisplaySexID\n10,6,0\n11,5,1\n")
    (tmp_path / "ChrRaces.csv").write_text("ID,ClientFileString\n5,Scourge\n6,Tauren\n")
    tables_stamp.write(tmp_path, client_tables.DISPLAY_TABLES, "db2@1.60.1.70450")
    displays, src = client_tables.read_displays(tmp_path)
    assert src == CLIENT
    assert displays == {1: Display("male", "tauren"), 2: Display("none", None), 3: Display("female", "scourge")}


def test_display_tables_refuse_a_missing_table_or_mixed_builds(tmp_path):
    with pytest.raises(FileNotFoundError, match="CreatureDisplayInfo.csv: run make tables-extract"):
        client_tables.read_displays(tmp_path)
    for t in client_tables.DISPLAY_TABLES:
        (tmp_path / f"{t}.csv").write_text("ID\n")
    tables_stamp.write(tmp_path, client_tables.DISPLAY_TABLES[:2], "db2@1")
    tables_stamp.write(tmp_path, client_tables.DISPLAY_TABLES[2:], "db2@2")
    with pytest.raises(ValueError, match="not stamped from one build"):
        client_tables.read_displays(tmp_path)


# ---- what the tables say ---------------------------------------------------------------------------------


def test_race_and_gender_come_from_the_client_first():
    assert casting.facts(_creature(1), DISPLAYS, CLIENT, VM, 1) == {
        "gender": ("male", CLIENT), "race": ("tauren", CLIENT)}


def test_a_creature_shown_as_both_genders_is_mixed():
    assert casting.facts(_creature(1, 2), DISPLAYS, CLIENT, VM, None)["gender"] == ("mixed", CLIENT)
    assert casting.facts(_creature(3, 1), DISPLAYS, CLIENT, VM, None)["gender"] == ("male", CLIENT)


def test_the_database_fills_what_the_client_lacks():
    f = casting.facts(_creature(999, type_=2), DISPLAYS, CLIENT, VM, 1)
    assert f == {"gender": ("female", VM), "race": ("dragonkin", VM), "archetype": ("dragon", VM)}
    assert casting.facts(_creature(1, leader=True), DISPLAYS, CLIENT, VM, None)["role"] == ("leader", VM)
    assert casting.facts(None, DISPLAYS, CLIENT, VM, None) == {}


def test_a_forsaken_model_is_undead():
    assert casting.facts(_creature(4), DISPLAYS, CLIENT, VM, None)["archetype"] == ("undead", CLIENT)


# ---- profiles: build and the casting pass ----------------------------------------------------------------


def _facts():
    return {10: {"race": ("scourge", CLIENT), "gender": ("male", CLIENT)}, 11: {}}


def test_build_writes_table_values_with_their_source():
    rows = casting.build([11, 10], _facts(), [], "2026-10-23")
    assert [r["creature"] for r in rows] == [10, 11]
    assert rows[0]["race"] == "scourge" and rows[0]["provenance"]["race"] == {"source": CLIENT, "imported": "2026-10-23"}
    assert rows[1] == {"creature": 11, "provenance": {}}


def test_the_pass_fills_gaps_and_never_replaces_a_table_value():
    rows = casting.build([10, 11], _facts(), [], "2026-10-23")
    drafts = [{"creature": 10, "age": "elder", "archetype": "undead", "race": "orc", "reason": "a croaking voice"},
              {"creature": 11, "age": "young", "archetype": "ghost", "race": "other", "gender": "female", "reason": "r"}]
    rows, problems = casting.merge_machine(rows, drafts, "m", "voce-1", "2026-10-23")
    assert rows[0]["race"] == "scourge" and rows[0]["age"] == "elder"
    assert problems == ["creature 10: race kept 'scourge' (draft says 'orc')"]
    assert rows[1]["provenance"]["age"] == {"source": "machine", "model": "m", "batch": "voce-1", "reason": "r",
                                            "imported": "2026-10-23"}
    assert casting.problems(rows) == []


def test_a_ruling_survives_a_rebuild_and_the_pass():
    ruled = {"creature": 10, "race": "scourge", "gender": "male", "age": "adult",
             "provenance": {"race": {"source": CLIENT, "imported": "2026-10-01"},
                            "gender": {"source": CLIENT, "imported": "2026-10-01"},
                            "age": RULED}}
    rows = casting.build([10], _facts(), [ruled], "2026-10-23")
    assert rows[0]["age"] == "adult" and rows[0]["provenance"]["race"]["imported"] == "2026-10-01"
    rows, problems = casting.merge_machine(rows, [{"creature": 10, "age": "elder", "reason": "r"}], "m", "b", "d")
    assert rows[0]["age"] == "adult" and problems


def test_drafts_with_bad_values_are_refused():
    rows = casting.build([11], _facts(), [], "2026-10-23")
    _, problems = casting.merge_machine(rows, [{"creature": 11, "age": "ancient", "reason": "r"},
                                               {"creature": 99, "age": "adult", "reason": "r"},
                                               {"creature": 11, "age": "adult"}], "m", "b", "2026-10-23")
    assert any("age 'ancient'" in p for p in problems)
    assert "draft for unknown creature 99" in problems and "creature 11: no reason" in problems


def test_validate_checks_profiles():
    bad = [{"creature": 1, "race": "Martian", "age": "adult", "provenance": {"race": {"source": "machine",
            "model": "m", "batch": "b", "reason": "r", "imported": "2026-10-23"}}},
           {"creature": 1, "provenance": {}}]
    problems = casting.problems(bad)
    assert any("lowercase race" in p for p in problems)
    assert any("1 age: no provenance" in p for p in problems)
    assert "voice profiles 1: duplicate" in problems


# ---- casting ---------------------------------------------------------------------------------------------


ROWS = [
    {"name": "ghost", "when": {"archetype": "ghost"}, "voices": ["g"]},
    {"name": "empty", "when": {"race": "tauren"}, "voices": []},
    {"name": "elder", "when": {"age": "elder"}, "voices": ["e1", "e2"]},
    {"name": "female", "when": {"gender": "female"}, "voices": ["f"]},
    {"name": "male", "when": {"gender": ["male", "none"]}, "voices": ["m"]},
]


def _p(c, **kw):
    return {"creature": c, **kw}


def test_first_matching_row_with_voices_wins():
    got = casting.cast([_p(1, archetype="ghost", age="elder", gender="male"), _p(2, race="tauren", gender="male"),
                        _p(3, gender="female", age="adult"), _p(4)], ROWS, "n", {})
    assert {c: v["row"] for c, v in got.items()} == {1: "ghost", 2: "male", 3: "female", 4: "narrator"}
    assert got[4]["voice"] == "n"


def test_a_creature_keeps_its_voice_and_neighbours_spread():
    elders = [_p(c, age="elder") for c in range(100, 140)]
    once = casting.cast(elders, ROWS, "n", {})
    again = casting.cast(list(reversed(elders)), ROWS, "n", {})
    assert once == again
    assert {v["voice"] for v in once.values()} == {"e1", "e2"}


def test_mixed_gender_is_cast_twice_and_an_override_wins():
    got = casting.cast([_p(5, gender="mixed", age="adult"), _p(6, gender="female")], ROWS, "n", {6: "m"})
    assert got[5] == {"voice": "m", "row": "male", "female": "f", "female_row": "female"}
    assert got[6] == {"voice": "m", "row": "override"}


def _voice(gemini="Algenib", notes="Raspy, slow, dry.", **kw):
    return {"voice": gemini, "notes": notes, "fits": "x", **kw}


def test_roster_problems():
    roster = {"m": _voice(), "Bad!": _voice(gemini="Robot", notes=""), "s": _voice(style=3, licence="ACML 1.0")}
    rows = [{"name": "a", "when": {"age": "old"}, "voices": ["m", "zz"]}, {"name": "a", "voices": "m"}]
    problems = casting.roster_problems(roster, rows, "m", "nope")
    for want in ("roster 'Bad!'", "voice 'Robot' is not a Gemini voice", "Bad!: notes must say", "narrator voice 'nope'",
                 "voice 'zz'", "age 'old'", "needs a unique name", "voices must be a list",
                 "roster s: unknown field(s) licence, style"):
        assert any(want in p for p in problems), want
    assert casting.roster_problems({"m": _voice()}, [{"name": "a", "voices": ["m"]}], "m", "m") == []


@pytest.mark.parametrize("notes", ["Voce roca.", "Slow, è stanco.", "A raspy voice, molto lento", "Il tono is dry.",
                                   "Dry, with a TEATRALE edge.", "Lento rhythm."])
def test_notes_are_english_only(notes):
    # Gemini reads Italian direction aloud: an accented letter or a common Italian word is refused
    problems = casting.roster_problems({"m": _voice(notes=notes)}, [], "m", "m")
    assert problems and all("notes must be English" in p for p in problems), problems


@pytest.mark.parametrize("notes", ["Lo-fi hiss, slow.", "Elderly, a la-di-da delivery.", "Delicate and older."])
def test_english_notes_with_italian_looking_pieces_pass(notes):
    # whole words only: "lo-fi" and "la-di-da" are words of their own, "Delicate" is not "del"
    assert casting.roster_problems({"m": _voice(notes=notes)}, [], "m", "m") == []


def _toml(path: Path, body: str = "") -> Path:
    path.write_text(
        'model = "gemini-3.1-flash-tts-preview"\nnarrator = "nar"\nbook_narrator = "nar"\n'
        '[roster.nar]\nvoice = "Charon"\nnotes = "An even, warm storyteller."\nfits = "narrator"\n'
        '[roster.um]\nvoice = "Algenib"\nnotes = "Raspy and dry."\nfits = "undead male"\n'
        '[roster.uf]\nvoice = "Gacrux"\nnotes = "Hollow and cold."\nfits = "undead female"\n'
        '[[cast]]\nname = "undead, female"\nwhen = { archetype = "undead", gender = "female" }\nvoices = ["uf"]\n'
        '[[cast]]\nname = "undead"\nwhen = { archetype = "undead" }\nvoices = ["um"]\n' + body,
        encoding="utf-8",
    )
    return path


def test_load_config_gives_the_roster_the_engine_reads(tmp_path):
    cfg = voice_cast.load_config(_toml(tmp_path / "voice.toml"))
    assert cfg["roster"]["um"] == {"gemini_voice": "Algenib", "model": "gemini-3.1-flash-tts-preview",
                                   "notes": "Raspy and dry.", "fits": "undead male"}
    assert [r["name"] for r in cfg["cast"]] == ["undead, female", "undead"]
    # the roster is what voice.in_step reads
    job = voice.Job("1-description", "1-description", "um", "m")
    assert voice.in_step([job], {"1-description": "Ciao."}, cfg["roster"], {}) == {
        "missing": ["1-description"], "stale": []}
    bad = _toml(tmp_path / "bad.toml", '[roster.it]\nvoice = "Kore"\nnotes = "Voce calma."\nfits = "x"\n')
    with pytest.raises(ValueError, match="notes must be English"):
        voice_cast.load_config(bad)


def test_the_committed_voice_toml_is_a_valid_gemini_roster():
    cfg = voice_cast.load_config(ROOT / "pipeline" / "voice.toml")
    assert cfg["narrator"] in cfg["roster"] and cfg["book_narrator"] in cfg["roster"]
    assert cfg["model"] == "gemini-3.1-flash-tts-preview"
    assert all(v["gemini_voice"] in GEMINI_VOICES for v in cfg["roster"].values())
    # the raspy undead male the owner liked for Undertaker Mordo (1568)
    mordo = {"creature": 1568, "race": "scourge", "gender": "male", "age": "adult", "archetype": "undead"}
    got = casting.cast([mordo], cfg["cast"], cfg["narrator"], {})[1568]
    assert cfg["roster"][got["voice"]]["gemini_voice"] == "Algenib"


# ---- wfj voice profiles build|export|import and wfj voice cast -------------------------------------------


@pytest.fixture
def world(tmp_path, monkeypatch):
    data = vf.make_data(tmp_path)
    vf.write_rows(data / "voice" / "speakers.jsonl", [
        {"key": "456-description", "speaker": 2079, "others": [1992], "provenance": vf.SRC},
        {"key": "456-completion", "speaker": 2079, "provenance": vf.SRC},
        {"key": "457-completion", "speaker": 5555, "provenance": vf.SRC},
        {"key": "459-description", "speaker": "narrator", "provenance": vf.SRC},
        {"key": G(voice.gossip_id(vf.HELLO)), "speaker": 3597, "provenance": vf.SRC},
        {"key": G(voice.gossip_id(vf.GREETING)), "speaker": 9000, "provenance": vf.SRC},
    ])
    vf.write_rows(data / "voice" / "profiles.jsonl", [{"creature": 2079, "age": "adult", "provenance": {"age": RULED}}])
    scope = tmp_path / voice.SCOPES["tirisfal"]
    scope.parent.mkdir(parents=True)
    scope.write_text("456\n457\n459\n")
    from wfj.io.jsonl_store import Store

    Store(data, english=True).save("unit", [{"id": 5555, "field": "name", "en": "Collector Seen",
                                             "src": vf.COLLECTOR}])
    monkeypatch.setattr(voice_cast, "data_root", lambda: data)
    return SimpleNamespace(data=data, db=vf.make_speaker_db(tmp_path / "mangos.sqlite"),
                           client=vf.make_client(tmp_path / "client"), tmp=tmp_path)


def _profiles(world):
    return {r["creature"]: r for r in voice_cast._rows(world.data / "voice" / "profiles.jsonl")}


def _build(world):
    return voice_cast.run_profiles(["build", "--vmangos", str(world.db), "--commit", "sha",
                                    "--client", str(world.client)])


def test_speaking_names_every_creature_main_or_other(world):
    assert voice_cast.speaking(world.data) == {2079, 1992, 5555, 3597, 9000}
    assert voice_cast.speaking(world.tmp) == set()  # no speakers table yet


def test_build_takes_the_tables_and_keeps_a_ruling(world):
    rows, stats = voice_cast.build(world.data, world.db, "sha", world.client, "2026-10-23")
    by = {r["creature"]: r for r in rows}
    vm = "vmangos@sha"
    assert [r["creature"] for r in rows] == [1992, 2079, 3597, 5555, 9000]
    assert (by[2079]["race"], by[2079]["gender"], by[2079]["age"], by[2079]["archetype"]) == (
        "scourge", "male", "adult", "undead")
    assert by[2079]["provenance"]["race"] == {"source": CLIENT, "imported": "2026-10-23"}
    assert by[2079]["provenance"]["age"] == RULED
    assert by[1992]["gender"] == "female" and by[1992]["provenance"]["gender"]["source"] == vm
    assert by[5555] == {"creature": 5555, "provenance": {}}  # the database lacks it
    assert {f: by[9000][f] for f in ("race", "gender", "archetype", "role")} == {
        "race": "beast", "gender": "none", "archetype": "beast-kin", "role": "leader"}
    assert stats == {
        "speakers": 5, "not in the database": 1, "race from the tables": 3, "gender from the tables": 4,
        "age from the tables": 0, "archetype from the tables": 3, "role from the tables": 1,
        "still need judgement": 4,
    }


def test_the_build_command_writes_profiles_and_prints_the_numbers(world, capsys):
    assert _build(world) == 0
    assert sorted(_profiles(world)) == [1992, 2079, 3597, 5555, 9000]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "voice profiles: 5 speakers → data/voice/profiles.jsonl"
    assert "voice profiles: not in the database: 1" in out and "voice profiles: still need judgement: 4" in out


def test_lines_by_speaker_are_italian_longest_first_and_shipped_only(world):
    got = voice_cast._lines_by_speaker(world.data)
    assert got[2079] == ["Salve, {name}. Difendi la valle.", "Ben fatto."]
    assert got[1992] == ["Salve, {name}. Difendi la valle."]
    assert got[3597] == ["Salve, viandante."] and got[5555] == ["Grazie."]


def test_export_writes_parts_of_the_speakers_that_need_judgement(world):
    _build(world)
    out = world.tmp / "pass"
    assert voice_cast.export(world.data, world.db, out, 2) == 4
    assert sorted(p.name for p in out.iterdir()) == ["part-01.jsonl", "part-02.jsonl"]
    items = [json.loads(ln) for p in sorted(out.iterdir()) for ln in p.read_text(encoding="utf-8").splitlines()]
    by = {i["creature"]: i for i in items}
    assert list(by) == [1992, 3597, 5555, 9000]  # 2079 owes nothing: the tables and a ruling say it all
    assert by[3597] == {"creature": 3597, "name": "Novice Elreth", "title": "", "type": "humanoid",
                        "known": {"race": "scourge", "gender": "male", "archetype": "undead"},
                        "lines": ["Salve, viandante."]}
    assert (by[5555]["name"], by[5555]["type"], by[5555]["lines"]) == ("Collector Seen", "unknown", ["Grazie."])
    assert by[9000]["known"] == {"race": "beast", "gender": "none", "archetype": "beast-kin", "role": "leader"}


def test_export_sends_at_most_three_lines(world):
    _build(world)
    many = [{"key": f"{q}-description", "speaker": 3597, "provenance": vf.SRC} for q in (456, 457, 459)]
    vf.write_rows(world.data / "voice" / "speakers.jsonl", [
        *many, {"key": "456-completion", "speaker": 3597, "provenance": vf.SRC}])
    voice_cast.export(world.data, world.db, world.tmp / "pass", 800)
    item = json.loads((world.tmp / "pass" / "part-01.jsonl").read_text(encoding="utf-8").splitlines()[1])
    assert item["creature"] == 3597 and len(item["lines"]) == 3


def _drafts(path, *rows):
    vf.write_rows(path, list(rows))
    return str(path)


def test_import_fills_ages_and_fails_while_one_is_owed(world, capsys):
    _build(world)
    capsys.readouterr()
    first = _drafts(world.tmp / "d1.jsonl",
                    {"creature": 1992, "age": "adult", "race": "scourge", "archetype": "undead", "reason": "a guard"},
                    {"creature": 3597, "age": "young", "reason": "a novice"},
                    {"creature": 5555, "age": "adult", "reason": "plain speech"},
                    {"creature": 42, "age": "adult", "reason": "r"})
    argv = ["import", "--drafts", first, "--model", "claude-opus-5-5", "--batch", "voce-1"]
    assert voice_cast.run_profiles(argv) == 1
    out = capsys.readouterr().out.splitlines()
    assert out == ["voice profiles: draft for unknown creature 42",
                   "voice profiles: 1 problem(s); 1 speaker(s) still owed an age"]
    p = _profiles(world)
    today = datetime.date.today().isoformat()
    assert p[1992]["age"] == "adult" and p[1992]["provenance"]["age"] == {
        "source": "machine", "model": "claude-opus-5-5", "batch": "voce-1", "reason": "a guard", "imported": today}
    second = _drafts(world.tmp / "d2.jsonl", {"creature": 9000, "age": "elder", "reason": "an old bat"})
    assert voice_cast.run_profiles(["import", "--drafts", second, "--model", "m1", "--batch", "voce-2"]) == 0
    assert "0 speaker(s) still owed an age" in capsys.readouterr().out


def test_missing_client_tables_fail_with_how_to_make_them(world, capsys):
    (world.client / "ChrRaces.csv").unlink()
    assert _build(world) == 1
    err = capsys.readouterr().err
    assert err.startswith("voice profiles: ") and "ChrRaces.csv: run make tables-extract" in err


def test_a_database_without_creature_columns_fails(world, tmp_path, capsys):
    bad = vf.make_speaker_db(tmp_path / "bad.sqlite")
    db = sqlite3.connect(bad)
    db.execute("DROP TABLE creature_template")
    db.commit()
    db.close()
    argv = ["build", "--vmangos", str(bad), "--commit", "sha", "--client", str(world.client)]
    assert voice_cast.run_profiles(argv) == 1
    assert "no table 'creature_template'" in capsys.readouterr().err


def _cast(world, *profiles):
    vf.write_rows(world.data / "voice" / "profiles.jsonl", list(profiles))
    cfg = _toml(world.tmp / "voice.toml",
                '[roster.hm]\nvoice = "Orus"\nnotes = "Firm."\nfits = "male"\n'
                '[roster.hf]\nvoice = "Kore"\nnotes = "Clear."\nfits = "female"\n'
                '[[cast]]\nname = "female"\nwhen = { gender = "female" }\nvoices = ["hf"]\n'
                '[[cast]]\nname = "male"\nwhen = { gender = ["male", "none"] }\nvoices = ["hm"]\n')
    assert voice_cast.run_cast(["--scope", "tirisfal", "--config", str(cfg)]) == 0
    return {r["creature"]: r for r in voice_cast._rows(world.data / "voice" / "voices.jsonl")}


def test_cast_writes_one_voice_per_creature_and_is_stable(world, capsys):
    profiles = [{"creature": 2079, "gender": "male", "archetype": "undead", "provenance": {}},
                {"creature": 1992, "gender": "mixed", "provenance": {}},
                {"creature": 3597, "gender": "female", "archetype": "undead", "provenance": {}},
                {"creature": 4242, "gender": "male", "provenance": {}}]  # speaks no scoped line
    first = _cast(world, *profiles)
    assert sorted(first) == [1992, 2079, 3597]
    assert {c: (r["voice"], r["row"]) for c, r in first.items()} == {
        2079: ("um", "undead"), 1992: ("hm", "male"), 3597: ("uf", "undead, female")}
    # a creature the game shows as both genders gets a female voice too
    assert (first[1992]["female"], first[1992]["female_row"]) == ("hf", "female")
    assert first[2079]["provenance"]["source"] == "cast@voice.toml"
    assert "voice cast: 3 creatures → data/voice/voices.jsonl" in capsys.readouterr().out
    path = world.data / "voice" / "voices.jsonl"
    old = path.read_text(encoding="utf-8").replace(f'"imported": "{datetime.date.today().isoformat()}"',
                                                   '"imported": "2026-01-01"')
    path.write_text(old, encoding="utf-8")
    _cast(world, *reversed(profiles))
    assert path.read_text(encoding="utf-8") == old  # same creature, same voice, old dates kept
