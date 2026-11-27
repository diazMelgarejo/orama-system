"""Bound enforcement of the W&B Cline launcher: the accounting proxy driven by stub `cline` clients."""
from __future__ import annotations

import json
import os
import stat
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Iterator

import pytest

from cline_wandb_fixtures import Upstream, launcher, part

pytestmark = pytest.mark.unit

FAKE_KEY = "wandb-test-key-0123456789"


@pytest.fixture
def fake_upstream() -> Iterator[tuple[Upstream, str]]:
    """A running fake upstream and its base URL."""
    server = Upstream()
    yield server, server.base_url
    server.release.set()
    server.shutdown()
    server.server_close()


def _make_stub_cline(bindir: Path, python_body: str) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    script = bindir / "cline"
    script.write_text(
        f"#!/usr/bin/env python3\n"
        f"import json, sys, urllib.request\n"
        f"{python_body}\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def test_cumulative_output_limit_terminates_child_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """When child output tokens exceed max_total_output, the launcher terminates child fail-closed (exit 124)."""
    server, upstream_url = fake_upstream
    server.tokens = 100
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
    headers=headers,
    method="POST",
)
try:
    urllib.request.urlopen(req)
except Exception:
    pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "50", "--", "task"])
    assert rc == 124, "child exceeding max_total_output must terminate fail-closed with exit code 124"
    out, err = capsys.readouterr()
    assert "max_total_output exceeded" in err


def test_cumulative_output_limit_sse_streaming_terminates_child_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """When streaming child output tokens exceed max_total_output, child terminates fail-closed (exit 124)."""
    server, upstream_url = fake_upstream
    server.tokens = 100
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test", "stream": True, "messages": []}).encode("utf-8"),
    headers=headers,
    method="POST",
)
try:
    urllib.request.urlopen(req)
except Exception:
    pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "50", "--", "task"])
    assert rc == 124, "streaming child exceeding max_total_output must terminate fail-closed with exit code 124"
    out, err = capsys.readouterr()
    assert "max_total_output exceeded" in err


def test_missing_usage_terminates_child_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """When upstream returns completions missing usage tokens, child terminates fail-closed (exit 124)."""
    server, upstream_url = fake_upstream
    server.mode = "nousage"
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
    headers=headers,
    method="POST",
)
try:
    urllib.request.urlopen(req)
except Exception:
    pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "50", "--", "task"])
    assert rc == 124, "missing usage must terminate fail-closed with exit code 124"
    out, err = capsys.readouterr()
    assert "unaccounted_dispatch" in err
    assert "max_total_output exceeded" not in err


def test_request_count_limit_terminates_child_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """When child request count exceeds max_requests, the launcher terminates child fail-closed (exit 124)."""
    server, upstream_url = fake_upstream
    server.tokens = 10
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

for i in range(2):
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except Exception:
        pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "1", "--max-total-output", "4096", "--", "task"])
    assert rc == 124, "child exceeding max_requests must terminate fail-closed with exit code 124"
    out, err = capsys.readouterr()
    assert "max_requests exceeded" in err


def test_within_budget_succeeds_and_ordinary_text_not_killed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """Child within bounds emits normal text ('turn 100', 'api_req_started') without false termination."""
    server, upstream_url = fake_upstream
    server.tokens = 10
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
    headers=headers,
    method="POST",
)
urllib.request.urlopen(req)
print("turn 100")
print("word1 word2")
print("api_req_started")
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "2", "--max-total-output", "50", "--", "task"])
    assert rc == 0
    out, err = capfd.readouterr()
    assert "turn 100" in out
    assert "word1 word2" in out
    assert "api_req_started" in out
    assert "ERROR" not in err


def test_query_string_cannot_bypass_accounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """A query string on /chat/completions (e.g. ?api-version=1) does not bypass accounting."""
    server, upstream_url = fake_upstream
    server.tokens = 10
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

for _ in range(2):
    req = urllib.request.Request(
        f"{base_url}/chat/completions?api-version=2024-02-01",
        data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except Exception:
        pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "1", "--max-total-output", "4096", "--", "task"])
    assert rc == 124
    out, err = capsys.readouterr()
    assert "max_requests exceeded" in err


def test_unsupported_post_route_refused_with_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_upstream: tuple[object, str],
) -> None:
    """Non-allowlisted POST routes (e.g. /responses, /completions) are refused fail-closed with 403."""
    server, upstream_url = fake_upstream
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
import urllib.error
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

for path in ("/responses", "/completions"):
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=b'{"test": 1}',
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
        sys.exit(1)
    except urllib.error.HTTPError as exc:
        if exc.code != 403:
            sys.exit(2)
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "4096", "--", "task"])
    assert rc == 0
    assert not server.hits


def test_post_breach_retry_rejected_with_429_without_forwarding(
    fake_upstream: tuple[object, str],
) -> None:
    """When a bound is already breached, subsequent /chat/completions calls receive 429 without being forwarded."""
    server, upstream_url = fake_upstream
    proxy = launcher.AccountingProxyServer(
        (launcher.LOOPBACK_HOST, 0),
        launcher.AccountingProxyHandler,
        max_requests=5,
        max_total_output=40,
        upstream_base_url=upstream_url,
        session_token="test-session-token",
        upstream_key="test-key",
    )
    t = threading.Thread(target=proxy.serve_forever, daemon=True)
    t.start()
    port = proxy.server_address[1]
    base_url = f"http://{launcher.LOOPBACK_HOST}:{port}/v1"
    try:
        with proxy.lock:
            proxy.boundary_error.append(launcher.BoundaryExceededError("max_total_output", 40, 50))
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer test-session-token"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 429
        assert not server.hits
    finally:
        proxy.shutdown()
        proxy.server_close()


def test_pre_forward_max_tokens_and_completion_tokens_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_upstream: tuple[object, str],
) -> None:
    """Proxy clamps forwarded max_tokens and max_completion_tokens to remaining budget."""
    server, upstream_url = fake_upstream
    server.tokens = 15
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

# First request asks for 100 max_tokens when total budget is 40. Upstream should see clamped to 40.
req1 = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test", "max_tokens": 100, "max_completion_tokens": 90}).encode("utf-8"),
    headers=headers,
    method="POST",
)
urllib.request.urlopen(req1)

# Second request asks for 100 when remaining is 40 - 15 = 25. Upstream should see clamped to 25.
req2 = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test", "max_tokens": 100, "max_completion_tokens": 80}).encode("utf-8"),
    headers=headers,
    method="POST",
)
urllib.request.urlopen(req2)
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "40", "--", "task"])
    assert rc == 0
    reqs = server.hits
    assert len(reqs) == 2
    assert reqs[0]["body"]["max_tokens"] == 40
    assert reqs[0]["body"]["max_completion_tokens"] == 40
    assert reqs[1]["body"]["max_tokens"] == 25
    assert reqs[1]["body"]["max_completion_tokens"] == 25


def test_upstream_transport_error_terminates_child_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """Upstream 504/502 transport error marks boundary exceeded and terminates fail-closed with 124."""
    server, upstream_url = fake_upstream
    server.mode = "drop_connection"
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test"}).encode("utf-8"),
    headers=headers,
    method="POST",
)
try:
    urllib.request.urlopen(req)
except Exception:
    pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "4096", "--", "task"])
    assert rc == 124
    out, err = capsys.readouterr()
    assert ("upstream_transport" in err or "unaccounted_dispatch" in err)


def test_accept_to_dispatch_race_closed_by_stop_and_drain(fake_upstream: tuple[object, str]) -> None:
    """stop_and_drain waits for request admitted in process_request even if worker thread was delayed."""
    server, upstream_url = fake_upstream
    server.tokens = 50

    worker_started = threading.Event()
    release_worker = threading.Event()

    class PausingProxyServer(launcher.AccountingProxyServer):
        def process_request_thread(self, request, client_address) -> None:
            worker_started.set()
            release_worker.wait(timeout=2.0)
            super().process_request_thread(request, client_address)

    drain_waiting = threading.Event()

    proxy = PausingProxyServer(
        (launcher.LOOPBACK_HOST, 0),
        launcher.AccountingProxyHandler,
        max_requests=5,
        max_total_output=40,
        upstream_base_url=upstream_url,
        session_token="test-session-token",
        upstream_key="test-key",
    )
    # Exercise the production stop_and_drain(): only observe the condition wait it performs, then delegate.
    real_wait_for = proxy._inflight_cond.wait_for

    inflight_at_wait: list[int] = []

    def signalling_wait_for(predicate: Callable[[], bool], timeout: float | None = None) -> bool:
        inflight_at_wait.append(proxy._inflight_requests)
        drain_waiting.set()
        return real_wait_for(predicate, timeout)

    proxy._inflight_cond.wait_for = signalling_wait_for  # type: ignore[method-assign]
    t = threading.Thread(target=proxy.serve_forever, daemon=True)
    t.start()
    port = proxy.server_address[1]
    base_url = f"http://{launcher.LOOPBACK_HOST}:{port}/v1"

    try:
        def client_req() -> None:
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=json.dumps({"model": "test", "messages": []}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer test-session-token"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req)
            except Exception:
                pass

        client_thread = threading.Thread(target=client_req, daemon=True)
        client_thread.start()

        # Wait until worker has reached process_request_thread (so request was admitted in process_request)
        assert worker_started.wait(timeout=2.0)

        # In child process simulation: child exited, launcher calls stop_and_drain in a thread
        drain_result: list[bool] = []

        def do_drain() -> None:
            drain_result.append(proxy.stop_and_drain(timeout_s=3.0))

        drain_thread = threading.Thread(target=do_drain, daemon=True)
        drain_thread.start()

        # Only after the drain reaches its condition wait, release the worker so it finishes processing and accounting
        assert drain_waiting.wait(timeout=2.0)
        assert drain_thread.is_alive() and drain_result == [], "drain returned before the admitted worker finished"
        release_worker.set()
        drain_thread.join(timeout=3.0)

        assert drain_result == [True]
        assert inflight_at_wait == [1], "the production condition wait must start with the worker in flight"
        with proxy.lock:
            assert len(proxy.boundary_error) == 1
            assert proxy.boundary_error[0].bound == "max_total_output"
    finally:
        release_worker.set()
        proxy.shutdown()
        proxy.server_close()


def test_upstream_httperror_read_timeout_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """When upstream returns HTTPError and reading the error body times out, proxy fails closed with 124."""
    import email.message
    import urllib.error

    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps({"model": "test"}).encode("utf-8"),
    headers=headers,
    method="POST",
)
try:
    urllib.request.urlopen(req)
except Exception:
    pass
sys.exit(0)
""",
    )
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)

    class MockErrorFile:
        def read(self, *args: object, **kwargs: object) -> bytes:
            raise TimeoutError("simulated HTTPError.read timeout")

        def close(self) -> None:
            pass

    opened: list[str] = []

    class MockOpener:
        def open(self, req: urllib.request.Request, timeout: float | None = None) -> object:
            opened.append(req.full_url)
            # Any non-2xx is unaccounted; if the body read were skipped the 400 would be relayed
            # (exit 0). Only the failing body read can turn it into an unaccounted dispatch (exit 124).
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=400,
                msg="Bad Request",
                hdrs=email.message.Message(),
                fp=MockErrorFile(),  # type: ignore[arg-type]
            )

    monkeypatch.setattr(part("upstream"), "_UPSTREAM_OPENER", MockOpener())
    # `.invalid` never resolves: were the opener patch lost, no request could reach a provider.
    monkeypatch.setattr(launcher, "BASE_URL", "https://upstream.invalid/v1")

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "4096", "--", "task"])
    assert opened == ["https://upstream.invalid/v1/chat/completions"], "the opener patch did not apply"
    assert rc == 124
    out, err = capsys.readouterr()
    assert "unaccounted_dispatch" in err



