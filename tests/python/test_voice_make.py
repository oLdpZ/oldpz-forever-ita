"""wfj voice plan|generate|status: the audio files of a scope, made by a stand-in Gemini engine and encoder (no
call ever reaches the real API)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import voice_fixture as vf

from wfj.cmd import voice_cast, voice_make
from wfj.core import voice
from wfj.io import gemini
from wfj.io.jsonl_store import Store

TOML = (
    'model = "gemini-3.1-flash-tts-preview"\nnarrator = "nar"\nbook_narrator = "book"\n'
    'narrator_profile = "The narrator of a fantasy adventure"\n'
    'book_narrator_profile = "A reader of old books and signs"\n'
    '[roster.nar]\nvoice = "Charon"\nnotes = "An even, warm storyteller."\nfits = "narrator"\n'
    '[roster.book]\nvoice = "Vindemiatrix"\nnotes = "Gentle and unhurried."\nfits = "book narrator"\n'
    '[roster.um]\nvoice = "Algenib"\nnotes = "Raspy and dry."\nfits = "undead male"\n'
    '[roster.uf]\nvoice = "Gacrux"\nnotes = "Hollow and cold."\nfits = "undead female"\n'
    '[[cast]]\nname = "undead, female"\nwhen = { archetype = "undead", gender = "female" }\nvoices = ["uf"]\n'
    '[[cast]]\nname = "undead"\nwhen = { archetype = "undead" }\nvoices = ["um"]\n'
)
SALVE = "Salve, {name}. Difendi la valle."
CLASS = "Un {class} come te serve qui."
PROFILE = {"source": "maintainer", "imported": "2026-10-23"}


def _it(id_, field, it):
    return {"id": id_, "field": field, "it": it, "status": "trusted"}


class FakeEngine:
    """Answers every prompt with half a second of silence; a transcript holding a word of `block` is stopped
    by the filter, and with `busy` every call is turned away."""

    def __init__(self, block=(), busy=False, error=None):
        self.calls: list[tuple[str, str]] = []
        self.block, self.busy, self.error = tuple(block), busy, error

    def synthesize(self, prompt: str, voice_name: str) -> bytes:
        self.calls.append((prompt, voice_name))
        said = transcript(prompt)
        if self.error:
            raise gemini.EngineError(self.error)
        if self.busy:
            raise gemini.Busy("HTTP 429: over quota")
        if any(b in said for b in self.block):
            raise gemini.Blocked("stopped (SAFETY)")
        return gemini.pcm_to_wav(b"\x00\x00" * 12000)

    def said(self) -> list[str]:
        return [transcript(p) for p, _ in self.calls]


def transcript(prompt: str) -> str:
    return prompt.split("#### TRANSCRIPT\n", 1)[1]


def fake_encode(wav_file: Path, out: Path) -> None:
    out.write_bytes(b"MP3" + wav_file.read_bytes()[:16])


def write_quests(data: Path, **changes: str) -> None:
    rows = {
        (456, "description"): SALVE,
        (456, "completion"): "Ben fatto.",
        (457, "description"): "Uccidi $N1 lupi.",
        (459, "description"): "Prega al santuario.",
        (470, "description"): CLASS,
        (470, "completion"): "Ottimo lavoro.",
    }
    for k, v in changes.items():
        q, f = k.split("_")
        rows[(int(q), f)] = v
    Store(data).save("quest", [_it(q, f, it) for (q, f), it in sorted(rows.items())])


@pytest.fixture
def world(tmp_path):
    """Quests 456, 457, 459 and 470 of the scope: Mordo (2079, undead male) offers 456 and 470 and thanks for
    456, the narrator reads 457, Saltain (1992, undead female) reads 459 and 5555 (no voice) 470's thanks."""
    data = vf.make_data(tmp_path)
    write_quests(data)
    vf.write_rows(data / "voice" / "speakers.jsonl", [
        {"key": "456-completion", "speaker": 2079, "provenance": vf.SRC},
        {"key": "456-description", "speaker": 2079, "provenance": vf.SRC},
        {"key": "457-description", "speaker": "narrator", "provenance": vf.SRC},
        {"key": "459-description", "speaker": 1992, "provenance": vf.SRC},
        {"key": "470-completion", "speaker": 5555, "provenance": vf.SRC},
        {"key": "470-description", "speaker": 2079, "provenance": vf.SRC},
    ])
    vf.write_rows(data / "voice" / "voices.jsonl", [
        {"creature": 1992, "voice": "uf", "row": "undead, female", "provenance": vf.SRC},
        {"creature": 2079, "voice": "um", "row": "undead", "provenance": vf.SRC},
    ])
    vf.write_rows(data / "voice" / "profiles.jsonl", [
        {"creature": 1992, "race": "scourge", "gender": "female", "age": "adult", "archetype": "undead",
         "provenance": {f: PROFILE for f in ("race", "gender", "age", "archetype")}},
        {"creature": 2079, "race": "scourge", "gender": "male", "age": "elder", "archetype": "undead",
         "role": "priest", "provenance": {f: PROFILE for f in ("race", "gender", "age", "archetype", "role")}},
    ])
    Store(data, english=True).save("unit", [
        {"id": 1992, "field": "name", "en": "Deathguard Saltain", "src": vf.COLLECTOR},
        {"id": 2079, "field": "name", "en": "Undertaker Mordo", "src": vf.COLLECTOR},
    ])
    scope = tmp_path / voice.SCOPES["tirisfal"]
    scope.parent.mkdir(parents=True)
    scope.write_text("456\n457\n459\n470\n")
    config = tmp_path / "voice.toml"
    config.write_text(TOML, encoding="utf-8")
    return SimpleNamespace(data=data, store=tmp_path / "store", cfg=voice_cast.load_config(config),
                           config=config, tmp=tmp_path)


