"""The Google Gemini TTS engine over HTTPS (stdlib only): one line's prompt in, one WAV out.

A line is one `generateContent` call on a TTS model. The key travels only in the `x-goog-api-key` header:
it is never part of a URL, a message or a repr. The audio comes back as base64 PCM (s16le, mono, 24 kHz).
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request
import wave
from collections.abc import Callable
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

    def _post(self, body: dict[str, Any]) -> Any:
        url = f"{self.base}/models/{self.model}:generateContent"
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self._key},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = self._scrub(e.read().decode("utf-8", "replace"))[:300]
            if e.code in (429, 503):
                raise Busy(f"HTTP {e.code}: {detail}") from None
            raise EngineError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as e:
            raise EngineError(self._scrub(f"{self.model}: {e}")) from None
        except ValueError:
            raise EngineError("the answer is not JSON") from None

    def synthesize(self, prompt: str, voice: str) -> bytes:
        """One take as a WAV (mono, 24 kHz). `Blocked` when the filter stopped it or no audio came."""
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
            },
        }
        answer = self._post(body)
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
            pcm = base64.b64decode(data, validate=True)
        except ValueError:
            raise EngineError("the audio is not valid base64") from None
        return pcm_to_wav(pcm)


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
