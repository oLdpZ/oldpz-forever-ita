"""wfj voice batch: a scope's takes sent as one batch job per project, fetched into the store and recorded as
generate records them, against a fake Gemini (upload, job, poll, download)."""

from __future__ import annotations

import datetime
import json

import fake_gemini
import pytest
from test_voice_make import TOML, fake_encode, world, write_quests  # noqa: F401 - world is a fixture

from wfj.cmd import voice, voice_batch, voice_cast, voice_make
from wfj.io import gemini
from wfj.io.gemini import Engine, EngineError

ALL = ["456-completion", "456-description", "456-description_f", "457-description", "459-description"]


@pytest.fixture
def w(world):  # noqa: F811 - the fixture of test_voice_make
    return world


@pytest.fixture
def api(monkeypatch):
    """A fake Gemini and the engines of projects 1 and 2 (keys k1, k2) on it."""
    servers = []
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "k2")

    def make(running_polls=0):
        s = fake_gemini.serve("ok", running_polls=running_polls)
        servers.append(s)

        def engine(key, model):
            return Engine(key, model, base=fake_gemini.url(s), timeout=5)

        return s, gemini.Projects("gemini-3.8-flash-tts", make=engine)

    yield make
    for s in servers:
        s.shutdown()
        s.server_close()


def _clock(minute=0):
    return lambda: datetime.datetime(2026, 10, 25, 8, minute, tzinfo=datetime.UTC)


def _submit(w, engine, minute=0, **kw):
    return voice_batch.submit(w.data, w.cfg, "tirisfal", w.store, engine, now=_clock(minute), **kw)


def _fetch(w, engine):
    return voice_batch.fetch(w.data, w.cfg, w.store, engine, log=lambda _: None, encode=fake_encode)


def test_submit_fetch_records_every_take_without_asking_the_engine(w, api):
    server, eng = api(running_polls=1)
    [job] = _submit(w, eng)
    assert sorted(job["takes"]) == ALL and job["name"] == "batches/b1" and job["project"] == 1
    sent = [json.loads(ln) for ln in server.uploads["files/in1"].decode().splitlines()]
    assert sorted(r["key"] for r in sent) == ALL
    # each line is the request a direct call would send, the take's voice in it
    by_key = {r["key"]: r["request"] for r in sent}
    um = w.cfg["roster"]["um"]["gemini_voice"]
    assert by_key["456-description"]["generationConfig"]["speechConfig"]["voiceConfig"] == {
        "prebuiltVoiceConfig": {"voiceName": um}}
    record = json.loads((w.store / "batches" / "20261025T080000Z.json").read_text())
    assert record["fetched"] is False and record["scope"] == "tirisfal"
    # sent and waiting: not sent again
    assert _submit(w, eng, minute=1) == []
    # still running: nothing made yet
    r = _fetch(w, eng)
    assert (r["pending"], r["kept"], r["made"]) == (1, 0, 0)
    r = _fetch(w, eng)
    assert (r["pending"], r["kept"], r["made"], r["stopped"]) == (0, 5, 5, None)
    audio = voice_make.audio_record(w.data)
    assert sorted(audio) == ALL
    assert all(a["provenance"]["source"].startswith("gemini@") for a in audio.values())
    assert voice_make.plan(w.data, w.cfg, "tirisfal", w.store)["to_make"] == 0
    assert not any(":generateContent" in c["path"] for c in server.calls)
    assert json.loads((w.store / "batches" / "20261025T080000Z.json").read_text())["fetched"] is True
    assert not list((w.store / "batches").glob("*.out.jsonl"))  # the download is not kept
    assert _fetch(w, eng) == {"pending": 0, "kept": 0, "made": 0, "stopped": None}


def test_a_blocked_take_is_left_out_and_sent_again(w, api):
    write_quests(w.data, **{"459_description": "Prega BLOCK al santuario."})
    _, eng = api()
    _submit(w, eng)
    r = _fetch(w, eng)
    assert (r["kept"], r["made"]) == (4, 4)
    record = next(iter(voice_batch.read_jobs(w.store)))[1]
    assert record["blocked"] and record["blocked"][0].startswith("459-description")
    [again] = _submit(w, eng, minute=5)
    assert list(again["takes"]) == ["459-description"]


def test_limit_sends_the_first_n(w, api):
    _, eng = api()
    assert len(_submit(w, eng, limit=2)[0]["takes"]) == 2
    assert len(_submit(w, eng, minute=1)[0]["takes"]) == 3  # the rest, not the two waiting


