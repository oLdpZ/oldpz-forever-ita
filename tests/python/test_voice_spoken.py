"""wfj voice spoken export|import: the lines the voice says from a spoken version (they name the player's class
or race, or the filter blocked every take), out to a file to write and back into data/voice/spoken.jsonl."""

from __future__ import annotations

import json

import pytest
import test_voice_make as vm
import voice_fixture as vf

from wfj.cmd import voice_make, voice_spoken
from wfj.core import voice

world = vm.world  # the same small world as the generate tests
CLASS, PROFILE, FakeEngine, write_quests = vm.CLASS, vm.PROFILE, vm.FakeEngine, vm.write_quests


def _read(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _export(world, store=True):
    out = world.tmp / "spoken-out.jsonl"
    argv = ["export", "--scope", "tirisfal", "--out", str(out), "--config", str(world.config)]
    assert voice_spoken.run([*argv, *(["--store", str(world.store)] if store else [])], root=world.data) == 0
    return _read(out)


def test_export_lists_class_lines_and_blocked_takes_with_text_and_reason(world):
    vm._gen(world, FakeEngine(block=["Ben fatto"]))
    rows = _export(world)
    assert [(r["key"], r["sex"]) for r in rows] == [("456-completion", "m"), ("470-description", "any")]
    blocked, cls = rows
    assert (cls["it"], cls["it_hash"], cls["spoken"]) == (CLASS, voice.it_hash(CLASS), "")
    assert "class or race" in cls["reason"]
    assert blocked["it"] == "Ben fatto." and blocked["reason"] == "blocked: stopped (SAFETY)"


def test_export_without_a_store_lists_the_class_lines(world):
    assert [r["key"] for r in _export(world, store=False)] == ["470-description"]


def test_export_skips_a_line_with_a_fresh_spoken_version_and_offers_a_stale_one_again(world):
    vf.write_rows(world.data / "voice" / "spoken.jsonl", [
        {"key": "470-description", "sex": "any", "it_hash": voice.it_hash("Vecchio."), "spoken": "Uno come te.",
         "reason": "class", "provenance": PROFILE},
    ])
    (row,) = _export(world)
    assert row["spoken"] == "Uno come te." and row["stale"] is True
    vf.write_rows(world.data / "voice" / "spoken.jsonl", [{**row, "it_hash": voice.it_hash(CLASS),
                                                            "provenance": PROFILE}])
    assert _export(world) == []


def test_import_writes_the_spoken_versions_with_provenance(world, capsys):
    rows = _export(world)
    rows[0]["spoken"] = "Uno come te serve qui."
    src = world.tmp / "done.jsonl"
    vf.write_rows(src, [*rows, {**rows[0], "key": "456-completion", "it_hash": voice.it_hash("Ben fatto."),
                                "sex": "m", "spoken": "  "}])  # an empty spoken version is left out
    assert voice_spoken.run(["import", str(src)], root=world.data) == 0
    got = _read(world.data / "voice" / "spoken.jsonl")
    assert len(got) == 1
    assert {k: got[0][k] for k in ("key", "sex", "it_hash", "spoken")} == {
        "key": "470-description", "sex": "any", "it_hash": voice.it_hash(CLASS), "spoken": "Uno come te serve qui."}
    assert got[0]["reason"] == rows[0]["reason"]
    assert got[0]["provenance"]["source"] == "maintainer"
    assert set(got[0]) == {"key", "sex", "it_hash", "spoken", "reason", "provenance"}
    assert "1 spoken version" in capsys.readouterr().out
    # a second import of the same line replaces it
    vf.write_rows(src, [{**rows[0], "spoken": "Chi come te serve qui."}])
    assert voice_spoken.run(["import", str(src)], root=world.data) == 0
    assert [r["spoken"] for r in _read(world.data / "voice" / "spoken.jsonl")] == ["Chi come te serve qui."]
    # and generate reads it
    engine = FakeEngine()
    vm._gen(world, engine)
    assert "Chi come te serve qui." in engine.said()


@pytest.mark.parametrize(("change", "why"), [
    ({"it_hash": "0" * 16}, "the Italian changed"),
    ({"spoken": "Un {class} come te."}, "markup"),
    ({"spoken": "[sospira] Uno come te."}, "sospira"),
    ({"sex": "x"}, "sex"),
    ({"key": "999-description"}, "not a line"),
    ({"reason": ""}, "reason"),
])
def test_import_refuses_a_bad_row_and_writes_nothing(world, capsys, change, why):
    (row,) = _export(world)
    src = world.tmp / "done.jsonl"
    vf.write_rows(src, [{**row, "spoken": "Uno come te.", **change}])
    assert voice_spoken.run(["import", str(src)], root=world.data) == 1
    assert why in capsys.readouterr().err
    assert not (world.data / "voice" / "spoken.jsonl").exists()


def test_a_spoken_version_must_read_for_every_sex_it_is_for(world, capsys):
    write_quests(world.data, **{"470_description": "Un {class} come te, {name}."})
    (row,) = _export(world)
    src = world.tmp / "done.jsonl"
    vf.write_rows(src, [{**row, "spoken": "Uno come te, $X."}])
    assert voice_spoken.run(["import", str(src)], root=world.data) == 1
    assert "470-description" in capsys.readouterr().err
    vf.write_rows(src, [{**row, "spoken": "Un<o/a> come te, {name}."}])
    assert voice_spoken.run(["import", str(src)], root=world.data) == 0
    assert voice_make.read_spoken(world.data)[("470-description", "any")]["spoken"] == "Un<o/a> come te, {name}."
