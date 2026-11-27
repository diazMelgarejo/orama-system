"""How the W&B Cline launcher runs its child process: argv, stdin, fail-closed stop and signals.

The installed `cline` is a wrapper that starts the real program as its own child, so every fake here is
a wrapper plus a grandchild. The launcher runs in a subprocess so a test can hold its stdin open or
signal it without touching the test runner.

The last test drives the real `cline` binary against a fake upstream. It is opt-in
(`ORAMA_REAL_CLINE_SMOKE=1`) because Cline leaves a detached hub daemon behind that the test must stop.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path
from typing import Any, Iterator, cast

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")]

SCRIPT = (Path(__file__).resolve().parents[1] / "bin" / "orama-system" / "skills"
          / "cline-wandb" / "scripts" / "launch_cline_wandb.py")
_spec = importlib.util.spec_from_file_location("launch_cline_wandb_for_process_tests", SCRIPT)
L = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = L
_spec.loader.exec_module(L)
KEYVAR = L.KEYVAR
PROVIDER_KEY = "provider-key-for-process-tests"
WAIT_S = 20.0
DRIVER = textwrap.dedent("""\
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("launcher_under_test", sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.BASE_URL = sys.argv[2]
    sys.exit(module.main(sys.argv[3:]))
    """)


class _FakeUpstream(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__((L.LOOPBACK_HOST, 0), _ChatHandler)
        self.hits: list[dict[str, str]] = []
        self.with_usage = True
        self.base_url = f"http://{L.LOOPBACK_HOST}:{self.server_address[1]}/v1"


class _ChatHandler(http.server.BaseHTTPRequestHandler):
    """A minimal OpenAI-compatible chat endpoint; `server.with_usage` decides whether usage is sent."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - base class signature
        return

    def do_POST(self) -> None:  # noqa: N802
        server = cast(_FakeUpstream, self.server)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        server.hits.append({"path": self.path, "auth": self.headers.get("Authorization", "")})
        usage = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3} if server.with_usage else None
        base = {"id": "chatcmpl-test", "created": 0, "model": body.get("model", "m")}
        if body.get("stream"):
            chunks = [
                {**base, "object": "chat.completion.chunk",
                 "choices": [{"index": 0, "delta": {"role": "assistant", "content": "OK"}, "finish_reason": None}]},
                {**base, "object": "chat.completion.chunk",
                 "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            ]
            if usage:
                chunks.append({**base, "object": "chat.completion.chunk", "choices": [], "usage": usage})
            payload = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"
            content_type = "text/event-stream"
        else:
            reply = {**base, "object": "chat.completion",
                     "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"},
                                  "finish_reason": "stop"}]}
            if usage:
                reply["usage"] = usage
            payload = json.dumps(reply)
            content_type = "application/json"
        data = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def upstream() -> Iterator[_FakeUpstream]:
    server = _FakeUpstream()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _gone_within(pid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while _alive(pid):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.05)
    return True


def _wait_for(path: Path) -> str:
    deadline = time.monotonic() + WAIT_S
    while not (path.exists() and path.read_text()):
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.05)
    return path.read_text()


