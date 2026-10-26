"""The Gemini TTS engine: request shape, blocked and busy takes, prompt, key handling (a fake server only)."""

from __future__ import annotations

import io
import json
import wave

import fake_gemini
import pytest

from wfj.io import gemini
from wfj.io.gemini import Blocked, Busy, Engine, EngineError

KEY = "AIzaSy-test-secret-key-123"


@pytest.fixture
def fake():
    servers = []

    def make(mode="ok"):
        s = fake_gemini.serve(mode)
        servers.append(s)
        return s, Engine(KEY, base=fake_gemini.url(s), timeout=5)

    yield make
    for s in servers:
        s.shutdown()
        s.server_close()


def test_synthesize_request_and_wav(fake):
    server, eng = fake("ok")
    wav = eng.synthesize("prompt", "Algenib")
    call = server.calls[0]
    assert call["path"] == "/v1beta/models/gemini-3.1-flash-tts-preview:generateContent"
    assert call["key"] == KEY
    gc = call["body"]["generationConfig"]
    assert gc["responseModalities"] == ["AUDIO"]
    assert gc["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Algenib"
    assert call["body"]["contents"] == [{"parts": [{"text": "prompt"}]}]
    assert "systemInstruction" not in call["body"]
    assert wav[:4] == b"RIFF"
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 24000)
        assert w.readframes(w.getnframes()) == fake_gemini.PCM


def test_whole_wav_answer_keeps_only_its_frames(fake):
    _, eng = fake("wav")
    wav = eng.synthesize("prompt", "Algenib")
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
        assert w.readframes(w.getnframes()) == fake_gemini.PCM
    assert b"C2PA" not in wav


@pytest.mark.parametrize("voice", ["voice_a74s310i6qa0", "it-it-advisor-1"])
def test_designed_and_library_voices_go_in_the_voice_field(fake, voice):
    server, eng = fake("ok")
    eng.synthesize("prompt", voice)
    assert server.calls[0]["body"]["generationConfig"]["speechConfig"]["voiceConfig"] == {"voice": voice}


def test_create_voice(fake):
    server, eng = fake("ok")
    assert eng.create_voice("ofi-mordo", "A raspy undead man.") == "voice_test123"
    call = server.calls[0]
    assert call["path"] == "/v1beta/voices"
    assert call["key"] == KEY
    assert call["body"] == {
        "store": True,
        "voice": {"type": "prompted", "display_name": "ofi-mordo", "language_code": "it-IT",
                  "prompted": {"input": "A raspy undead man."}},
    }


def test_create_voice_error_without_key(fake):
    _, eng = fake("http400")
    with pytest.raises(EngineError) as e:
        eng.create_voice("ofi-x", "A voice.")
    assert KEY not in str(e.value)


def test_voice_kinds():
    assert gemini.voice_kind("Algenib") == "prebuilt"
    assert gemini.voice_kind("voice_a74s310i6qa0") == "designed"
    assert gemini.voice_kind("it-it-advisor-1") == "library"
    assert gemini.voice_kind("algenib") is None
    assert gemini.voice_kind("voice_") is None


@pytest.mark.parametrize("mode", ["safety", "noaudio"])
def test_blocked_take(fake, mode):
    _, eng = fake(mode)
    with pytest.raises(Blocked):
        eng.synthesize("p", "Kore")


def test_http_error_is_engine_error_without_key(fake):
    _, eng = fake("http400")
    with pytest.raises(EngineError) as e:
        eng.synthesize("p", "Kore")
    assert not isinstance(e.value, (Blocked, Busy))
    assert KEY not in str(e.value)
    assert "400" in str(e.value)


def test_busy_is_not_a_try(fake):
    server, eng = fake("busy-then-ok")
    waits = []
    wav = gemini.synthesize_retry(eng, "p", "Kore", tries=1, sleep=waits.append)
    assert wav[:4] == b"RIFF"
    assert waits == [5]
    assert len(server.calls) == 2


def test_busy_forever_gives_up_after_the_waits():
    class Always(Engine):
        def synthesize(self, prompt, voice):
            raise Busy("HTTP 503")

    waits = []
    with pytest.raises(Busy):
        gemini.synthesize_retry(Always(KEY), "p", "Kore", sleep=waits.append)
    assert waits == [5, 15, 45, 120]


