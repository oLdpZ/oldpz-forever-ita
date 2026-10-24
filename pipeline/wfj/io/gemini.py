"""The Google Gemini TTS engine over HTTPS (stdlib only): one line's prompt in, one WAV out.

A line is one `generateContent` call on a TTS model. The key travels only in the `x-goog-api-key` header:
it is never part of a URL, a message or a repr. The audio comes back as base64 PCM (s16le, mono, 24 kHz),
or (3.8) as a whole WAV whose data chunk is followed by a metadata chunk: only its frames are kept.

A voice is a prebuilt name (`Algenib`), a library voice (`it-it-…`) or a designed voice (`voice_…`, made
from an English description with `create_voice` and kept by the API).
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import wave
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

API = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.1-flash-tts-preview"
RATE = 24000
KEY_VAR = "GEMINI_API_KEY"

# the 30 prebuilt voices of the Gemini TTS models
GEMINI_VOICES = (
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe",
    "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi",
    "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
)  # fmt: skip
_DESIGNED = re.compile(r"voice_[a-z0-9]+")
_LIBRARY = re.compile(r"[a-z]{2}-[a-z]{2}-[a-z0-9]+(?:-[a-z0-9]+)*")


def voice_kind(voice: str) -> str | None:
    """`prebuilt`, `library` or `designed`, or None when `voice` is none of them."""
    if voice in GEMINI_VOICES:
        return "prebuilt"
    if _DESIGNED.fullmatch(voice):
        return "designed"
    if _LIBRARY.fullmatch(voice):
        return "library"
    return None


# finish reasons of a take the safety filter stopped (random: the same line often passes on another try)
_BLOCKED = ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY")


class EngineError(RuntimeError):
    """The engine is not answering, or answered with an error."""


class Blocked(EngineError):
    """The safety filter stopped the take, or it carried no audio."""


class Busy(EngineError):
    """The engine is overloaded or over quota (429, 503): wait and ask again."""


def prompt_text(profile: str, notes: str, transcript: str) -> str:
    """The prompt in the three sections the model follows: who speaks, how, and what."""
    return f"# AUDIO PROFILE: {profile}\n\n### DIRECTOR'S NOTES\n{notes}\n\n#### TRANSCRIPT\n{transcript}"


def pcm_to_wav(pcm: bytes, rate: int = RATE) -> bytes:
    """Raw PCM s16le mono as a WAV file."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def audio_to_wav(raw: bytes) -> bytes:
    """The engine's audio as a clean WAV: raw PCM is wrapped; a WAV keeps only its audio frames (the chunk
    3.8 adds after them is metadata, read as sound it is a loud noise at the end)."""
    if raw[:4] != b"RIFF":
        return pcm_to_wav(raw)
    try:
        with wave.open(io.BytesIO(raw), "rb") as r:
            channels, width, rate = r.getnchannels(), r.getsampwidth(), r.getframerate()
            frames = r.readframes(r.getnframes())
    except (wave.Error, EOFError):
        raise EngineError("the audio is not a valid WAV") from None
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(frames)
    return buf.getvalue()


def request_body(prompt: str, voice: str) -> dict[str, Any]:
    """One take's `generateContent` request: the same in a direct call and in a batch file's line."""
    if voice_kind(voice) == "prebuilt":
        voice_config: dict[str, Any] = {"prebuiltVoiceConfig": {"voiceName": voice}}
    else:
        voice_config = {"voice": voice}
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": voice_config}},
    }


def answer_wav(answer: Any) -> bytes:
    """The WAV of one `generateContent` answer (direct, or a batch result line's `response`). `Blocked` when
    the filter stopped it or no audio came."""
    if not isinstance(answer, dict):
        raise EngineError("unexpected answer")
    cands = answer.get("candidates")
    cand = cands[0] if isinstance(cands, list) and cands and isinstance(cands[0], dict) else {}
    parts = (cand.get("content") or {}).get("parts") or []
    data = None
    if parts and isinstance(parts[0], dict):
        data = (parts[0].get("inlineData") or {}).get("data")
    if not data:
        reason = cand.get("finishReason") or (answer.get("promptFeedback") or {}).get("blockReason")
        raise Blocked(f"no audio ({reason or 'no reason given'})")
    if cand.get("finishReason") in _BLOCKED:
        raise Blocked(f"stopped ({cand['finishReason']})")
    try:
        raw = base64.b64decode(data, validate=True)
    except ValueError:
        raise EngineError("the audio is not valid base64") from None
    return audio_to_wav(raw)


