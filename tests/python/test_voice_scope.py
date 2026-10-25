"""`wfj voice scope tirisfal`: the pilot's quests and book pages, from the database's zone and spawns and the
players' captures; and the committed list it wrote."""

from __future__ import annotations

from pathlib import Path

import voice_fixture as vf
from wfj.cmd import voice as cmd
from wfj.cmd import voice_scope
from wfj.core import voice

ROOT = Path(__file__).resolve().parents[2]


def test_the_zone_quests_forever_quests_given_inside_and_signs_standing_inside(tmp_path):
    data = vf.make_data(tmp_path)
    db = vf.make_speaker_db(tmp_path / "mangos.sqlite")
    cap = vf.make_captures(tmp_path / "fvo",
                           {"event": "accept", "questID": 459, "npc": 1992},  # given in Tirisfal
                           {"event": "accept", "questID": 461, "npc": 9000},  # the same spot, on another map
                           {"event": "complete", "questID": 462, "npc": 1992})  # nobody saw who gives it
    quests, books, report = voice_scope.build(data, db, "tirisfal", cap)
    assert quests == (456, 457, 458, 459, 463)  # 456: its highest patch is Tirisfal's; 463 is Deathknell's
    assert books == (vf.SIGNED, vf.UNSIGNED)  # sign 800's two pages; 801 stands far south and under the city
    assert report["forever"] == ["459: given by 1992"]
    assert report["outside"] == ["461: given by 9000"]
    assert report["unplaced"] == ["462: no giver captured"]


def test_the_zone_is_its_map_rectangle_above_the_city_under_it():
    (z,) = voice_scope.ZONES["tirisfal"]
    assert z.holds(0, *vf.IN)
    assert not z.holds(1, *vf.IN) and not z.holds(0, *vf.OUT) and not z.holds(0, *vf.UNDER)


def test_a_city_inside_a_zone_rectangle_is_cut_out():
    # Orgrimmar stands inside Durotar's box, Thunder Bluff inside Mulgore's; Ratchet is past Durotar's river
    _, durotar, mulgore = voice_scope.ZONES["orda"]
    assert durotar.holds(1, 300.0, -4700.0, 10.0)  # Razor Hill
    assert not durotar.holds(1, 1600.0, -4400.0, 30.0)  # Orgrimmar
    assert not durotar.holds(1, -956.0, -3754.0, 5.0)  # Ratchet
    assert mulgore.holds(1, -2300.0, -400.0, -9.0)  # Bloodhoof Village
    assert not mulgore.holds(1, -1200.0, 0.0, 100.0)  # Thunder Bluff
    assert not mulgore.holds(1, -2350.0, -1925.0, 90.0)  # Camp Taurajo, in the Barrens


def test_the_alliance_cities_and_neighbours_are_left_out():
    elwynn, dun_morogh, teldrassil = voice_scope.ZONES["alleanza"]
    assert elwynn.holds(0, -9466.0, 74.0, 57.0)  # Goldshire
    assert elwynn.holds(0, -8903.0, -163.0, 82.0)  # Northshire Abbey
    assert not elwynn.holds(0, -8858.0, 625.0, 96.0)  # Stormwind
    assert not elwynn.holds(0, -10509.0, 1045.0, 61.0)  # Sentinel Hill, in Westfall
    assert dun_morogh.holds(0, -5606.0, -544.0, 392.0)  # Kharanos
    assert not dun_morogh.holds(0, -4900.0, -1000.0, 506.0)  # Ironforge
    assert not dun_morogh.holds(0, -5402.0, -2895.0, 342.0)  # Thelsamar, in Loch Modan
    assert teldrassil.holds(1, 9837.0, 966.0, 1308.0)  # Dolanaar
    assert not teldrassil.holds(1, 10173.0, 2570.0, 1367.0)  # Darnassus
    assert not teldrassil.holds(1, 7848.0, -2216.0, 471.0)  # Moonglade
    assert voice_scope.ZONES["iniziali"] == voice_scope.ZONES["orda"] + voice_scope.ZONES["alleanza"]


def test_the_whole_game_lists_every_quest_and_page(tmp_path):
    data = vf.make_data(tmp_path)
    db = vf.make_speaker_db(tmp_path / "mangos.sqlite")
    quests, books, report = voice_scope.build(data, db, "tutto", None)
    _, zbooks, _ = voice_scope.build(data, db, "tirisfal", None)
    assert quests == (457, 458, 459, 461, 462)  # the English store's quests, Forever's too, placed or not
    assert set(zbooks) <= set(books)  # a sign standing far away is listed too
    assert report == {"forever": [], "outside": [], "unplaced": [], "pages": []}


def test_a_giver_the_database_never_spawns_is_reported(tmp_path):
    data = vf.make_data(tmp_path)
    db = vf.make_speaker_db(tmp_path / "mangos.sqlite")
    cap = vf.make_captures(tmp_path / "fvo", {"event": "accept", "questID": 459, "npc": 256930},
                           {"event": "accept", "questID": 461, "isObject": True})
    _, _, report = voice_scope.build(data, db, "tirisfal", cap)
    assert report["unplaced"] == ["459: given by 256930, whom the database never spawns", "461: given by an object",
                                  "462: no giver captured"]


def test_without_captures_forever_quests_are_reported_not_guessed(tmp_path):
    data = vf.make_data(tmp_path)
    db = vf.make_speaker_db(tmp_path / "mangos.sqlite")
    quests, _, report = voice_scope.build(data, db, "tirisfal", None)
    assert quests == (456, 457, 458, 463)
    assert report["unplaced"] == ["459: no giver captured", "461: no giver captured", "462: no giver captured"]


def test_the_list_is_deterministic_and_reads_back(tmp_path, monkeypatch):
    data = vf.make_data(tmp_path)
    monkeypatch.setattr(voice_scope, "data_root", lambda: data)
    db = vf.make_speaker_db(tmp_path / "mangos.sqlite")
    out = tmp_path / "scope.txt"
    argv = ["tirisfal", "--vmangos", str(db), "--out", str(out)]
    assert voice_scope.run(argv) == 0
    first = out.read_bytes()
    assert voice_scope.run(argv) == 0
    assert out.read_bytes() == first
    assert voice.read_scope_file(out) == ((456, 457, 458, 463), (vf.SIGNED, vf.UNSIGNED))
    assert first.decode().startswith("# ")  # says what wrote it


def test_the_dispatcher_runs_scope(monkeypatch):
    seen = []
    monkeypatch.setattr(voice_scope, "run", lambda argv: seen.append(list(argv)) or 0)
    assert cmd.run(["scope", "tirisfal", "--vmangos", "x"]) == 0
    assert seen == [["tirisfal", "--vmangos", "x"]]


def test_the_committed_pilot_list():
    path = ROOT / voice.SCOPES["tirisfal"]
    quests, books = voice.read_scope_file(path)
    body = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    assert (len(quests), len(books), len(body)) == (QUESTS, BOOKS, QUESTS + BOOKS)
    assert 363 in quests  # Rude Awakening, Deathknell's first quest


# what `wfj voice scope tirisfal` wrote from VMaNGOS 4641790 and forever-vo 025070f: 48 quests of Tirisfal and
# Deathknell, 11 Forever quests given there, and the 17 pages of 3 signs and books standing there
QUESTS, BOOKS = 59, 17
