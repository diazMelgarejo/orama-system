"""Lifecycle and spend-accounting tests for the Cline W&B accounting proxy.

Every test synchronizes on events (arrival, drain-wait, release), never on sleeps. Loopback addresses
come from the launcher's LOOPBACK_HOST so the private-literal hygiene hook stays satisfied.
"""
from __future__ import annotations

import http.client
import http.server
import importlib.util
import json
import os
import stat
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).resolve().parents[1] / "bin" / "orama-system" / "skills"
          / "cline-wandb" / "scripts" / "launch_cline_wandb.py")
_spec = importlib.util.spec_from_file_location("launch_cline_wandb_lifecycle", SCRIPT)
L = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = L
_spec.loader.exec_module(L)

TOKEN = "session-token-for-tests"
PROVIDER_KEY = "provider-key-for-tests"
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

    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(size) or b"{}")
        srv = self.server
        srv.hits.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization")})
        srv.arrived.set()
        if srv.arrival_file is not None:
            srv.arrival_file.write_text("arrived")
        srv.release.wait(WAIT_S * 2)
        if srv.mode == "truncated-500":
            self._send(500, b"short", declared=500)
        elif srv.mode == "huge":
            self._send(200, b"x" * 5000)
        elif srv.status != 200:
            self._send(srv.status, b'{"error":"upstream"}')
        elif body.get("stream"):
            chunks = b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
            if body.get("stream_options", {}).get("include_usage"):
                chunks += b'data: {"usage":{"completion_tokens": %d}}\n\n' % srv.tokens
            self._send(200, chunks + b"data: [DONE]\n\n")
        else:
            payload = {"choices": []} if srv.mode == "nousage" else {"choices": [], "usage": {"completion_tokens": srv.tokens}}
            self._send(200, json.dumps(payload).encode())


