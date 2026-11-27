"""Shared helpers for the W&B Cline launcher tests: the launcher loaded by path and one fake upstream."""
from __future__ import annotations

import gzip
import http.server
import importlib.util
import json
import sys
import threading
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / "bin" / "orama-system" / "skills"
          / "cline-wandb" / "scripts" / "launch_cline_wandb.py")
_spec = importlib.util.spec_from_file_location("launch_cline_wandb", SCRIPT)
launcher = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = launcher
_spec.loader.exec_module(launcher)

WAIT_S = 5.0


class _UpstreamHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args: object) -> None:
        pass

    def _send(self, status: int, body: bytes, declared: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Length", str(len(body) if declared is None else declared))
        self.end_headers()
        self.wfile.write(body)

    def _send_reply(self, body: bytes) -> None:
        """Send a 2xx chat reply, gzip-encoded or labelled with an encoding when the mode calls for it."""
        mode = self.server.mode
        permitted = "gzip" in self.headers.get("Accept-Encoding", "")
        encoding = None
        if mode == "gzip-anyway" or (mode == "gzip-if-permitted" and permitted):
            # Level 0 stores the plaintext inside the gzip stream, where a parser that ignored the
            # encoding could still read the usage report.
            body, encoding = gzip.compress(body, compresslevel=self.server.gzip_level), "gzip"
        elif mode == "labelled-identity":
            encoding = "identity"
        self.send_response(200)
        if encoding:
            self.send_header("Content-Encoding", encoding)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        srv = self.server
        srv.hits.append({"path": self.path, "body": None, "auth": self.headers.get("Authorization"),
                         "headers": {k.lower(): v for k, v in self.headers.items()}})
        if srv.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", f"{srv.redirect_to}/v1/redirected")  # fixed path, never request data
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Connection", "X-Resp-Hop")
        self.send_header("X-Resp-Hop", "leak")
        self.send_header("X-Kept", "yes")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(size) or b"{}")
        srv = self.server
        srv.hits.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization"),
                         "headers": {k.lower(): v for k, v in self.headers.items()},
                         "accept_encoding": self.headers.get_all("Accept-Encoding")})
        srv.arrived.set()
        if srv.arrival_file is not None:
            srv.arrival_file.write_text("arrived")
        srv.release.wait(WAIT_S * 2)
        if srv.mode == "drop_connection":
            self.close_connection = True
        elif srv.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", f"{srv.redirect_to}/v1/redirected")  # fixed path, never request data
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif srv.mode == "truncated-500":
            self._send(500, b"short", declared=500)
        elif srv.mode == "truncated-400":
            self._send(400, b"short", declared=500)
        elif srv.mode == "truncated-200":
            ok = json.dumps({"choices": [], "usage": {"completion_tokens": 1}}).encode()
            self._send(200, ok, declared=len(ok) + 100)
        elif srv.mode == "sse-malformed-usage" and body.get("stream"):
            self._send(200, b'data: {"usage": {"completion_tokens": 0}}\n\n'
                            b'data: {"usage": {"completion_tokens": "bad"}}\n\ndata: [DONE]\n\n')
        elif srv.mode == "huge":
            self._send(200, b"x" * 5000)
        elif srv.status != 200:
            self._send(srv.status, b'{"error":"upstream"}')
        elif body.get("stream"):
            chunks = b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
            if body.get("stream_options", {}).get("include_usage"):
                chunks += b'data: {"usage":{"completion_tokens": %d}}\n\n' % srv.tokens
            self._send_reply(chunks + b"data: [DONE]\n\n")
        else:
            payload = {"choices": []} if srv.mode == "nousage" else {"choices": [], "usage": {"completion_tokens": srv.tokens}}
            self._send_reply(json.dumps(payload).encode())
            srv.responded.append(srv.mode)


class Upstream(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__((launcher.LOOPBACK_HOST, 0), _UpstreamHandler)
        self.hits: list[dict] = []
        self.mode, self.tokens, self.status = "ok", 5, 200
        self.release, self.arrived = threading.Event(), threading.Event()
        self.arrival_file: Path | None = None
        self.redirect_to = ""
        self.responded: list[str] = []
        self.gzip_level = 9
        self.release.set()
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def base_url(self) -> str:
        return f"http://{launcher.LOOPBACK_HOST}:{self.server_address[1]}/v1"
