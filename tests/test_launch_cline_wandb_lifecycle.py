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
from typing import Any, Callable, Iterator

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

    def do_GET(self) -> None:
        srv = self.server
        srv.hits.append({"path": self.path, "body": None, "auth": self.headers.get("Authorization"),
                         "headers": {k.lower(): v for k, v in self.headers.items()}})
        if srv.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", f"{srv.redirect_to}{self.path}")
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
                         "headers": {k.lower(): v for k, v in self.headers.items()}})
        srv.arrived.set()
        if srv.arrival_file is not None:
            srv.arrival_file.write_text("arrived")
        srv.release.wait(WAIT_S * 2)
        if srv.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", f"{srv.redirect_to}{self.path}")
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
        self.redirect_to = ""
        self.release.set()
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def base_url(self) -> str:
        return f"http://{L.LOOPBACK_HOST}:{self.server_address[1]}/v1"


class Rig:
    def __init__(self, *, max_requests: int = 5, max_out: int = 50, child: bool = True,
                 handler: type[L.AccountingProxyHandler] = L.AccountingProxyHandler) -> None:
        self.up = Upstream()
        self.proxy = L.AccountingProxyServer(
            (L.LOOPBACK_HOST, 0), handler, max_requests, max_out,
            upstream_base_url=self.up.base_url, timeout_ms=3000, session_token=TOKEN, upstream_key=PROVIDER_KEY,
        )
        self.serving = threading.Thread(target=self.proxy.serve_forever, daemon=True)
        self.serving.start()
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

    def get(self, path: str = "/v1/models", headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection(L.LOOPBACK_HOST, self.proxy.server_address[1], timeout=10)
        conn.request("GET", path, headers={"Authorization": f"Bearer {TOKEN}", **(headers or {})})
        resp = conn.getresponse()
        data = resp.read()
        got = {k.lower(): v for k, v in resp.getheaders()}
        conn.close()
        return resp.status, got, data

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
        if self.serving.is_alive():
            self.proxy.shutdown()
        self.serving.join(WAIT_S)
        self.proxy.server_close()


RigFactory = Callable[..., Rig]


@pytest.fixture
def rig() -> Iterator[RigFactory]:
    made: list[Rig] = []

    def make(**kw: Any) -> Rig:
        made.append(Rig(**kw))
        return made[-1]

    yield make
    for item in made:
        item.close()


def test_unauthenticated_chat_is_refused_before_any_counter_changes(rig: RigFactory) -> None:
    r = rig()
    assert r.post(token=None)[0] == 401 and r.post(token="wrong")[0] == 401
    assert r.proxy.request_count == 0 and not r.up.hits and r.child.poll() is None


def test_chat_is_clamped_counted_and_uses_the_provider_key_upstream(rig: RigFactory) -> None:
    r = rig(max_out=50)
    status, _ = r.post(path="/v1/chat/completions?api-version=1", body={"model": "m", "messages": [], "max_tokens": 999})
    assert status == 200 and r.proxy.request_count == 1
    assert r.up.hits[0]["body"]["max_tokens"] == 50
    assert r.up.hits[0]["auth"] == f"Bearer {PROVIDER_KEY}" and r.proxy.cumulative_output_tokens == 5


def test_other_post_routes_are_refused_and_never_forwarded(rig: RigFactory) -> None:
    r = rig()
    assert r.post(path="/v1/responses")[0] == 403 and not r.up.hits


def test_streaming_gets_include_usage_and_sse_usage_is_accounted(rig: RigFactory) -> None:
    r = rig()
    assert r.post(body={"model": "m", "messages": [], "stream": True})[0] == 200
    assert r.up.hits[0]["body"]["stream_options"] == {"include_usage": True}
    assert r.proxy.cumulative_output_tokens == 5


def test_over_budget_response_breaches_terminates_child_and_blocks_retries(rig: RigFactory) -> None:
    r = rig(max_out=10)
    r.up.tokens = 100
    assert r.post()[0] == 429 and r.breach_names() == ["max_total_output"] and r.child_exited()
    forwarded = len(r.up.hits)
    assert r.post()[0] == 429 and len(r.up.hits) == forwarded


def test_a_recorded_breach_alone_blocks_forwarding_even_with_budget_left(rig: RigFactory) -> None:
    r = rig(child=False)
    r.proxy.boundary_error.append(L.BoundaryExceededError("max_requests", 5, 6))
    assert r.post()[0] == 429 and not r.up.hits and r.proxy.request_count == 0


def test_possibly_billed_statuses_are_debited_in_full_and_fail_closed(rig: RigFactory) -> None:
    r = rig(max_out=50)
    r.up.status = 500
    assert r.post()[0] == 500
    assert r.breach_names() == ["unaccounted_dispatch"] and r.proxy.cumulative_output_tokens == 50 and r.child_exited()


def test_definitive_rejection_is_relayed_without_breach_or_debit(rig: RigFactory) -> None:
    r = rig(max_out=50)
    r.up.status = 400
    assert r.post()[0] == 400
    assert not r.proxy.boundary_error and r.proxy.cumulative_output_tokens == 0 and r.child.poll() is None


@pytest.mark.parametrize("mode", ["truncated-500", "huge"])
def test_unreadable_or_oversize_upstream_bodies_fail_closed(rig: RigFactory, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    monkeypatch.setattr(L, "MAX_RESPONSE_BYTES", 1000)
    r = rig()
    r.up.mode = mode
    r.post()
    assert r.breach_names() == ["unaccounted_dispatch"]


def test_worker_queued_behind_the_gate_cannot_dispatch_after_the_drain_deadline(rig: RigFactory) -> None:
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


def test_drain_blocks_on_admitted_work_then_reports_the_unaccounted_response(rig: RigFactory) -> None:
    r = rig(child=False)
    r.up.release.clear()
    r.up.mode = "nousage"
    status: dict[str, int] = {}
    worker = threading.Thread(target=lambda: status.setdefault("s", r.post()[0]))
    worker.start()
    assert r.up.arrived.wait(WAIT_S)
    at_wait, real_wait_for = threading.Event(), r.proxy._inflight_cond.wait_for

    def signalling_wait_for(predicate: Callable[[], bool], timeout: float | None = None) -> bool:
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


def _install_fake_cline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
        open({str(marker)!r}, "w").write(json.dumps({{"apiKey": settings["apiKey"], "status": resp.status, "cfg": cfg,
                                                      "key_in_env": {L.KEYVAR!r} in os.environ,
                                                      "key_in_env_values": {PROVIDER_KEY!r} in os.environ.values()}}))
        """))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(L.KEYVAR, PROVIDER_KEY)
    return marker


def test_main_hands_cline_the_session_token_never_the_provider_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert seen["key_in_env"] is False and seen["key_in_env_values"] is False
    assert up.hits[0]["auth"] == f"Bearer {PROVIDER_KEY}" and not os.path.exists(seen["cfg"])


def test_main_exits_124_when_a_response_has_no_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_cline(tmp_path, monkeypatch)
    up = Upstream()
    up.mode = "nousage"
    monkeypatch.setattr(L, "BASE_URL", up.base_url)
    try:
        assert L.main(["--max-requests", "2", "--max-total-output", "50", "--", "task"]) == 124
    finally:
        up.shutdown()
        up.server_close()


def test_main_waits_for_an_inflight_request_after_the_child_has_exited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
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

        def signalling_wait_for(predicate: Callable[[], bool], timeout: float | None = None) -> bool:
            at_wait.set()
            return real_wait_for(predicate, timeout)

        self._inflight_cond.wait_for = signalling_wait_for
        return real_stop_and_drain(self, timeout_s)

    monkeypatch.setattr(L.AccountingProxyServer, "stop_and_drain", observed_stop_and_drain)
    drain_reached: list[bool] = []

    def release_after_drain_wait() -> None:
        try:
            drain_reached.append(at_wait.wait(WAIT_S))
        finally:
            up.release.set()

    releaser = threading.Thread(target=release_after_drain_wait)
    releaser.start()
    try:
        rc = L.main(["--max-requests", "2", "--max-total-output", "50", "--", "task"])
    finally:
        up.release.set()
        releaser.join(WAIT_S)
        up.shutdown()
        up.server_close()
    assert drain_reached == [True], "the drain never reached its condition wait before the upstream was released"
    assert arrival.exists() and len(up.hits) == 1
    assert rc == 124
    assert "unaccounted_dispatch" in capsys.readouterr().err


def test_chat_redirect_is_not_followed_and_the_provider_key_never_reaches_another_origin(rig: RigFactory) -> None:
    r = rig(max_out=50)
    other = Upstream()
    try:
        r.up.mode, r.up.redirect_to = "redirect", other.base_url.removesuffix("/v1")
        status, _ = r.post()
        assert status == 502 and not other.hits
        assert r.breach_names() == ["unaccounted_dispatch"] and r.proxy.cumulative_output_tokens == 50
        assert r.child_exited()
    finally:
        other.shutdown()
        other.server_close()


def test_non_chat_redirect_is_not_followed_or_relayed(rig: RigFactory) -> None:
    r = rig(child=False)
    other = Upstream()
    try:
        r.up.mode, r.up.redirect_to = "redirect", other.base_url.removesuffix("/v1")
        status, headers, _ = r.get()
        assert status == 502 and "location" not in headers and not other.hits
        assert len(r.up.hits) == 1 and not r.proxy.boundary_error
    finally:
        other.shutdown()
        other.server_close()


@pytest.mark.parametrize("mode", ["truncated-400", "truncated-200"])
def test_response_shorter_than_its_declared_length_fails_closed_with_spend_recorded(rig: RigFactory, mode: str) -> None:
    r = rig(max_out=50)
    r.up.mode = mode
    status, _ = r.post()
    assert status == 502, "a truncated body must not be relayed as a definitive rejection or an accounted success"
    assert r.breach_names() == ["unaccounted_dispatch"]
    assert r.proxy.cumulative_output_tokens == 50 and r.child_exited()


def test_complete_definitive_rejection_is_still_relayed_without_a_debit(rig: RigFactory) -> None:
    r = rig(max_out=50)
    r.up.status = 400
    assert r.post()[0] == 400 and r.proxy.cumulative_output_tokens == 0 and not r.proxy.boundary_error


def test_malformed_streamed_usage_fails_closed_and_debits_the_whole_reservation(rig: RigFactory) -> None:
    r = rig(max_out=50)
    r.up.mode = "sse-malformed-usage"
    status, _ = r.post(body={"model": "m", "messages": [], "stream": True})
    assert status == 502
    assert r.breach_names() == ["unaccounted_dispatch"]
    assert r.proxy.cumulative_output_tokens == 50 and r.child_exited()


def test_hop_by_hop_fields_are_stripped_on_both_legs(rig: RigFactory) -> None:
    r = rig(child=False)
    status, headers, _ = r.get(headers={"Connection": "X-Hop-Only", "X-Hop-Only": "1", "Keep-Alive": "timeout=5",
                                        "X-End-To-End": "kept"})
    sent = r.up.hits[0]["headers"]
    assert status == 200
    assert "x-hop-only" not in sent and "keep-alive" not in sent and sent["x-end-to-end"] == "kept"
    assert sent["authorization"] == f"Bearer {PROVIDER_KEY}"
    assert "x-resp-hop" not in headers and headers["x-kept"] == "yes"


class _PausingGetHandler(L.AccountingProxyHandler):
    entered = threading.Event()
    proceed = threading.Event()

    def _forward(self, body_bytes: bytes, *, chat_budget: int | None, is_streaming: bool) -> None:
        type(self).entered.set()
        type(self).proceed.wait(WAIT_S)
        super()._forward(body_bytes, chat_budget=chat_budget, is_streaming=is_streaming)


def test_admitted_non_chat_worker_cannot_dispatch_after_the_proxy_is_closed(rig: RigFactory) -> None:
    _PausingGetHandler.entered.clear()
    _PausingGetHandler.proceed.clear()
    r = rig(child=False, handler=_PausingGetHandler)
    result: dict[str, int] = {}
    worker = threading.Thread(target=lambda: result.setdefault("s", r.get()[0]))
    worker.start()
    try:
        assert _PausingGetHandler.entered.wait(WAIT_S)
        with r.proxy.lock:
            r.proxy._phase = L.PHASE_CLOSED
    finally:
        _PausingGetHandler.proceed.set()
        worker.join(WAIT_S)
    assert result == {"s": 503} and not r.up.hits