def _gen(world, engine, **kw):
    return voice_make.generate(world.data, world.cfg, "tirisfal", world.store, engine, encode=fake_encode,
                               log=lambda *_: None, sleep=lambda _s: None, **kw)


def _audio(world) -> dict:
    return voice_make.audio_record(world.data)


def _spoken(world, rows) -> None:
    vf.write_rows(world.data / "voice" / "spoken.jsonl", rows)


# ---- generate --------------------------------------------------------------------------------------------


def test_a_plain_line_makes_one_file_and_a_name_makes_one_per_sex(world):
    engine = FakeEngine()
    r = _gen(world, engine)
    audio = _audio(world)
    assert sorted(audio) == ["456-completion", "456-description", "456-description_f", "457-description",
                             "459-description"]
    assert r["made"] == 5 and r["stopped"] is None
    said = dict(zip(engine.said(), (v for _, v in engine.calls), strict=True))
    assert said["Salve, eroe. Difendi la valle."] == "Algenib"
    assert said["Salve, eroina. Difendi la valle."] == "Algenib"
    assert said["Uccidi 7 lupi."] == "Charon"  # $N1 is the English's number
    assert said["Prega al santuario."] == "Gacrux"
    f = audio["456-description_f"]
    assert (f["key"], f["voice"], f["sex"], f["seconds"], f["chars"]) == (
        "456-description", "um", "f", 0.5, len("Salve, eroina. Difendi la valle."))
    assert f["it_hash"] == voice.it_hash(SALVE)
    r_um = world.cfg["roster"]["um"]
    assert f["fingerprint"] == voice.fingerprint(voice.text_hash(SALVE), "um", "Algenib", r_um["model"],
                                                 r_um["notes"], "f")
    assert audio["456-description"]["sex"] == "m"
    assert f["provenance"]["source"] == "gemini@gemini-3.1-flash-tts-preview"
    mp3 = world.store / "mp3" / "456-description_f.mp3"
    assert mp3.read_bytes().startswith(b"MP3") and f["bytes"] == mp3.stat().st_size
    assert f["sha256"] == voice_make.file_sha(mp3)
    assert (world.store / "wav" / "456-description_f.wav").is_file()  # the original take stays in the store
    status = json.loads((world.store / "status.json").read_text())
    assert (status["done"], status["total"], status["finished"]) == (5, 5, True)


