"""wfj voice audition: the page of the first lines of each speaker, made by a stand-in engine (no call ever
reaches the real API)."""

from __future__ import annotations

import re

import test_voice_make as vm
import voice_fixture as vf

from wfj.cmd import voice, voice_audition, voice_make
from wfj.core import voice as core

world = vm.world  # the same small world as the generate tests
FakeEngine, fake_encode = vm.FakeEngine, vm.fake_encode


def _audition(world, engine=None, per=2):
    engine = engine or FakeEngine()
    path, result = voice_audition.audition(
        world.data, world.cfg, "tirisfal", world.store, engine, per, encode=fake_encode,
        log=lambda *_: None, sleep=lambda _s: None,
    )
    return path, result, engine


def _read(path):
    return path.read_text(encoding="utf-8")


def test_every_speaker_is_listed_once_with_its_voice_and_notes(world):
    path, _, _ = _audition(world)
    page = _read(path)
    assert path == world.store / "audition" / "index.html"
    for name in ("Undertaker Mordo", "Deathguard Saltain", "Narratore"):
        assert page.count(f"<h2>{name}</h2>") == 1
    assert "Algenib" in page and "Raspy and dry." in page
    assert "Undertaker Mordo; race: scourge; gender: male; age: elder; archetype: undead; role: priest" in page


def test_the_players_point_to_files_the_store_holds(world):
    path, _, _ = _audition(world)
    srcs = re.findall(r'<audio controls[^>]*src="([^"]+)"', _read(path))
    # Mordo's first two lines (the second for both sexes), the narrator's and Saltain's
    assert len(srcs) == 5
    for src in srcs:
        assert src.startswith("../mp3/")
        assert (path.parent / src).resolve().is_file()


def test_only_the_first_lines_of_each_speaker_are_made_and_only_once(world):
    path, result, engine = _audition(world, per=1)
    assert sorted(voice_make.audio_record(world.data)) == ["456-completion", "457-description", "459-description"]
    assert result["made"] == 3 and len(engine.calls) == 3
    assert len(re.findall(r"<audio ", _read(path))) == 3
    again = FakeEngine()
    _audition(world, again, per=1)
    assert again.calls == []  # the same cache as generate


def test_both_sexes_files_of_a_line_are_listed(world):
    path, _, _ = _audition(world)
    page = _read(path)
    assert "456-description_f" in page and "personaggio femminile" in page


def test_the_spoken_versions_show_the_written_text_beside_the_spoken_one(world):
    vf.write_rows(world.data / "voice" / "spoken.jsonl", [
        {"key": "470-description", "sex": "any", "it_hash": core.it_hash(vm.CLASS),
         "spoken": "Uno come te <serve> qui.", "reason": "names the class", "provenance": vm.PROFILE},
    ])
    path, _, _ = _audition(world)
    page = _read(path)
    assert "Versioni parlate" in page
    assert vm.CLASS in page and "Uno come te &lt;serve&gt; qui." in page and "names the class" in page
    assert "<serve>" not in page


def test_the_blocked_takes_are_listed(world):
    path, result, _ = _audition(world, FakeEngine(block=["Ben fatto"]))
    page = _read(path)
    assert result["blocked"] == 1
    assert "Bloccate" in page and "456-completion" in page and "stopped (SAFETY)" in page
    assert "file non generato" in page


def test_the_key_never_reaches_the_page(world, monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")
    keys = []

    def make_engine(key, model):
        keys.append((key, model))
        return FakeEngine()

    monkeypatch.setattr(voice_make, "make_engine", make_engine)
    monkeypatch.setattr(voice_make, "to_mp3", fake_encode)
    argv = ["--scope", "tirisfal", "--per", "2", "--store", str(world.store), "--config", str(world.config)]
    assert voice_audition.run(argv, root=world.data) == 0
    assert keys == [("SECRET-KEY-123", "gemini-3.1-flash-tts-preview")]
    assert "SECRET-KEY-123" not in _read(world.store / "audition" / "index.html")
    assert "SECRET-KEY-123" not in capsys.readouterr().out


def test_a_stopped_engine_still_writes_the_page_and_fails(world, monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(voice_make, "make_engine", lambda _k, _m: FakeEngine(error="down"))
    monkeypatch.setattr(voice_make, "to_mp3", fake_encode)
    argv = ["--scope", "tirisfal", "--store", str(world.store), "--config", str(world.config)]
    assert voice_audition.run(argv, root=world.data) == 1
    assert "stopped" in capsys.readouterr().err
    assert (world.store / "audition" / "index.html").is_file()


def test_the_dispatcher_knows_the_verb(world, monkeypatch):
    seen = []
    monkeypatch.setattr(voice_audition, "run", lambda argv, root=None: seen.append(list(argv)) or 0)
    assert voice.run(["audition", "--scope", "tirisfal"]) == 0
    assert seen == [["--scope", "tirisfal"]]


def test_generate_can_be_narrowed_to_some_lines(world):
    engine = FakeEngine()
    r = vm._gen(world, engine, keys={"457-description"})
    assert r["made"] == 1 and sorted(voice_make.audio_record(world.data)) == ["457-description"]
