"""wfj voice design: the roster's designed voices are made once and their ids written into voice.toml, going
on in the next project when one is full."""

from __future__ import annotations

import tomllib

import fake_gemini
import pytest

from wfj.cmd import voice_design
from wfj.io import gemini
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
FULL = Busy('HTTP 429: {"error": {"code": 429, "message": "Project has reached the maximum number of voices."}}')
DOWN = Busy("HTTP 500: Voice synthesis service failed to process the request.")


def _toml(tmp_path, text=TOML):
    path = tmp_path / "voice.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _roster(path):
    return tomllib.loads(path.read_text(encoding="utf-8"))["roster"]


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


def test_with_voice_writes_the_project_after_the_first_and_replaces_an_old_one():
    out = voice_design.with_voice(TOML, "mordo2", "voice_abc", project=2)
    assert out.endswith('[roster.mordo2]\nvoice = "voice_abc"\nproject = 2\ndesign = "An older undead man."\n'
                        'notes = "Slow."\n')
    assert "project" not in tomllib.loads(out)["roster"]["mordo"]
    # a voice remade (its voice line deleted) keeps no project line of the old voice
    remade = voice_design.with_voice(out.replace('voice = "voice_abc"\n', ""), "mordo2", "voice_new", project=3)
    assert tomllib.loads(remade)["roster"]["mordo2"] == {
        "voice": "voice_new", "project": 3, "design": "An older undead man.", "notes": "Slow."}
    back = voice_design.with_voice(out.replace('voice = "voice_abc"\n', ""), "mordo2", "voice_one")
    assert "project" not in tomllib.loads(back)["roster"]["mordo2"]


def test_design_makes_each_missing_voice_once(tmp_path):
    path = _toml(tmp_path)
    asked = []

    def create(project, name, description):
        asked.append((project, name, description))
        return f"voice_{len(asked)}"

    assert voice_design.design(path, create, say=lambda _: None) == (2, {}, None)
    assert asked == [(1, "ofi-mordo", "An undead man, raspy and dry."), (1, "ofi-mordo2", "An older undead man.")]
    roster = _roster(path)
    assert (roster["mordo"]["voice"], roster["mordo2"]["voice"]) == ("voice_1", "voice_2")
    assert "project" not in roster["mordo"]
    assert voice_design.design(path, create, say=lambda _: None) == (0, {}, None)


def test_a_refused_design_does_not_stop_the_others(tmp_path):
    path = _toml(tmp_path)

    def create(project, name, description):
        if name == "ofi-mordo":
            raise EngineError("HTTP 400: Voice prompt was blocked by safety policies.")
        return "voice_ok"

    made, refused, stopped = voice_design.design(path, create, say=lambda _: None)
    assert made == 1 and list(refused) == ["mordo"] and stopped is None
    assert voice_design.to_design(path.read_text(encoding="utf-8")) == [("mordo", "An undead man, raspy and dry.")]


def test_a_busy_engine_stops_the_run(tmp_path):
    path = _toml(tmp_path)

    def create(project, name, description):
        raise Busy("HTTP 429: Resource has been exhausted (e.g. check quota).")

    waits = []
    with pytest.raises(Busy):
        voice_design.design(path, create, say=lambda _: None, sleep=waits.append, has_key=lambda _n: True)
    assert waits == [5, 15, 45]


def test_a_failure_inside_the_engine_is_asked_again(tmp_path):
    path = _toml(tmp_path)
    asked = []

    def create(project, name, description):
        asked.append(name)
        if len(asked) == 1:
            raise DOWN
        return "voice_ok"

    assert voice_design.design(path, create, say=lambda _: None, sleep=lambda _: None) == (2, {}, None)
    assert asked == ["ofi-mordo", "ofi-mordo", "ofi-mordo2"]


def test_a_voice_the_engine_keeps_failing_on_is_listed_and_the_others_made(tmp_path):
    path = _toml(tmp_path)
    waits = []

    def create(project, name, description):
        if name == "ofi-mordo":
            raise DOWN
        return "voice_ok"

    made, refused, stopped = voice_design.design(path, create, say=lambda _: None, sleep=waits.append)
    assert (made, list(refused), stopped) == (1, ["mordo"], None)
    assert refused["mordo"].startswith("HTTP 500") and waits == [5, 15, 45]
    assert _roster(path)["mordo2"]["voice"] == "voice_ok" and "voice" not in _roster(path)["mordo"]