@pytest.fixture
def fake_cline(tmp_path: Path) -> Iterator[Path]:
    """Directory holding a fake `cline` wrapper; any grandchild it recorded is killed afterwards."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    yield bindir
    pidfile = tmp_path / "grandchild.pid"
    if pidfile.exists() and pidfile.read_text() and _alive(int(pidfile.read_text())):
        os.kill(int(pidfile.read_text()), signal.SIGKILL)


def _install(bindir: Path, body: str) -> None:
    script = bindir / "cline"
    script.write_text(f"#!{sys.executable}\n{textwrap.dedent(body)}")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


def _wrapper_with_grandchild(tmp_path: Path, grandchild: str) -> str:
    """Source for a wrapper that starts `grandchild`, records its pid and waits for it, as `cline` does."""
    source = tmp_path / "grandchild.py"
    source.write_text(textwrap.dedent(grandchild))
    return f"""
    import subprocess, sys
    child = subprocess.Popen([sys.executable, {str(source)!r}, *sys.argv[1:]])
    open({str(tmp_path / "grandchild.pid")!r}, "w").write(str(child.pid))
    sys.exit(child.wait())
    """


def _launch(tmp_path: Path, bindir: Path, base_url: str, **popen: Any) -> subprocess.Popen:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "TMPDIR": str(tmp_path), "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
           KEYVAR: PROVIDER_KEY}
    argv = [sys.executable, "-c", DRIVER, str(SCRIPT), base_url,
            "--max-requests", "3", "--max-total-output", "100", "--", "task"]
    # Output goes to files: an orphaned grandchild would hold a pipe open and hide that it is still alive.
    with open(tmp_path / "launcher.out", "w") as out, open(tmp_path / "launcher.err", "w") as err:
        return subprocess.Popen(argv, cwd=tmp_path, env=env, stdout=out, stderr=err, start_new_session=True,
                                **popen)


def _finish(proc: subprocess.Popen, tmp_path: Path) -> tuple[int, str]:
    try:
        proc.wait(timeout=WAIT_S)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        pytest.fail("the launcher did not exit")
    return proc.returncode, (tmp_path / "launcher.err").read_text()


def test_cline_sees_a_closed_stdin_even_when_the_callers_stdin_stays_open(
    tmp_path: Path, fake_cline: Path, upstream
) -> None:
    _install(fake_cline, f"""
    import sys
    open({str(tmp_path / "stdin.txt")!r}, "w").write("eof after %d bytes" % len(sys.stdin.read()))
    """)
    proc = _launch(tmp_path, fake_cline, upstream.base_url, stdin=subprocess.PIPE)
    rc, err = _finish(proc, tmp_path)
    proc.stdin.close()
    assert rc == 0, err
    assert (tmp_path / "stdin.txt").read_text() == "eof after 0 bytes"


@pytest.mark.parametrize("ignores_term", [False, True], ids=["exits-on-term", "ignores-term"])
def test_fail_closed_stop_ends_the_whole_cline_process_group(
    tmp_path: Path, fake_cline: Path, upstream, ignores_term: bool
) -> None:
    upstream.with_usage = False  # a response without usage is unaccounted, so the launcher fails closed
    _install(fake_cline, _wrapper_with_grandchild(tmp_path, f"""
    import http.client, json, os, signal, sys, time, urllib.parse
    if {ignores_term!r}:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    cfg = sys.argv[sys.argv.index("--config") + 1]
    settings = json.load(open(os.path.join(cfg, "data", "settings", "providers.json")))
    settings = settings["providers"]["openai-compatible"]["settings"]
    url = urllib.parse.urlsplit(settings["baseUrl"])
    time.sleep(0.5)
    conn = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    conn.request("POST", url.path + "/chat/completions", json.dumps({{"model": "m", "messages": []}}),
                 {{"Authorization": "Bearer " + settings["apiKey"], "Content-Type": "application/json"}})
    try:
        conn.getresponse().read()
    except OSError:
        pass
    time.sleep(60)
    """))
    rc, err = _finish(_launch(tmp_path, fake_cline, upstream.base_url, stdin=subprocess.DEVNULL), tmp_path)
    grandchild = int((tmp_path / "grandchild.pid").read_text())
    assert rc == 124, err
    assert _gone_within(grandchild, 1.0), "the real Cline process outlived the fail-closed launcher"


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP], ids=["int", "term", "hup"])
def test_a_signal_to_the_launcher_reaches_the_cline_process_group(
    tmp_path: Path, fake_cline: Path, upstream, signum: signal.Signals
) -> None:
    _install(fake_cline, _wrapper_with_grandchild(tmp_path, f"""
    import signal, sys, time
    def stop(number, frame):
        open({str(tmp_path / "signal.txt")!r}, "w").write(str(number))
        sys.exit(0)
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, stop)
    open({str(tmp_path / "ready.txt")!r}, "w").write("ready")
    time.sleep(60)
    """))
    proc = _launch(tmp_path, fake_cline, upstream.base_url, stdin=subprocess.DEVNULL)
    _wait_for(tmp_path / "ready.txt")
    grandchild = int((tmp_path / "grandchild.pid").read_text())
    os.kill(proc.pid, signum)  # the launcher only, as a supervisor would
    rc, err = _finish(proc, tmp_path)
    assert _wait_for(tmp_path / "signal.txt") == str(int(signum))
    assert rc == 128 + int(signum), err
    assert _gone_within(grandchild, 1.0)
    assert not list(tmp_path.glob("clinecfg-*")), "the throwaway config was left behind"


def _stubborn_cline_with_a_detached_tool(tmp_path: Path, trigger: str) -> str:
    """A Cline that ignores INT, TERM and HUP and runs its tool in a new session, as the real one does."""
    return _wrapper_with_grandchild(tmp_path, f"""
    import http.client, json, os, signal, subprocess, sys, time, urllib.parse
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, signal.SIG_IGN)
    tool = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    open({str(tmp_path / "tool.pid")!r}, "w").write(str(tool.pid))
    cfg = sys.argv[sys.argv.index("--config") + 1]
    settings = json.load(open(os.path.join(cfg, "data", "settings", "providers.json")))
    settings = settings["providers"]["openai-compatible"]["settings"]
    url = urllib.parse.urlsplit(settings["baseUrl"])
    if {trigger!r} == "breach":
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
        conn.request("POST", url.path + "/chat/completions", json.dumps({{"model": "m", "messages": []}}),
                     {{"Authorization": "Bearer " + settings["apiKey"], "Content-Type": "application/json"}})
        try:
            conn.getresponse().read()
        except OSError:
            pass
    open({str(tmp_path / "ready.txt")!r}, "w").write("ready")
    time.sleep(60)
    """)


@pytest.fixture
def detached_tool(tmp_path: Path) -> Iterator[Path]:
    """Path of the detached tool's pid file; the tool is killed afterwards if a test left it running."""
    pidfile = tmp_path / "tool.pid"
    yield pidfile
    if pidfile.exists() and pidfile.read_text() and _alive(int(pidfile.read_text())):
        os.kill(int(pidfile.read_text()), signal.SIGKILL)


