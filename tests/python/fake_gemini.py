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

    def _send_raw(self, code: int, raw: bytes, headers: dict | None = None) -> None:
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    # ---- batch mode: upload (start, then the bytes), create, poll, download, cancel ----

    def _batch_post(self, raw: bytes) -> bool:
        srv = self.server
        if self.path == "/upload/v1beta/files":
            srv.calls.append({"path": self.path, "key": self.headers.get("x-goog-api-key"),
                              "headers": dict(self.headers), "body": json.loads(raw)})
            if srv.mode == "batch-busy":
                self._send(429, {"error": {"message": "quota"}})
                return True
            port = srv.server_address[1]
            self._send_raw(200, b"{}", {"X-Goog-Upload-URL": f"http://127.0.0.1:{port}/upload-session/1"})
            return True
        if self.path.startswith("/upload-session/"):
            name = f"files/in{len(srv.uploads) + 1}"
            srv.uploads[name] = raw
            srv.calls.append({"path": self.path, "key": self.headers.get("x-goog-api-key"),
                              "headers": dict(self.headers)})
            self._send(200, {"file": {"name": name}})
            return True
        if self.path.endswith(":batchGenerateContent"):
            body = json.loads(raw)
            srv.calls.append({"path": self.path, "key": self.headers.get("x-goog-api-key"), "body": body})
            name = f"batches/b{len(srv.batches) + 1}"
            srv.batches[name] = {"input": body["batch"]["input_config"]["file_name"], "polls": 0}
            self._send(200, {"name": name, "metadata": {"state": "JOB_STATE_PENDING"}})
            return True
        if self.path.endswith(":cancel"):
            srv.batches[self.path.split("/v1beta/", 1)[1].removesuffix(":cancel")]["cancelled"] = True
            self._send(200, {})
            return True
        return False

    def do_GET(self):
        srv = self.server
        srv.calls.append({"path": self.path, "key": self.headers.get("x-goog-api-key")})
        if self.path.startswith("/v1beta/batches/"):
            name = self.path.removeprefix("/v1beta/")
            job = srv.batches[name]
            job["polls"] += 1
            if job.get("cancelled"):
                return self._send(200, {"name": name, "metadata": {"state": "JOB_STATE_CANCELLED"}})
            if job["polls"] <= srv.running_polls:
                return self._send(200, {"name": name, "metadata": {"state": "JOB_STATE_RUNNING"}})
            out = f"files/out-{name.split('/')[1]}"
            srv.outputs[out] = batch_results(srv.uploads[job["input"]])
            return self._send(200, {"name": name, "metadata": {"state": "JOB_STATE_SUCCEEDED"},
                                    "response": {"responsesFile": out}})
        if self.path.startswith("/download/v1beta/") and self.path.endswith(":download?alt=media"):
            out = self.path.removeprefix("/download/v1beta/").removesuffix(":download?alt=media")
            return self._send_raw(200, srv.outputs[out], {"Content-Type": "application/jsonl"})
        return self._send(404, {"error": {"message": "not found"}})

    def do_POST(self):  # noqa: PLR0911 - one answer per mode
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        if self._batch_post(raw):
            return None
        body = json.loads(raw or b"{}")
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


def batch_results(jsonl: bytes) -> bytes:
    """The results file of a batch: per input line, audio (a 48 kHz WAV, as 3.8), a blocked take when the
    prompt says BLOCK, or an error when it says ERROR. Lines come back in reverse order: keys, not order,
    tie a result to its request."""
    out = []
    for line in jsonl.decode().splitlines():
        row = json.loads(line)
        text = row["request"]["contents"][0]["parts"][0]["text"]
        if "BLOCK" in text:
            out.append({"key": row["key"], "response": {"candidates": [{"finishReason": "SAFETY"}]}})
        elif "ERROR" in text:
            out.append({"key": row["key"], "error": {"code": 500, "message": "internal"}})
        else:
            part = {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(wav_with_metadata()).decode()}}
            out.append({"key": row["key"], "response": {"candidates": [
                {"content": {"parts": [part]}, "finishReason": "STOP"}]}})
    return "".join(json.dumps(r) + "\n" for r in reversed(out)).encode()


def serve(mode: str = "ok", running_polls: int = 0) -> HTTPServer:
    """`running_polls`: how many polls of a batch answer RUNNING before it SUCCEEDS."""
    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.mode = mode  # type: ignore[attr-defined]
    server.calls = []  # type: ignore[attr-defined]
    server.uploads, server.batches, server.outputs = {}, {}, {}  # type: ignore[attr-defined]
    server.running_polls = running_polls  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def url(server: HTTPServer) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}/v1beta"