def test_the_prompt_is_english_direction_over_the_italian_transcript(world):
    engine = FakeEngine()
    _gen(world, engine)
    prompts = {transcript(p): p for p, _ in engine.calls}
    mordo = prompts["Ben fatto."]
    assert mordo == gemini.prompt_text(
        "Undertaker Mordo; race: scourge; gender: male; age: elder; archetype: undead; role: priest",
        "Raspy and dry.", "Ben fatto.")
    assert prompts["Uccidi 7 lupi."].startswith("# AUDIO PROFILE: The narrator of a fantasy adventure\n")


def test_a_class_line_stays_silent_until_it_has_a_spoken_version(world):
    engine = FakeEngine()
    _gen(world, engine)
    assert "470-description" not in _audio(world)
    assert not [s for s in engine.said() if "{class}" in s or "Un " in s]
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    assert ("470-description", "no spoken version") in [(s, k) for s, k, _ in p["silent"]]
    _spoken(world, [{"key": "470-description", "sex": "any", "it_hash": voice.it_hash(CLASS),
                     "spoken": "Uno come te serve qui.", "reason": "names the class", "provenance": PROFILE}])
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 1
    assert engine.said() == ["Uno come te serve qui."]
    rec = _audio(world)["470-description"]
    assert rec["it_hash"] == voice.it_hash(CLASS)  # the addon still compares the written Italian
    r_um = world.cfg["roster"]["um"]
    assert rec["fingerprint"] == voice.fingerprint(voice.text_hash(CLASS, (), "Uno come te serve qui."), "um",
                                                   "Algenib", r_um["model"], r_um["notes"], "m")


def test_a_spoken_version_of_older_italian_is_ignored(world):
    _spoken(world, [{"key": "470-description", "sex": "any", "it_hash": voice.it_hash("Un tempo."),
                     "spoken": "Uno come te serve qui.", "reason": "names the class", "provenance": PROFILE}])
    engine = FakeEngine()
    _gen(world, engine)
    assert "Uno come te serve qui." not in engine.said()
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    assert ("470-description", "stale spoken version") in [(s, k) for s, k, _ in p["silent"]]


def test_a_spoken_version_with_the_name_is_made_for_each_sex(world):
    _spoken(world, [{"key": "470-description", "sex": "any", "it_hash": voice.it_hash(CLASS),
                     "spoken": "Uno come te serve qui, {name}.", "reason": "class", "provenance": PROFILE}])
    engine = FakeEngine()
    _gen(world, engine)
    assert {"470-description", "470-description_f"} <= set(_audio(world))
    assert {"Uno come te serve qui, eroe.", "Uno come te serve qui, eroina."} <= set(engine.said())


def test_a_spoken_version_for_one_sex_wins_over_one_for_both(world):
    write_quests(world.data, **{"470_description": "Un {class} come te, {name}."})
    it = "Un {class} come te, {name}."
    _spoken(world, [
        {"key": "470-description", "sex": "any", "it_hash": voice.it_hash(it), "spoken": "Uno come te, {name}.",
         "reason": "class", "provenance": PROFILE},
        {"key": "470-description", "sex": "f", "it_hash": voice.it_hash(it), "spoken": "Una come te, eroina.",
         "reason": "class", "provenance": PROFILE},
    ])
    engine = FakeEngine()
    _gen(world, engine)
    assert {"Uno come te, eroe.", "Una come te, eroina."} <= set(engine.said())