class Upstream(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__((L.LOOPBACK_HOST, 0), _UpstreamHandler)
        self.hits: list[dict] = []
        self.mode, self.tokens, self.status = "ok", 5, 200
        self.release, self.arrived = threading.Event(), threading.Event()
        self.arrival_file: Path | None = None
        self.release.set()
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def base_url(self) -> str:
        return f"http://{L.LOOPBACK_HOST}:{self.server_address[1]}/v1"


class Rig:
    def __init__(self, *, max_requests: int = 5, max_out: int = 50, child: bool = True) -> None:
        self.up = Upstream()
        self.proxy = L.AccountingProxyServer(
            (L.LOOPBACK_HOST, 0), L.AccountingProxyHandler, max_requests, max_out,
            upstream_base_url=self.up.base_url, timeout_ms=3000, session_token=TOKEN, upstream_key=PROVIDER_KEY,
        )
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]) if child else None
        if self.child:
            self.proxy.set_child_proc(self.child)

    def post(self, path: str = "/v1/chat/completions", body: dict | None = None, token: str | None = TOKEN) -> tuple[int, bytes]:
        conn = http.client.HTTPConnection(L.LOOPBACK_HOST, self.proxy.server_address[1], timeout=10)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        conn.request("POST", path, json.dumps(body if body is not None else {"model": "m", "messages": []}), headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, data

    def child_exited(self) -> bool:
        try:
            self.child.wait(timeout=WAIT_S)
            return True
        except subprocess.TimeoutExpired:
            return False

    def breach_names(self) -> list[str]:
        return [e.bound for e in self.proxy.boundary_error]

    def close(self) -> None:
        if self.child and self.child.poll() is None:
            self.child.kill()
        self.up.release.set()
        self.up.shutdown()
        self.up.server_close()
        self.proxy.server_close()


@pytest.fixture
def rig():
    made: list[Rig] = []

    def make(**kw: object) -> Rig:
        made.append(Rig(**kw))
        return made[-1]

    yield make
    for item in made:
        item.close()


def test_unauthenticated_chat_is_refused_before_any_counter_changes(rig):
    r = rig()
    assert r.post(token=None)[0] == 401 and r.post(token="wrong")[0] == 401
    assert r.proxy.request_count == 0 and not r.up.hits and r.child.poll() is None


def test_chat_is_clamped_counted_and_uses_the_provider_key_upstream(rig):
    r = rig(max_out=50)
    status, _ = r.post(path="/v1/chat/completions?api-version=1", body={"model": "m", "messages": [], "max_tokens": 999})
    assert status == 200 and r.proxy.request_count == 1
    assert r.up.hits[0]["body"]["max_tokens"] == 50
    assert r.up.hits[0]["auth"] == f"Bearer {PROVIDER_KEY}" and r.proxy.cumulative_output_tokens == 5


def test_other_post_routes_are_refused_and_never_forwarded(rig):
    r = rig()
    assert r.post(path="/v1/responses")[0] == 403 and not r.up.hits


def test_streaming_gets_include_usage_and_sse_usage_is_accounted(rig):
    r = rig()
    assert r.post(body={"model": "m", "messages": [], "stream": True})[0] == 200
    assert r.up.hits[0]["body"]["stream_options"] == {"include_usage": True}
    assert r.proxy.cumulative_output_tokens == 5


def test_over_budget_response_breaches_terminates_child_and_blocks_retries(rig):
    r = rig(max_out=10)
    r.up.tokens = 100
    assert r.post()[0] == 429 and r.breach_names() == ["max_total_output"] and r.child_exited()
    forwarded = len(r.up.hits)
    assert r.post()[0] == 429 and len(r.up.hits) == forwarded


def test_a_recorded_breach_alone_blocks_forwarding_even_with_budget_left(rig):
    r = rig(child=False)
    r.proxy.boundary_error.append(L.BoundaryExceededError("max_requests", 5, 6))
    assert r.post()[0] == 429 and not r.up.hits and r.proxy.request_count == 0


def test_possibly_billed_statuses_are_debited_in_full_and_fail_closed(rig):
    r = rig(max_out=50)
    r.up.status = 500
    assert r.post()[0] == 500
    assert r.breach_names() == ["unaccounted_dispatch"] and r.proxy.cumulative_output_tokens == 50 and r.child_exited()


def test_definitive_rejection_is_relayed_without_breach_or_debit(rig):
    r = rig(max_out=50)
    r.up.status = 400
    assert r.post()[0] == 400
    assert not r.proxy.boundary_error and r.proxy.cumulative_output_tokens == 0 and r.child.poll() is None


@pytest.mark.parametrize("mode", ["truncated-500", "huge"])
def test_unreadable_or_oversize_upstream_bodies_fail_closed(rig, monkeypatch, mode):
    monkeypatch.setattr(L, "MAX_RESPONSE_BYTES", 1000)
    r = rig()
    r.up.mode = mode
    r.post()
    assert r.breach_names() == ["unaccounted_dispatch"]


def test_worker_queued_behind_the_gate_cannot_dispatch_after_the_drain_deadline(rig):
    r = rig(max_requests=9, max_out=500, child=False)
    r.up.release.clear()
    results: dict[str, int] = {}
    first = threading.Thread(target=lambda: results.setdefault("A", r.post()[0]))
    first.start()
    assert r.up.arrived.wait(WAIT_S)
    second = threading.Thread(target=lambda: results.setdefault("B", r.post()[0]))
    second.start()
    deadline = time.monotonic() + WAIT_S
    while r.proxy._inflight_requests < 2 and time.monotonic() < deadline:
        time.sleep(0.005)
    assert r.proxy._inflight_requests == 2
    assert r.proxy.stop_and_drain(timeout_s=0.5) is False and r.proxy.phase == L.PHASE_CLOSED
    r.up.release.set()
    first.join(WAIT_S)
    second.join(WAIT_S)
    assert results == {"A": 200, "B": 503} and len(r.up.hits) == 1


def test_drain_blocks_on_admitted_work_then_reports_the_unaccounted_response(rig):
    r = rig(child=False)
    r.up.release.clear()
    r.up.mode = "nousage"
    status: dict[str, int] = {}
    worker = threading.Thread(target=lambda: status.setdefault("s", r.post()[0]))
    worker.start()
    assert r.up.arrived.wait(WAIT_S)
    at_wait, real_wait_for = threading.Event(), r.proxy._inflight_cond.wait_for

    def signalling_wait_for(predicate, timeout=None):
        at_wait.set()
        return real_wait_for(predicate, timeout)

    r.proxy._inflight_cond.wait_for = signalling_wait_for
    outcome: dict[str, bool] = {}
    drain = threading.Thread(target=lambda: outcome.setdefault("drained", r.proxy.stop_and_drain(timeout_s=WAIT_S * 2)))
    drain.start()
    assert at_wait.wait(WAIT_S) and drain.is_alive()
    r.up.release.set()
    drain.join(WAIT_S * 2)
    worker.join(WAIT_S)
    assert outcome["drained"] is True and status["s"] == 502 and r.breach_names() == ["unaccounted_dispatch"]


def _install_fake_cline(tmp_path: Path, monkeypatch) -> Path:
    marker = tmp_path / "seen.json"
    script = tmp_path / "cline"
    script.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import http.client, json, os, sys, urllib.parse
        argv = sys.argv
        cfg = argv[argv.index("--config") + 1]
        settings = json.load(open(os.path.join(cfg, "data", "settings", "providers.json")))["providers"]["openai-compatible"]["settings"]
        url = urllib.parse.urlsplit(settings["baseUrl"])
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
        conn.request("POST", url.path + "/chat/completions", json.dumps({{"model": "m", "messages": []}}),
                     {{"Authorization": "Bearer " + settings["apiKey"], "Content-Type": "application/json"}})
        resp = conn.getresponse(); resp.read()
        open({str(marker)!r}, "w").write(json.dumps({{"apiKey": settings["apiKey"], "status": resp.status, "cfg": cfg}}))
        """))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(L.KEYVAR, PROVIDER_KEY)
    return marker


def test_main_hands_cline_the_session_token_never_the_provider_key(tmp_path, monkeypatch):
    marker = _install_fake_cline(tmp_path, monkeypatch)
    up = Upstream()
    monkeypatch.setattr(L, "BASE_URL", up.base_url)
    try:
        rc = L.main(["--max-requests", "2", "--max-total-output", "50", "--", "task"])
    finally:
        up.shutdown()
        up.server_close()
    seen = json.loads(marker.read_text())
    assert rc == 0 and seen["status"] == 200 and seen["apiKey"] != PROVIDER_KEY
    assert up.hits[0]["auth"] == f"Bearer {PROVIDER_KEY}" and not os.path.exists(seen["cfg"])


def test_main_exits_124_when_the_child_succeeds_but_a_response_had_no_usage(tmp_path, monkeypatch):
    _install_fake_cline(tmp_path, monkeypatch)
    up = Upstream()
    up.mode = "nousage"
    monkeypatch.setattr(L, "BASE_URL", up.base_url)
    try:
        assert L.main(["--max-requests", "2", "--max-total-output", "50", "--", "task"]) == 124
    finally:
        up.shutdown()
        up.server_close()


def test_main_waits_for_an_inflight_request_after_the_child_has_exited(tmp_path, monkeypatch):
    """The child exits 0 while its request is still held upstream; only the drain can catch the breach."""
    arrival = tmp_path / "arrived"
    cline = tmp_path / "cline"
    cline.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import http.client, json, os, sys, threading, time, urllib.parse
        argv = sys.argv
        cfg = argv[argv.index("--config") + 1]
        s = json.load(open(os.path.join(cfg, "data", "settings", "providers.json")))["providers"]["openai-compatible"]["settings"]
        url = urllib.parse.urlsplit(s["baseUrl"])
        def send():
            conn = http.client.HTTPConnection(url.hostname, url.port, timeout=30)
            conn.request("POST", url.path + "/chat/completions", json.dumps({{"model": "m", "messages": []}}),
                         {{"Authorization": "Bearer " + s["apiKey"], "Content-Type": "application/json"}})
            conn.getresponse().read()
        threading.Thread(target=send, daemon=True).start()
        deadline = time.monotonic() + 10
        while not os.path.exists({str(arrival)!r}) and time.monotonic() < deadline:
            time.sleep(0.005)
        os._exit(0)
        """))
    cline.chmod(cline.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(L.KEYVAR, PROVIDER_KEY)
    up = Upstream()
    up.mode, up.arrival_file = "nousage", arrival
    up.release.clear()
    monkeypatch.setattr(L, "BASE_URL", up.base_url)
    at_wait = threading.Event()
    real_stop_and_drain = L.AccountingProxyServer.stop_and_drain

    def observed_stop_and_drain(self, timeout_s: float = 5.0) -> bool:
        real_wait_for = self._inflight_cond.wait_for

        def signalling_wait_for(predicate, timeout=None):
            at_wait.set()
            return real_wait_for(predicate, timeout)

        self._inflight_cond.wait_for = signalling_wait_for
        return real_stop_and_drain(self, timeout_s)

    monkeypatch.setattr(L.AccountingProxyServer, "stop_and_drain", observed_stop_and_drain)
    releaser = threading.Thread(target=lambda: (at_wait.wait(WAIT_S), up.release.set()))
    releaser.start()
    try:
        rc = L.main(["--max-requests", "2", "--max-total-output", "50", "--", "task"])
    finally:
        up.release.set()
        releaser.join(WAIT_S)
        up.shutdown()
        up.server_close()
    assert rc == 124