def test_four_blocked_takes_then_blocked(fake):
    server, eng = fake("safety")
    waits = []
    with pytest.raises(Blocked):
        gemini.synthesize_retry(eng, "p", "Kore", sleep=waits.append)
    assert len(server.calls) == 4
    assert waits == []


def test_unreachable_engine_error_without_key():
    eng = Engine(KEY, base="http://127.0.0.1:1/v1beta", timeout=2)
    with pytest.raises(EngineError) as e:
        eng.synthesize("p", "Kore")
    assert KEY not in str(e.value)


def test_prompt_text_sections():
    assert gemini.prompt_text("Mordo, undead", "Voice: raspy.", "[cough] Ah.") == (
        "# AUDIO PROFILE: Mordo, undead\n\n### DIRECTOR'S NOTES\nVoice: raspy.\n\n#### TRANSCRIPT\n[cough] Ah."
    )


def test_voices():
    assert len(gemini.GEMINI_VOICES) == 30
    assert len(set(gemini.GEMINI_VOICES)) == 30
    assert "Algenib" in gemini.GEMINI_VOICES


def test_read_key_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    f = tmp_path / ".env"
    f.write_text("GEMINI_API_KEY=other\n")
    assert gemini.read_key(f) == KEY
    assert gemini.read_key(None) == KEY


def test_read_key_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    f = tmp_path / ".env"
    f.write_text(f'# c\nELEVENLABS_API_KEY=xx\nexport GEMINI_API_KEY = "{KEY}"\n')
    assert gemini.read_key(f) == KEY


def test_read_key_missing_message_has_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    f = tmp_path / ".env"
    f.write_text(f"ELEVENLABS_API_KEY={KEY}\nGEMINI_API_KEY=\n")
    for arg in (f, None, tmp_path / "missing.env"):
        with pytest.raises(EngineError) as e:
            gemini.read_key(arg)
        assert KEY not in str(e.value)


def test_read_key_per_project(monkeypatch, tmp_path):
    for n in ("", "_2", "_3", "_4"):
        monkeypatch.delenv(f"GEMINI_API_KEY{n}", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_2", "two")
    f = tmp_path / ".env"
    f.write_text("GEMINI_API_KEY=one\nGEMINI_API_KEY_2=not-this\nexport GEMINI_API_KEY_3='three'\n")
    assert [gemini.read_key(f, n) for n in (1, 2, 3)] == ["one", "two", "three"]
    assert gemini.read_key(f) == "one"
    with pytest.raises(EngineError, match="no GEMINI_API_KEY_4 in the environment or in"):
        gemini.read_key(f, 4)
    with pytest.raises(EngineError, match="no project 0"):
        gemini.read_key(f, 0)


def test_projects_route_each_voice_through_its_projects_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "k2")
    monkeypatch.delenv("GEMINI_API_KEY_3", raising=False)
    server = fake_gemini.serve("ok")
    try:
        made = []

        def make(key, model):
            made.append(key)
            return Engine(key, model, base=fake_gemini.url(server), timeout=5)

        projects = gemini.Projects("gemini-3.8-flash-tts", None, {"voice_b": 2, "voice_c": 3}, make=make)
        assert made == []  # no key is read before its project is needed
        for voice in ("voice_b", "Algenib", "voice_unknown", "it-it-advisor-1"):
            projects.synthesize("prompt", voice)
        assert [c["key"] for c in server.calls] == ["k2", "k1", "k1", "k1"]
        assert made == ["k2", "k1"]  # an engine per project, made once
        assert [projects.project_of(v) for v in ("voice_b", "voice_c", "Charon", "voice_x")] == [2, 3, 1, 1]
        assert projects.has_key(2) and not projects.has_key(3)
        # a project whose key is missing fails only when a take needs it
        with pytest.raises(EngineError, match="no GEMINI_API_KEY_3"):
            projects.synthesize("prompt", "voice_c")
        assert "k1" not in repr(projects) and "k2" not in repr(projects)
    finally:
        server.shutdown()
        server.server_close()


