"""wfj voice batch: a scope's takes sent as one batch job, fetched into the store and recorded as generate
records them, against a fake Gemini (upload, job, poll, download)."""

from __future__ import annotations

import datetime
import json

import fake_gemini
import pytest
from test_voice_make import fake_encode, world, write_quests  # noqa: F401 - world is a fixture

from wfj.cmd import voice, voice_batch, voice_make
from wfj.io.gemini import Engine

ALL = ["456-completion", "456-description", "456-description_f", "457-description", "459-description"]


@pytest.fixture
def w(world):  # noqa: F811 - the fixture of test_voice_make
    return world


@pytest.fixture
def api():
    servers = []

    def make(running_polls=0):
        s = fake_gemini.serve("ok", running_polls=running_polls)
        servers.append(s)
        return s, Engine("k", model="gemini-3.8-flash-tts", base=fake_gemini.url(s), timeout=5)

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
    job = _submit(w, eng)
    assert sorted(job["takes"]) == ALL and job["name"] == "batches/b1"
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
    assert _submit(w, eng, minute=1) is None
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
    again = _submit(w, eng, minute=5)
    assert list(again["takes"]) == ["459-description"]


def test_limit_sends_the_first_n(w, api):
    _, eng = api()
    assert len(_submit(w, eng, limit=2)["takes"]) == 2
    assert len(_submit(w, eng, minute=1)["takes"]) == 3  # the rest, not the two waiting


def test_a_line_changed_after_sending_is_not_shipped_but_sent_again(w, api):
    _, eng = api()
    _submit(w, eng)
    write_quests(w.data, **{"459_description": "Prega al santuario, presto."})
    r = _fetch(w, eng)
    assert (r["kept"], r["made"]) == (5, 4)
    assert "459-description" not in voice_make.audio_record(w.data)
    again = _submit(w, eng, minute=5)
    assert list(again["takes"]) == ["459-description"]


def test_cancel_asks_for_every_waiting_job(w, api):
    server, eng = api(running_polls=9)
    _submit(w, eng)
    assert voice_batch.cancel(w.store, eng, log=lambda _: None) == 1
    r = _fetch(w, eng)
    assert (r["pending"], r["kept"]) == (0, 0)
    assert json.loads((w.store / "batches" / "20261025T080000Z.json").read_text())["state"] == "CANCELLED"


def test_the_verb_is_reached_through_wfj_voice(w, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert voice.run(["batch", "fetch", "--store", str(w.store), "--config", str(w.config)]) == 1
    assert "GEMINI_API_KEY" in capsys.readouterr().err
