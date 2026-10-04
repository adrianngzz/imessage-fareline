"""Local brain. Photon and the uAgent both POST here. They do not split fares."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fareline.handle import handle
from fareline.intents import model_from_env
from fareline.ledger import Ledger

DEFAULT_PORT = 8787


def make_handler(ledger: Ledger, model=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self._send(200, {"ok": True})
                return
            if path == "/nets":
                self._send(200, ledger.public_state())
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path != "/act":
                self._send(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                self._send(400, {"error": "invalid json"})
                return
            speaker = body.get("speaker")
            text = body.get("text")
            if not isinstance(speaker, str) or not isinstance(text, str):
                self._send(400, {"error": "speaker and text are required"})
                return
            result = handle(text, speaker, ledger, model)
            print(f"{speaker}: {text} -> {result['action']}", flush=True)
            self._send(200, result)

        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def serve(ledger: Ledger, port: int = DEFAULT_PORT, model=None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(ledger, model))
    return server


def load_dotenv(path: Path | None = None) -> None:
    file = path or Path(".env")
    if not file.exists():
        return
    for line in file.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_dotenv()
    path = Path(os.environ.get("FARELINE_LEDGER_PATH", "data/ledger.json"))
    port = int(os.environ.get("FARELINE_PORT", str(DEFAULT_PORT)))
    ledger = Ledger(path)
    model = model_from_env()
    server = serve(ledger, port, model)
    print(f"Fareline ledger on http://127.0.0.1:{port}", flush=True)
    print(f"Ledger file: {path.resolve()}", flush=True)
    print("POST /act  {\"speaker\",\"text\"}    GET /nets", flush=True)
    if model is None:
        print("No LLM key set. Golden-transcript phrases still work.", flush=True)
    else:
        print("LLM is on for lines the golden phrases do not match.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