def test_four_blocked_takes_record_the_line_and_the_run_goes_on(world):
    engine = FakeEngine(block=["Ben fatto"])
    r = _gen(world, engine)
    assert engine.said().count("Ben fatto.") == 4
    assert "456-completion" not in _audio(world)
    assert not (world.store / "mp3" / "456-completion.mp3").exists()
    assert r["made"] == 4 and r["blocked"] == 1
    rows = [json.loads(x) for x in (world.store / "blocked.jsonl").read_text().splitlines()]
    assert [(b["key"], b["sex"], b["tries"], b["reason"]) for b in rows] == [
        ("456-completion", "m", 4, "stopped (SAFETY)")]
    # a blocked line is not asked again while its text and voice stay the same
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 0 and engine.calls == []
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    assert p["blocked"] == 1 and p["to_make"] == 0
    # changed Italian is a new line: asked again, and taken off the list once made
    write_quests(world.data, **{"456_completion": "Ben fatto, davvero."})
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 1
    assert (world.store / "blocked.jsonl").read_text() == ""


def test_a_rerun_makes_nothing_and_changed_italian_remakes_only_its_line(world):
    _gen(world, FakeEngine())
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 0 and engine.calls == []
    write_quests(world.data, **{"459_description": "Prega al santuario, presto."})
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 1
    assert engine.said() == ["Prega al santuario, presto."]


def test_a_file_gone_from_the_store_is_made_again(world):
    _gen(world, FakeEngine())
    (world.store / "mp3" / "457-description.mp3").unlink()
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 1 and engine.said() == ["Uccidi 7 lupi."]


def test_limit_stops_after_that_many_files_and_the_next_run_resumes(world):
    engine = FakeEngine()
    r = _gen(world, engine, limit=3)
    assert r["made"] == 3 and len(engine.calls) == 3 and len(_audio(world)) == 3
    status = json.loads((world.store / "status.json").read_text())
    assert (status["done"], status["total"]) == (3, 5)
    engine = FakeEngine()
    assert _gen(world, engine)["made"] == 2 and len(engine.calls) == 2


@pytest.mark.parametrize("engine", [FakeEngine(busy=True), FakeEngine(error="HTTP 500: internal")])
def test_a_busy_or_failing_engine_stops_the_run_and_keeps_what_was_made(world, engine):
    _gen(world, FakeEngine(), limit=2)
    r = _gen(world, engine)
    assert r["made"] == 0 and r["stopped"]
    assert len(_audio(world)) == 2  # the record survives the stop
    assert not (world.store / "blocked.jsonl").exists() or (world.store / "blocked.jsonl").read_text() == ""
    if engine.busy:
        assert len(engine.calls) == 5  # one take, then a call after each of the four waits
    status = json.loads((world.store / "status.json").read_text())
    assert status["finished"] is False


def test_a_line_the_voice_cannot_read_is_reported_and_the_rest_are_made(world):
    write_quests(world.data, **{"459_description": "Prega [sottovoce] al santuario."})
    engine = FakeEngine()
    r = _gen(world, engine)
    assert r["made"] == 4 and "459-description" not in _audio(world)
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    refused = {s: why for s, k, why in p["silent"] if k == "refused"}
    assert "sottovoce" in refused["459-description"]


def test_an_english_tag_is_sent_and_any_other_bracket_is_refused():
    assert voice_make.build_prompt("k", "Mordo", "Raspy.", "[sigh] Ancora tu.").endswith("[sigh] Ancora tu.")
    for bad in ("[sospira] Ancora tu.", "Ancora [tu.", "Ancora tu.]", "[Sigh] no."):
        with pytest.raises(voice.VoiceError, match="k: "):
            voice_make.build_prompt("k", "Mordo", "Raspy.", bad)
    with pytest.raises(voice.VoiceError, match="English only"):
        voice_make.build_prompt("k", "Il becchino", "Raspy.", "Ciao.")
    with pytest.raises(voice.VoiceError, match="English only"):
        voice_make.build_prompt("k", "Mordo", "Voce calma.", "Ciao.")