def test_fail_closed_stop_also_ends_a_tool_that_runs_in_its_own_session(
    tmp_path: Path, fake_cline: Path, upstream, detached_tool: Path
) -> None:
    upstream.with_usage = False
    _install(fake_cline, _stubborn_cline_with_a_detached_tool(tmp_path, "breach"))
    rc, err = _finish(_launch(tmp_path, fake_cline, upstream.base_url, stdin=subprocess.DEVNULL), tmp_path)
    assert rc == 124, err
    assert _gone_within(int(detached_tool.read_text()), 1.0), "a Cline tool command outlived the stop"


def test_a_second_signal_kills_cline_and_its_detached_tool(
    tmp_path: Path, fake_cline: Path, upstream, detached_tool: Path
) -> None:
    _install(fake_cline, _stubborn_cline_with_a_detached_tool(tmp_path, "signal"))
    proc = _launch(tmp_path, fake_cline, upstream.base_url, stdin=subprocess.DEVNULL)
    _wait_for(tmp_path / "ready.txt")
    os.kill(proc.pid, signal.SIGTERM)
    time.sleep(0.5)
    os.kill(proc.pid, signal.SIGTERM)
    rc, err = _finish(proc, tmp_path)
    assert rc == 128 + int(signal.SIGTERM), err
    assert _gone_within(int((tmp_path / "grandchild.pid").read_text()), 1.0)
    assert _gone_within(int(detached_tool.read_text()), 1.0), "a Cline tool command outlived the stop"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind((L.LOOPBACK_HOST, 0))
        return sock.getsockname()[1]


def _stop_hub_daemons(port: int) -> None:
    """Stop only the detached hub daemon this test caused, identified by its private port."""
    listing = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True, check=True).stdout
    for line in listing.splitlines():
        pid, _, command = line.strip().partition(" ")
        if "--cline-hub-daemon" in command and f"--port {port}" in command:
            os.kill(int(pid), signal.SIGTERM)


@pytest.mark.skipif(os.environ.get("ORAMA_REAL_CLINE_SMOKE") != "1" or shutil.which("cline") is None,
                    reason="opt-in: set ORAMA_REAL_CLINE_SMOKE=1 with the real cline on PATH")
def test_real_cline_completes_one_turn_through_the_accounting_proxy(tmp_path: Path, upstream) -> None:
    port = _free_port()
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    env = {"HOME": str(home), "TMPDIR": str(tmp_path), "PATH": os.environ["PATH"], KEYVAR: PROVIDER_KEY,
           "CLINE_NO_AUTO_UPDATE": "1", "CLINE_TELEMETRY_DISABLED": "1", "CLINE_HUB_PORT": str(port)}
    argv = [sys.executable, "-c", DRIVER, str(SCRIPT), upstream.base_url,
            "--max-requests", "3", "--max-total-output", "1000", "--", "Reply with the single word OK"]
    try:
        done = subprocess.run(argv, cwd=work, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=90, check=False)
    finally:
        _stop_hub_daemons(port)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "OK" in done.stdout
    assert [h["auth"] for h in upstream.hits] == [f"Bearer {PROVIDER_KEY}"]
    assert PROVIDER_KEY not in done.stdout + done.stderr