def test_a_line_changed_after_sending_is_not_shipped_but_sent_again(w, api):
    _, eng = api()
    _submit(w, eng)
    write_quests(w.data, **{"459_description": "Prega al santuario, presto."})
    r = _fetch(w, eng)
    assert (r["kept"], r["made"]) == (5, 4)
    assert "459-description" not in voice_make.audio_record(w.data)
    [again] = _submit(w, eng, minute=5)
    assert list(again["takes"]) == ["459-description"]


def test_cancel_asks_for_every_waiting_job(w, api):
    server, eng = api(running_polls=9)
    _submit(w, eng)
    assert voice_batch.cancel(w.store, eng, log=lambda _: None) == 1
    r = _fetch(w, eng)
    assert (r["pending"], r["kept"]) == (0, 0)
    assert json.loads((w.store / "batches" / "20261025T080000Z.json").read_text())["state"] == "CANCELLED"


def _two_projects(w):
    """The world with Saltain's voice (uf) a designed voice made in project 2."""
    config = w.tmp / "voice-projects.toml"
    config.write_text(TOML.replace(
        '[roster.uf]\nvoice = "Gacrux"\n',
        '[roster.uf]\nvoice = "voice_uf1"\ndesign = "A hollow, cold undead woman."\nproject = 2\n'), encoding="utf-8")
    w.cfg = voice_cast.load_config(config)
    return w


def test_takes_go_in_one_job_per_project_and_come_back_through_its_key(w, api):
    w = _two_projects(w)
    server, eng = api(running_polls=1)
    one, two = _submit(w, eng)
    assert (one["project"], sorted(one["takes"])) == (1, [k for k in ALL if k != "459-description"])
    assert (two["project"], list(two["takes"]), two["name"]) == (2, ["459-description"], "batches/b2")
    created = [c for c in server.calls if c["path"].endswith(":batchGenerateContent")]
    assert [(c["key"], c["body"]["batch"]["display_name"]) for c in created] == [
        ("k1", "ofi-tirisfal-20261025T080000Z"), ("k2", "ofi-tirisfal-20261025T080000Z-p2")]
    sent = [json.loads(ln) for ln in server.uploads[two["input"]].decode().splitlines()]
    assert sent[0]["request"]["generationConfig"]["speechConfig"]["voiceConfig"] == {"voice": "voice_uf1"}
    assert sorted(p.name for p in (w.store / "batches").glob("*.json")) == [
        "20261025T080000Z-p2.json", "20261025T080000Z.json"]
    assert _submit(w, eng, minute=1) == []
    del server.calls[:]
    _fetch(w, eng)
    r = _fetch(w, eng)
    assert (r["pending"], r["kept"], r["made"]) == (0, 5, 5)
    polls = [(c["path"], c["key"]) for c in server.calls if c["path"].startswith("/v1beta/batches/")]
    assert sorted(set(polls)) == [("/v1beta/batches/b1", "k1"), ("/v1beta/batches/b2", "k2")]
    downloads = {c["key"] for c in server.calls if c["path"].startswith("/download/")}
    assert downloads == {"k1", "k2"}


def test_a_job_recorded_before_projects_is_fetched_with_project_1(w, api):
    server, eng = api()
    _submit(w, eng)
    record = w.store / "batches" / "20261025T080000Z.json"
    old = json.loads(record.read_text())
    del old["project"]
    record.write_text(json.dumps(old))
    assert _fetch(w, eng)["kept"] == 5
    assert {c["key"] for c in server.calls if c["path"].startswith("/v1beta/batches/")} == {"k1"}


def test_a_missing_key_sends_nothing(w, api, monkeypatch):
    w = _two_projects(w)
    monkeypatch.delenv("GEMINI_API_KEY_2")
    server, eng = api()
    with pytest.raises(EngineError, match="no GEMINI_API_KEY_2"):
        _submit(w, eng)
    assert server.calls == [] and not (w.store / "batches").exists()


def test_the_verb_is_reached_through_wfj_voice(w, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert voice.run(["batch", "fetch", "--store", str(w.store), "--config", str(w.config)]) == 1
    assert "GEMINI_API_KEY" in capsys.readouterr().err


def test_max_tokens_sends_one_small_job_per_free_project_and_the_rest_later(w, api):
    s, engine = api()
    one = _submit(w, engine, max_tokens=1)
    assert [len(j["takes"]) for j in one] == [1]
    assert _submit(w, engine, minute=1, max_tokens=10**6) == []  # project 1 still has a job waiting
    _fetch(w, engine)
    rest = _submit(w, engine, minute=2, max_tokens=10**6)
    assert len(rest[0]["takes"]) == len(ALL) - 1
