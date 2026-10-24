"""A stand-in for the Gemini API's `generateContent`, for the tests of the Gemini engine.

`serve(mode)` listens on a free local port and keeps what it was asked in `server.calls`. Modes: `ok`,
`safety` (finishReason SAFETY, no audio), `busy-then-ok` (503 once, then ok), `noaudio` (a candidate with
no inlineData), `http400`, `wav` (a whole WAV at 48 kHz with a trailing metadata chunk, as 3.8 answers).
A POST to `/voices` (making a designed voice) answers with the id `voice_test123`.
"""

from __future__ import annotations

import base64
import io
import json
import struct
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

PCM = b"\x01\x00" * 2400  # 0.1 s at 24 kHz


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        srv = self.server
        srv.calls.append({"path": self.path, "key": self.headers.get("x-goog-api-key"), "body": body})
        if "key=" in self.path:
            return self._send(400, {"error": {"message": "key in the URL"}})
        mode = srv.mode
        if self.path.endswith("/voices") and mode != "http400":
            return self._send(200, {"id": "voice_test123", "type": "prompted"})
        if mode == "http400":
            return self._send(400, {"error": {"message": f"bad request {self.headers.get('x-goog-api-key')}"}})
        if mode == "busy-then-ok" and len(srv.calls) == 1:
            return self._send(503, {"error": {"message": "high demand"}})
        if mode == "safety":
            return self._send(200, {"candidates": [{"finishReason": "SAFETY"}]})
        if mode == "noaudio":
            return self._send(200, {"candidates": [{"content": {"parts": [{"text": "hm"}]}, "finishReason": "STOP"}]})
        if mode == "wav":
            data = base64.b64encode(wav_with_metadata()).decode()
            part = {"inlineData": {"mimeType": "audio/wav", "data": data}}
            return self._send(200, {"candidates": [{"content": {"parts": [part]}, "finishReason": "STOP"}]})
        data = base64.b64encode(PCM).decode()
        part = {"inlineData": {"mimeType": "audio/L16;rate=24000", "data": data}}
        return self._send(200, {"candidates": [{"content": {"parts": [part]}, "finishReason": "STOP"}]})


def wav_with_metadata() -> bytes:
    """PCM as a 48 kHz WAV followed by a chunk that is not audio (3.8 adds C2PA metadata after the data)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(PCM)
    raw = buf.getvalue()
    meta = b"C2PA" + struct.pack("<I", 8) + b"metadata"
    return b"RIFF" + struct.pack("<I", len(raw) - 8 + len(meta)) + raw[8:] + meta


def serve(mode: str = "ok") -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.mode = mode  # type: ignore[attr-defined]
    server.calls = []  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def url(server: HTTPServer) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}/v1beta"