def test_sse_null_usage_before_a_valid_terminal_report_is_accepted() -> None:
    body = (b'data: {"usage": null}\n\ndata: {"choices": []}\n\n'
            b'data: {"usage": {"completion_tokens": 7}}\n\ndata: [DONE]\n\n')
    assert launcher.extract_sse_completion_tokens(body) == 7


@pytest.mark.parametrize("terminal", [
    '{"usage": {"completion_tokens": "bad"}}',
    '{"usage": {"completion_tokens": -1}}',
    '{"usage": {"completion_tokens": true}}',
    '{"usage": {}}',
    '{"usage": "garbage"}',
    '{"usage": {"completion_tokens": 3',
])
def test_sse_malformed_terminal_usage_never_falls_back_to_an_earlier_zero(terminal: str) -> None:
    body = f'data: {{"usage": {{"completion_tokens": 0}}}}\n\ndata: {terminal}\n\ndata: [DONE]\n\n'.encode()
    assert launcher.extract_sse_completion_tokens(body) is None


def test_hop_by_hop_names_include_connection_nominated_fields() -> None:
    import email.message

    headers = email.message.Message()
    headers["Connection"] = "X-Hop-Only, keep-alive"
    headers["Connection"] = "X-Second"
    names = launcher.hop_by_hop_names(headers, "host")
    assert {"x-hop-only", "x-second", "keep-alive", "transfer-encoding", "upgrade", "host"} <= names