def test_a_speaker_with_no_voice_is_silent_and_named(world):
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    silent = {s: (k, why) for s, k, why in p["silent"]}
    assert silent["470-completion"] == ("no voice", "creature 5555 has no voice (wfj voice cast)")


def test_a_line_said_by_differently_cast_creatures_gets_a_file_per_voice(world):
    vf.write_rows(world.data / "voice" / "speakers.jsonl", [
        {"key": "456-description", "speaker": 2079, "others": [1992], "provenance": vf.SRC},
    ])
    engine = FakeEngine()
    _gen(world, engine)
    assert sorted(_audio(world)) == ["456-description", "456-description_f", "456-description_uf",
                                     "456-description_uf_f"]
    assert _audio(world)["456-description_uf_f"]["voice"] == "uf"
    prompts = [p for p, v in engine.calls if v == "Gacrux"]
    assert all(p.startswith("# AUDIO PROFILE: Deathguard Saltain; race: scourge; gender: female") for p in prompts)


def test_a_mixed_creature_reads_in_its_female_voice_too(world):
    vf.write_rows(world.data / "voice" / "voices.jsonl", [
        {"creature": 2079, "voice": "um", "row": "undead", "female": "uf", "female_row": "undead, female",
         "provenance": vf.SRC},
        {"creature": 1992, "voice": "uf", "row": "undead, female", "provenance": vf.SRC},
    ])
    rows = voice_make._rows(world.data / "voice" / "profiles.jsonl")
    rows[1]["gender"] = "mixed"
    vf.write_rows(world.data / "voice" / "profiles.jsonl", rows)
    engine = FakeEngine()
    _gen(world, engine)
    assert "456-completion_uf" in _audio(world)
    prompts = {v: p for p, v in engine.calls if transcript(p) == "Ben fatto."}
    assert "gender: male;" in prompts["Algenib"] and "gender: female;" in prompts["Gacrux"]


# ---- plan and status -------------------------------------------------------------------------------------


def test_plan_counts_lines_characters_hours_and_cost(world, capsys):
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    texts = ["Salve, eroe. Difendi la valle.", "Salve, eroina. Difendi la valle.", "Ben fatto.",
             "Uccidi 7 lupi.", "Prega al santuario."]
    chars = sum(map(len, texts))
    assert (p["files"], p["to_make"], p["missing"], p["stale"]) == (5, 5, 5, 0)
    assert p["chars"] == chars
    assert p["hours"] == pytest.approx(chars / 11 / 3600)
    assert p["dollars"] == pytest.approx(chars / 11 * 25 * 20 / 1_000_000)
    _gen(world, FakeEngine())
    write_quests(world.data, **{"456_completion": "Ben fatto, davvero."})
    p = voice_make.plan(world.data, world.cfg, "tirisfal", world.store)
    assert (p["missing"], p["stale"], p["to_make"], dict(p["by_voice"])) == (0, 1, 1, {"um": 1})
    assert voice_make.run(["plan", "--scope", "tirisfal", "--store", str(world.store),
                           "--config", str(world.config)], root=world.data) == 0
    out = capsys.readouterr().out
    assert "voice plan (tirisfal): 5 files; to make 1 (0 new, 1 changed)" in out
    assert "characters" in out and "h of audio" in out and "$" in out
    assert "silent: no voice: 1" in out and "silent: no spoken version: 1" in out


def test_status_says_finished_running_or_stopped(world, monkeypatch):
    assert voice_make.status_lines(world.store) == [f"voice status: no run recorded in {world.store}"]
    _gen(world, FakeEngine(), limit=2)
    assert "running: 2/5" in voice_make.status_lines(world.store)[0]  # this process wrote it, and lives

    def gone(pid, sig):
        raise ProcessLookupError(pid)

    monkeypatch.setattr(voice_make.os, "kill", gone)
    line = voice_make.status_lines(world.store)[0]
    assert "2/5 files (tirisfal)" in line and "stopped" in line and "make voice-generate" in line
    _gen(world, FakeEngine())
    assert "finished: 3/3" in voice_make.status_lines(world.store)[0]