def test_three_voices_failing_in_a_row_stop_the_run(tmp_path):
    text = TOML + "".join(f'\n[roster.x{i}]\ndesign = "A man, number {i}."\nnotes = "Slow."\n' for i in range(3))
    path = _toml(tmp_path, text)
    asked = []

    def create(project, name, description):
        asked.append(name)
        if name == "ofi-mordo2":
            return "voice_ok"
        raise DOWN

    made, refused, stopped = voice_design.design(path, create, say=lambda _: None, sleep=lambda _: None)
    # mordo fails, mordo2 is made (the count starts again), then x0, x1, x2 fail in a row: x2 is the third
    assert made == 1 and list(refused) == ["mordo", "x0", "x1", "x2"]
    assert "3 voices in a row" in stopped
    asked_again = []
    voice_design.design(path, lambda p, n, d: asked_again.append(n) or "voice_ok", say=lambda _: None)
    assert asked_again == ["ofi-mordo", "ofi-x0", "ofi-x1", "ofi-x2"]


def test_a_full_project_goes_on_in_the_next_and_writes_it(tmp_path):
    path = _toml(tmp_path)
    asked, said, waits = [], [], []

    def create(project, name, description):
        asked.append((project, name))
        if project == 1 and len(asked) > 1:
            raise FULL
        return f"voice_p{project}n{len(asked)}"

    got = voice_design.design(path, create, say=said.append, sleep=waits.append, has_key=lambda n: n <= 2)
    assert got == (2, {}, None)
    assert asked == [(1, "ofi-mordo"), (1, "ofi-mordo2"), (2, "ofi-mordo2")]
    assert waits == []  # a full project is not waited for
    roster = _roster(path)
    assert roster["mordo"] == {"voice": "voice_p1n1", "design": "An undead man, raspy and dry.",
                               "notes": "Brisk, natural pace."}
    assert (roster["mordo2"]["voice"], roster["mordo2"]["project"]) == ("voice_p2n3", 2)
    assert any("project 1 is full" in s for s in said)


def test_every_project_full_stops_with_what_was_made(tmp_path):
    path = _toml(tmp_path)

    def create(project, name, description):
        if project == 2:
            raise FULL
        return "voice_ok"

    made, refused, stopped = voice_design.design(path, create, say=lambda _: None, project=2,
                                                 has_key=lambda n: n <= 2)
    assert (made, refused) == (0, {})
    assert "project 2 is full" in stopped and "GEMINI_API_KEY_3" in stopped
    assert path.read_text(encoding="utf-8") == TOML


@pytest.fixture
def keys(monkeypatch):
    """Projects 1 and 2 keyed (k1, k2), none for 3; every engine made talks to one fake server."""
    server = fake_gemini.serve("ok")
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "k2")
    monkeypatch.delenv("GEMINI_API_KEY_3", raising=False)
    monkeypatch.setattr(gemini, "Engine", lambda key, model: Engine(key, model, base=fake_gemini.url(server),
                                                                     timeout=5))
    yield server
    server.shutdown()
    server.server_close()


def test_design_through_the_engine(tmp_path, keys):
    path = _toml(tmp_path)
    assert voice_design.run(["--config", str(path)], root=tmp_path) == 0
    assert [c["path"] for c in keys.calls] == ["/v1beta/voices"] * 2
    assert [c["key"] for c in keys.calls] == ["k1", "k1"]
    assert _roster(path)["mordo"]["voice"] == "voice_test123"


def test_the_command_goes_on_in_project_2_when_project_1_is_full(tmp_path, keys, capsys):
    keys.full_keys.add("k1")
    path = _toml(tmp_path)
    assert voice_design.run(["--config", str(path)], root=tmp_path) == 0
    # one call finds project 1 full; both voices are made in project 2
    assert [c["key"] for c in keys.calls] == ["k1", "k2", "k2"]
    roster = _roster(path)
    assert roster["mordo"]["project"] == roster["mordo2"]["project"] == 2
    assert "made 2 voice(s)" in capsys.readouterr().out


def test_the_command_starts_in_the_project_asked_and_stops_when_all_are_full(tmp_path, keys, capsys):
    keys.full_keys.add("k2")
    path = _toml(tmp_path)
    assert voice_design.run(["--config", str(path), "--project", "2"], root=tmp_path) == 1
    assert [c["key"] for c in keys.calls] == ["k2"]
    out = capsys.readouterr()
    assert "made 0 voice(s)" in out.out
    assert "project 2 is full" in out.err and "GEMINI_API_KEY_3" in out.err and "k2" not in out.err
    assert path.read_text(encoding="utf-8") == TOML
    assert voice_design.run(["--config", str(path), "--project", "3"], root=tmp_path) == 1
    assert "no GEMINI_API_KEY_3" in capsys.readouterr().err


def test_dry_run_makes_nothing(tmp_path, capsys):
    path = _toml(tmp_path)
    assert voice_design.run(["--config", str(path), "--dry-run"], root=tmp_path) == 0
    assert path.read_text(encoding="utf-8") == TOML
    assert "2 voice(s) to make" in capsys.readouterr().out