# a batch's state, with either prefix the API uses (JOB_STATE_…, BATCH_STATE_…) taken off
BATCH_DONE = ("SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED")


def batch_state(job: Mapping[str, Any]) -> str:
    """PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED, EXPIRED (or UNKNOWN). The docs read it from
    `metadata.state` or from `state`: both are taken."""
    state = (job.get("metadata") or {}).get("state") or job.get("state") or "UNKNOWN"
    return str(state).removeprefix("JOB_STATE_").removeprefix("BATCH_STATE_")


def batch_results_file(job: Mapping[str, Any]) -> str | None:
    """The `files/…` holding a finished batch's results (`response.responsesFile`, or `dest.fileName`, or
    under `metadata.output`: the docs name all three)."""
    for holder in (job.get("response"), job.get("dest"), (job.get("metadata") or {}).get("output")):
        if isinstance(holder, Mapping):
            name = holder.get("responsesFile") or holder.get("fileName")
            if isinstance(name, str) and name:
                return name
    return None


def read_key(env_file: Path | None = None) -> str:
    """The API key: `GEMINI_API_KEY` from the environment, else from a `.env` file (`NAME=value` lines)."""
    key = os.environ.get(KEY_VAR, "").strip()
    if key:
        return key
    if env_file is not None:
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            raise EngineError(f"cannot read {env_file}: {e.strerror or type(e).__name__}") from None
        for raw in lines:
            name, sep, value = raw.strip().removeprefix("export ").partition("=")
            if sep and name.strip() == KEY_VAR:
                value = value.strip().strip("'\"").strip()
                if value:
                    return value
    where = f" or in {env_file}" if env_file is not None else ""
    raise EngineError(f"no {KEY_VAR} in the environment{where}")