def test_a_full_project_is_told_apart_from_the_daily_quota(fake):
    server, eng = fake("ok")
    server.full_keys.add(KEY)
    with pytest.raises(Busy) as e:
        eng.create_voice("ofi-x", "An old man.")
    assert gemini.voices_full(e.value)
    assert not gemini.voices_full(Busy("HTTP 429: Resource has been exhausted (e.g. check quota)."))
    assert not gemini.voices_full(Busy("HTTP 500: the maximum number of voices"))
    assert not gemini.voices_full(EngineError("HTTP 429: maximum number of voices"))


def test_repr_has_no_key():
    eng = Engine(KEY)
    assert KEY not in repr(eng)
    assert KEY not in str(eng)


# ---- batch mode ------------------------------------------------------------------------------------------


def _lines(*texts):
    return "".join(
        json.dumps({"key": f"k{i}", "request": gemini.request_body(t, "voice_abc")}) + "\n"
        for i, t in enumerate(texts)
    ).encode()


def test_batch_upload_create_poll_download(tmp_path):
    server = fake_gemini.serve("ok", running_polls=1)
    try:
        eng = Engine(KEY, model="gemini-3.8-flash-tts", base=fake_gemini.url(server), timeout=5)
        name = eng.upload("ofi-voce", _lines("Ciao.", "BLOCK"))
        assert name == "files/in1"
        start, send = server.calls[0], server.calls[1]
        assert start["path"] == "/upload/v1beta/files" and start["key"] == KEY
        assert start["headers"]["X-Goog-Upload-Command"] == "start"
        assert start["headers"]["X-Goog-Upload-Header-Content-Type"] == "application/jsonl"
        assert send["headers"]["X-Goog-Upload-Command"] == "upload, finalize"
        job = eng.create_batch("ofi-tirisfal", name)
        assert job == "batches/b1"
        create = server.calls[2]
        assert create["path"] == "/v1beta/models/gemini-3.8-flash-tts:batchGenerateContent"
        assert create["body"] == {"batch": {"display_name": "ofi-tirisfal", "input_config": {"file_name": name}}}
        first = eng.get_batch(job)
        assert gemini.batch_state(first) == "RUNNING" and gemini.batch_results_file(first) is None
        done = eng.get_batch(job)
        assert gemini.batch_state(done) == "SUCCEEDED"
        out = tmp_path / "out.jsonl"
        eng.download(gemini.batch_results_file(done), out)
        rows = {r["key"]: r for r in map(json.loads, out.read_text().splitlines())}
        assert set(rows) == {"k0", "k1"}
        with wave.open(io.BytesIO(gemini.answer_wav(rows["k0"]["response"]))) as w:
            assert w.getframerate() == 48000 and w.readframes(w.getnframes()) == fake_gemini.PCM
        with pytest.raises(Blocked):
            gemini.answer_wav(rows["k1"]["response"])
        assert all(c["key"] == KEY for c in server.calls if "upload-session" not in c["path"])
        assert all("key=" not in c["path"] for c in server.calls)
    finally:
        server.shutdown()
        server.server_close()


def test_batch_cancel(tmp_path):
    server = fake_gemini.serve("ok", running_polls=5)
    try:
        eng = Engine(KEY, base=fake_gemini.url(server), timeout=5)
        job = eng.create_batch("x", eng.upload("x", _lines("Ciao.")))
        eng.cancel_batch(job)
        assert gemini.batch_state(eng.get_batch(job)) == "CANCELLED"
    finally:
        server.shutdown()
        server.server_close()


def test_a_busy_upload_is_busy():
    server = fake_gemini.serve("batch-busy")
    try:
        with pytest.raises(Busy):
            Engine(KEY, base=fake_gemini.url(server), timeout=5).upload("x", b"{}\n")
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(("job", "state", "results"), [
    ({"metadata": {"state": "JOB_STATE_SUCCEEDED"}, "response": {"responsesFile": "files/a"}}, "SUCCEEDED", "files/a"),
    ({"state": "BATCH_STATE_RUNNING"}, "RUNNING", None),
    ({"state": "JOB_STATE_SUCCEEDED", "dest": {"fileName": "files/b"}}, "SUCCEEDED", "files/b"),
    ({"metadata": {"state": "BATCH_STATE_SUCCEEDED", "output": {"responsesFile": "files/c"}}}, "SUCCEEDED", "files/c"),
    ({}, "UNKNOWN", None),
])
def test_batch_state_and_results_in_every_documented_place(job, state, results):
    assert gemini.batch_state(job) == state
    assert gemini.batch_results_file(job) == results
