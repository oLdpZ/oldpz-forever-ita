"""A stand-in for the Gemini API's `generateContent`, for the tests of the Gemini engine.

`serve(mode)` listens on a free local port and keeps what it was asked in `server.calls`. Modes: `ok`,
`safety` (finishReason SAFETY, no audio), `busy-then-ok` (503 once, then ok), `noaudio` (a candidate with
no inlineData), `http400`.
"""

from __future__ import annotations

import base64
import json
import threading
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
        if mode == "http400":
            return self._send(400, {"error": {"message": f"bad request {self.headers.get('x-goog-api-key')}"}})
        if mode == "busy-then-ok" and len(srv.calls) == 1:
            return self._send(503, {"error": {"message": "high demand"}})
        if mode == "safety":
            return self._send(200, {"candidates": [{"finishReason": "SAFETY"}]})
        if mode == "noaudio":
            return self._send(200, {"candidates": [{"content": {"parts": [{"text": "hm"}]}, "finishReason": "STOP"}]})
        data = base64.b64encode(PCM).decode()
        part = {"inlineData": {"mimeType": "audio/L16;rate=24000", "data": data}}
        return self._send(200, {"candidates": [{"content": {"parts": [part]}, "finishReason": "STOP"}]})


def serve(mode: str = "ok") -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.mode = mode  # type: ignore[attr-defined]
    server.calls = []  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def url(server: HTTPServer) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}/v1beta"
