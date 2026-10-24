"""wfj voice design: the roster's designed voices are made once and their ids written into voice.toml."""

from __future__ import annotations

import tomllib

import fake_gemini
import pytest

from wfj.cmd import voice_design
from wfj.io.gemini import Busy, Engine, EngineError

TOML = (
    'model = "gemini-3.8-flash-tts"\n\n'
    "[roster.mordo]\n"
    'design = "An undead man, raspy and dry."\n'
    'notes = "Brisk, natural pace."\n\n'
    "[roster.nar]\n"
    'voice = "Charon"\n'
    'notes = "Calm."\n\n'
    "[roster.mordo2]\n"
    'design = "An older undead man."\n'
    'notes = "Slow."\n'
)


def test_to_design_lists_designs_without_a_voice():
    assert voice_design.to_design(TOML) == [
        ("mordo", "An undead man, raspy and dry."), ("mordo2", "An older undead man."),
    ]


def test_with_voice_writes_the_id_under_its_own_table_only():
    out = voice_design.with_voice(TOML, "mordo", "voice_abc")
    roster = tomllib.loads(out)["roster"]
    assert roster["mordo"]["voice"] == "voice_abc"
    assert "voice" not in roster["mordo2"]
    assert out.replace('\nvoice = "voice_abc"', "", 1) == TOML
    with pytest.raises(ValueError, match=r"no \[roster.nobody\]"):
        voice_design.with_voice(TOML, "nobody", "voice_abc")


def test_design_makes_each_missing_voice_once(tmp_path):
    path = tmp_path / "voice.toml"
    path.write_text(TOML, encoding="utf-8")
    asked = []

    def create(name, description):
        asked.append((name, description))
        return f"voice_{len(asked)}"

    assert voice_design.design(path, create, say=lambda _: None) == (2, {})
    assert asked == [("ofi-mordo", "An undead man, raspy and dry."), ("ofi-mordo2", "An older undead man.")]
    roster = tomllib.loads(path.read_text(encoding="utf-8"))["roster"]
    assert (roster["mordo"]["voice"], roster["mordo2"]["voice"]) == ("voice_1", "voice_2")
    assert voice_design.design(path, create, say=lambda _: None) == (0, {})


def test_a_refused_design_does_not_stop_the_others(tmp_path):
    path = tmp_path / "voice.toml"
    path.write_text(TOML, encoding="utf-8")

    def create(name, description):
        if name == "ofi-mordo":
            raise EngineError("HTTP 400: Voice prompt was blocked by safety policies.")
        return "voice_ok"

    made, refused = voice_design.design(path, create, say=lambda _: None)
    assert made == 1 and list(refused) == ["mordo"]
    assert voice_design.to_design(path.read_text(encoding="utf-8")) == [("mordo", "An undead man, raspy and dry.")]


def test_a_busy_engine_stops_the_run(tmp_path):
    path = tmp_path / "voice.toml"
    path.write_text(TOML, encoding="utf-8")

    def create(name, description):
        raise Busy("HTTP 429")

    with pytest.raises(Busy):
        voice_design.design(path, create, say=lambda _: None)


def test_design_through_the_engine(tmp_path):
    server = fake_gemini.serve("ok")
    try:
        path = tmp_path / "voice.toml"
        path.write_text(TOML, encoding="utf-8")
        eng = Engine("k", base=fake_gemini.url(server), timeout=5)
        assert voice_design.design(path, eng.create_voice, say=lambda _: None) == (2, {})
        assert [c["path"] for c in server.calls] == ["/v1beta/voices"] * 2
        assert tomllib.loads(path.read_text(encoding="utf-8"))["roster"]["mordo"]["voice"] == "voice_test123"
    finally:
        server.shutdown()
        server.server_close()


def test_dry_run_makes_nothing(tmp_path, capsys):
    path = tmp_path / "voice.toml"
    path.write_text(TOML, encoding="utf-8")
    assert voice_design.run(["--config", str(path), "--dry-run"], root=tmp_path) == 0
    assert path.read_text(encoding="utf-8") == TOML
    assert "2 voice(s) to make" in capsys.readouterr().out