class Engine:
    def __init__(self, key: str, model: str = MODEL, base: str = API, timeout: float = 120.0):
        if not key:
            raise EngineError("empty API key")
        self._key = key
        self.model = model
        self.base = base.rstrip("/")
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"Engine(model={self.model!r}, base={self.base!r})"

    def _scrub(self, text: str) -> str:
        return text.replace(self._key, "***")

    def _open(self, req: urllib.request.Request) -> tuple[bytes, Any]:
        """(body, headers) of a request carrying the key in its header; HTTP errors as the engine's errors."""
        req.add_header("x-goog-api-key", self._key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.read(), r.headers
        except urllib.error.HTTPError as e:
            detail = self._scrub(e.read().decode("utf-8", "replace"))[:300]
            if e.code in (429, 503):
                raise Busy(f"HTTP {e.code}: {detail}") from None
            raise EngineError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as e:
            raise EngineError(self._scrub(f"{self.model}: {e}")) from None

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(f"{self.base}/{path}", data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        raw, _ = self._open(req)
        try:
            return json.loads(raw or b"{}")
        except ValueError:
            raise EngineError("the answer is not JSON") from None

    def _post(self, body: dict[str, Any], path: str | None = None) -> Any:
        return self._call("POST", path or f"models/{self.model}:generateContent", body)

    def synthesize(self, prompt: str, voice: str) -> bytes:
        """One take as a WAV (mono). `Blocked` when the filter stopped it or no audio came."""
        return answer_wav(self._post(request_body(prompt, voice)))

    # ---- batch mode: many takes in one job, half the price, done within a day (no daily request cap) ----

    def _root(self) -> str:
        """The API's host part, before /v1beta (uploads and downloads have their own paths under it)."""
        return self.base.rsplit("/", 1)[0]

    def upload(self, name: str, data: bytes, mime: str = "application/jsonl") -> str:
        """A file through the File API's resumable upload (start, then upload and finalize): its `files/…`."""
        start = urllib.request.Request(
            f"{self._root()}/upload/{self.base.rsplit('/', 1)[1]}/files",
            data=json.dumps({"file": {"display_name": name}}).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(len(data)),
                "X-Goog-Upload-Header-Content-Type": mime,
            },
        )
        _, headers = self._open(start)
        url = headers.get("X-Goog-Upload-URL") or headers.get("x-goog-upload-url")
        if not url:
            raise EngineError("the upload was not started (no upload URL)")
        send = urllib.request.Request(
            url, data=data, method="POST",
            headers={"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"},
        )
        raw, _ = self._open(send)
        try:
            answer = json.loads(raw)
        except ValueError:
            raise EngineError("the upload answer is not JSON") from None
        file_name = (answer.get("file") or {}).get("name") if isinstance(answer, dict) else None
        if not file_name:
            raise EngineError("no file name in the upload answer")
        return str(file_name)

    def create_batch(self, display_name: str, file_name: str) -> str:
        """A batch job over an uploaded JSONL file of `{"key", "request"}` lines: its `batches/…` name."""
        body = {"batch": {"display_name": display_name, "input_config": {"file_name": file_name}}}
        answer = self._post(body, f"models/{self.model}:batchGenerateContent")
        name = answer.get("name") if isinstance(answer, dict) else None
        if not isinstance(name, str) or not name.startswith("batches/"):
            raise EngineError("no batch name in the answer")
        return name

    def get_batch(self, name: str) -> dict[str, Any]:
        answer = self._call("GET", name)
        if not isinstance(answer, dict):
            raise EngineError("unexpected batch answer")
        return answer

    def cancel_batch(self, name: str) -> None:
        self._call("POST", f"{name}:cancel", {})

    def download(self, file_name: str, out: Path) -> None:
        """A result file (`files/…`) written to `out`, streamed: a whole scope's audio is large."""
        version = self.base.rsplit("/", 1)[1]
        req = urllib.request.Request(f"{self._root()}/download/{version}/{file_name}:download?alt=media")
        req.add_header("x-goog-api-key", self._key)
        part = out.with_name(out.name + ".part")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r, part.open("wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            part.replace(out)
        except urllib.error.HTTPError as e:
            detail = self._scrub(e.read().decode("utf-8", "replace"))[:300]
            raise EngineError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as e:
            raise EngineError(self._scrub(f"download: {e}")) from None
        finally:
            part.unlink(missing_ok=True)

    def create_voice(self, name: str, description: str, language: str = "it-IT") -> str:
        """A designed voice made from an English description and kept by the API (it lasts a year from its
        last use, up to 200 per project): its `voice_…` id."""
        body = {
            "store": True,
            "voice": {"type": "prompted", "display_name": name, "language_code": language,
                      "prompted": {"input": description}},
        }
        answer = self._post(body, "voices")
        vid = ""
        if isinstance(answer, dict):
            vid = answer.get("id") or str(answer.get("name", "")).rsplit("/", 1)[-1]
        if voice_kind(vid) != "designed":
            raise EngineError(f"no voice id in the answer ({str(vid)[:40]!r})")
        return vid


def synthesize_retry(
    engine: Engine,
    prompt: str,
    voice: str,
    tries: int = 4,
    waits: tuple[float, ...] = (5, 15, 45, 120),
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """`synthesize` with retries. A blocked take is asked again, up to `tries` takes in all, then `Blocked`.
    A busy engine is waited for (`waits` in turn) without using up a take, then `Busy` once the waits end."""
    taken = 0
    waited = 0
    while True:
        try:
            return engine.synthesize(prompt, voice)
        except Blocked:
            taken += 1
            if taken >= tries:
                raise
        except Busy:
            if waited >= len(waits):
                raise
            sleep(waits[waited])
            waited += 1