# ---- the command -----------------------------------------------------------------------------------------


def test_generate_reads_the_key_and_never_prints_it(world, monkeypatch, capsys):
    monkeypatch.delenv(gemini.KEY_VAR, raising=False)
    args = ["generate", "--scope", "tirisfal", "--store", str(world.store), "--config", str(world.config)]
    assert voice_make.run(args, root=world.data) == 1
    assert "no GEMINI_API_KEY" in capsys.readouterr().err
    env = world.tmp / ".env"
    env.write_text("GEMINI_API_KEY=sekret-123\n")
    made: list[str] = []

    def engine(key, model):
        made.append(key)
        assert model == "gemini-3.1-flash-tts-preview"
        return FakeEngine()

    monkeypatch.setattr(voice_make, "make_engine", engine)
    monkeypatch.setattr(voice_make, "to_mp3", fake_encode)
    assert voice_make.run([*args, "--env-file", str(env), "--limit", "1"], root=world.data) == 0
    out = capsys.readouterr()
    assert made == ["sekret-123"] and "sekret" not in out.out + out.err
    assert "made 1 of 5 files" in out.out


def test_generate_stopped_by_the_engine_exits_with_a_resume_hint(world, monkeypatch, capsys):
    monkeypatch.setenv(gemini.KEY_VAR, "k")
    monkeypatch.setattr(voice_make, "make_engine", lambda key, model: FakeEngine(busy=True))
    monkeypatch.setattr(voice_make.time, "sleep", lambda _s: None)
    args = ["generate", "--scope", "tirisfal", "--store", str(world.store), "--config", str(world.config)]
    assert voice_make.run(args, root=world.data) == 1
    err = capsys.readouterr().err
    assert "HTTP 429" in err and "run it again to resume" in err


def test_generate_and_status_need_a_store(world, monkeypatch, capsys):
    monkeypatch.delenv("VOICE_ROOT", raising=False)
    with pytest.raises(SystemExit):
        voice_make.run(["status"], root=world.data)
    assert "--store" in capsys.readouterr().err
    monkeypatch.setenv("VOICE_ROOT", str(world.store))
    assert voice_make.run(["status"], root=world.data) == 0
    assert "no run recorded" in capsys.readouterr().out


# ---- the encoder -----------------------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("lame") is None, reason="lame is not installed")
def test_mp3_is_mono_22khz_32kbps_without_a_xing_frame(tmp_path):
    wav = tmp_path / "x.wav"
    wav.write_bytes(gemini.pcm_to_wav(b"\x00\x00" * 24000))
    out = tmp_path / "x.mp3"
    voice_make.to_mp3(wav, out)
    b = out.read_bytes()
    i = b.find(b"\xff")
    while not (b[i] == 0xFF and b[i + 1] & 0xE0 == 0xE0):
        i = b.find(b"\xff", i + 1)
    h = int.from_bytes(b[i:i + 4], "big")
    assert ((h >> 19) & 3, (h >> 17) & 3) == (2, 1)  # MPEG-2, Layer III
    assert (h >> 12) & 0xF == 4  # 32 kbps in the MPEG-2 Layer III table
    assert (h >> 10) & 3 == 0  # 22.05 kHz in MPEG-2
    assert (h >> 6) & 3 == 3  # mono
    assert b"Xing" not in b[:2048] and b"Info" not in b[:2048]
    assert wav.is_file() and not (tmp_path / "x.mp3.part").exists()


def test_wav_seconds_reads_the_take():
    assert voice_make.wav_seconds(gemini.pcm_to_wav(b"\x00\x00" * 36000)) == 1.5
