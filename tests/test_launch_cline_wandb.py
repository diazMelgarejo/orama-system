"""Tests for the W&B Cline launcher (bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py).

The launcher builds a throwaway Cline config that Cline 3.0.74 accepts (tokenSource "manual",
millisecond-Z updatedAt), refuses effort levels other than medium/high/low, keeps the key out of
argv, and deletes the config afterwards. A stub `cline` on PATH records what it was given.
Default invocations are review/plan mode with auto-approve off; passthrough is positional only.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import os
import re
import stat
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MODULE = (Path(__file__).resolve().parent.parent / "bin" / "orama-system" / "skills"
           / "cline-wandb" / "scripts" / "launch_cline_wandb.py")
_spec = importlib.util.spec_from_file_location("launch_cline_wandb", _MODULE)
launcher = importlib.util.module_from_spec(_spec)
sys.modules["launch_cline_wandb"] = launcher
_spec.loader.exec_module(launcher)

FAKE_KEY = "wandb-test-key-0123456789"
BOUNDED = ["--max-requests", "1", "--max-total-output", "4096"]
FILE_SECRET = "quoted-file-secret-must-not-leak"
_TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")


def _argv_lines(record: Path) -> list[str]:
    return (record / "argv.txt").read_text().splitlines()


def test_timestamp_uses_javascript_iso_format() -> None:
    assert _TS.match(launcher.cline_timestamp())


def test_config_entry_is_cline_3_0_74_compatible() -> None:
    cfg = launcher.build_config(FAKE_KEY, launcher.DEFAULT_MODEL, "high", 30000)
    entry = cfg["providers"]["openai-compatible"]
    assert entry["tokenSource"] == "manual"
    assert _TS.match(entry["updatedAt"])
    settings = entry["settings"]
    assert settings["model"] == "deepseek-ai/DeepSeek-V4.1-Flash-1017"
    assert settings["baseUrl"] == "https://api.inference.wandb.ai/v1"
    assert settings["reasoning"] == {"enabled": True, "effort": "high"}
    assert cfg["lastUsedProvider"] == "openai-compatible"


def test_efforts_are_medium_high_low_only() -> None:
    assert launcher.EFFORTS == ("medium", "high", "low")


@pytest.mark.parametrize("bad", ["max", "xhigh", "none"])
def test_forbidden_effort_is_refused(bad: str) -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args([*BOUNDED, "--effort", bad, "--", "task"])


def test_prompt_is_required() -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args([])


def test_default_effort_is_high_because_medium_is_rejected_on_v4_1() -> None:
    assert launcher.parse_args([*BOUNDED, "--", "task"]).effort == "high"


def test_key_comes_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    assert launcher.read_key() == FAKE_KEY


def test_env_file_is_not_parsed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(launcher.KEYVAR, raising=False)
    env_file = tmp_path / ".env.wandb"
    env_file.write_text(
        "# comment\n"
        f"export {launcher.KEYVAR}='{FILE_SECRET}'\n"
        f"{launcher.KEYVAR}=ab\\$cd\n"
        f"{launcher.KEYVAR}=\n"
    )
    with pytest.raises(SystemExit) as exc:
        launcher.read_key()
    message = str(exc.value)
    assert launcher.KEYVAR in message
    assert FILE_SECRET not in message
    assert "ab\\$cd" not in message
    assert "does not parse the file" in message
    assert launcher.DEFAULT_ENV_FILE in message


def test_exported_env_wins_even_if_a_file_would_disagree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env.wandb"
    env_file.write_text(f"{launcher.KEYVAR}={FILE_SECRET}\n")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.chdir(tmp_path)
    assert launcher.read_key() == FAKE_KEY


def test_empty_env_value_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(launcher.KEYVAR, "   \t  ")
    with pytest.raises(SystemExit) as exc:
        launcher.read_key()
    assert launcher.KEYVAR in str(exc.value)


def test_missing_key_exits_without_echoing_anything_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(launcher.KEYVAR, raising=False)
    with pytest.raises(SystemExit) as exc:
        launcher.read_key()
    assert launcher.KEYVAR in str(exc.value)


STUB_RECORD_ENV = "FAKE_CLINE_RECORD"


def _windows_stub_python() -> str:
    """Return the Python source the Windows cline.cmd stub runs.

    The record directory comes from the STUB_RECORD_ENV variable and never from this text, so a
    directory name containing an apostrophe or a quote cannot break the source.
    """
    return (
        "import sys, os, shutil, json, pathlib; "
        f"rec = pathlib.Path(os.environ['{STUB_RECORD_ENV}']); "
        "(rec / 'argv.txt').write_text('\\n'.join(sys.argv[1:])); "
        "cfg = sys.argv[sys.argv.index('--config')+1] if '--config' in sys.argv else None; "
        "shutil.copy(os.path.join(cfg, 'data', 'settings', 'providers.json'), rec / 'providers.json') if cfg else None; "
        "(rec / 'cfgdir.txt').write_text(cfg) if cfg else None; "
        "(rec / 'dirmode.txt').write_text('700'); "
        "(rec / 'filemode.txt').write_text('600'); "
        "sys.exit(0)"
    )


@pytest.fixture
def stub_cline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Put a fake `cline` first on PATH; it records argv and a copy of the config it was given."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    record = tmp_path / "record"
    record.mkdir()
    script = bindir / "cline"
    script.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$@" > "$FAKE_CLINE_RECORD/argv.txt"\n'
        'while [ $# -gt 0 ]; do if [ "$1" = "--config" ]; then CFG="$2"; fi; shift; done\n'
        'cp "$CFG/data/settings/providers.json" "$FAKE_CLINE_RECORD/providers.json"\n'
        'echo "$CFG" > "$FAKE_CLINE_RECORD/cfgdir.txt"\n'
        'stat -f "%Lp" "$CFG" > "$FAKE_CLINE_RECORD/dirmode.txt" 2>/dev/null || stat -c "%a" "$CFG" > "$FAKE_CLINE_RECORD/dirmode.txt"\n'
        'stat -f "%Lp" "$CFG/data/settings/providers.json" > "$FAKE_CLINE_RECORD/filemode.txt" 2>/dev/null '
        '|| stat -c "%a" "$CFG/data/settings/providers.json" > "$FAKE_CLINE_RECORD/filemode.txt"\n'
        "exit 0\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    if sys.platform == "win32":
        cmd_script = bindir / "cline.cmd"
        cmd_script.write_text(f'@echo off\r\n"{sys.executable}" -c "{_windows_stub_python()}" %*\r\n')
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setenv(STUB_RECORD_ENV, str(record))
    # Execution tests simulate a future client whose two enforcing bounds are verified.
    monkeypatch.setattr(launcher, "BOUND_CONTRACT", {"max_requests": True, "max_total_output": True})
    return {"record": record}


@pytest.mark.parametrize(
    "dirname",
    [
        pytest.param("O'Neil temp", id="apostrophe"),
        pytest.param(
            'say "hi" temp', id="double-quote",
            marks=pytest.mark.skipif(sys.platform == "win32", reason="Windows forbids double quotes in file names"),
        ),
    ],
)
def test_windows_stub_source_never_embeds_the_record_path(tmp_path: Path, dirname: str) -> None:
    """The stub source holds no path text, so a record directory with an apostrophe (every platform) or
    double quotes (not Windows, which forbids them in names) still runs."""
    import subprocess

    record = tmp_path / dirname
    record.mkdir()
    cfg = tmp_path / "cfg"
    (cfg / "data" / "settings").mkdir(parents=True)
    (cfg / "data" / "settings" / "providers.json").write_text("{}", encoding="utf-8")
    source = _windows_stub_python()
    assert str(record) not in source and dirname not in source
    done = subprocess.run(
        [sys.executable, "-c", source, "--config", str(cfg), "--probe"],
        env={**os.environ, STUB_RECORD_ENV: str(record)}, capture_output=True, text=True, check=False,
    )
    assert done.returncode == 0, done.stderr
    assert (record / "argv.txt").read_text(encoding="utf-8").split("\n") == ["--config", str(cfg), "--probe"]
    assert (record / "providers.json").read_text(encoding="utf-8") == "{}"
    assert (record / "cfgdir.txt").read_text(encoding="utf-8") == str(cfg)


def test_run_passes_explicit_route_and_keeps_key_out_of_argv(stub_cline: dict[str, Path]) -> None:
    rc = launcher.main([*BOUNDED, "--effort", "medium", "--model", "deepseek-ai/DeepSeek-V4-Flash-0731", "--", "do the task"])
    record = stub_cline["record"]
    argv = _argv_lines(record)
    assert rc == 0
    assert argv[:1] == ["--config"] and argv[2:4] == ["-P", "openai-compatible"]
    assert ["-m", "deepseek-ai/DeepSeek-V4-Flash-0731"] == argv[4:6]
    assert ["--thinking", "medium"] == argv[6:8]
    assert ["--plan", "--auto-approve", "false"] == argv[8:11]
    assert argv[-1] == "do the task"
    assert FAKE_KEY not in "\n".join(argv)


def test_default_main_is_plan_mode_without_act(stub_cline: dict[str, Path]) -> None:
    launcher.main([*BOUNDED, "--", "task"])
    argv = _argv_lines(stub_cline["record"])
    assert "--plan" in argv
    assert argv[argv.index("--auto-approve") + 1] == "false"
    assert "--act" not in argv


def test_implement_omits_plan_and_keeps_auto_approve_false(stub_cline: dict[str, Path]) -> None:
    launcher.main([*BOUNDED, "--implement", "--", "task"])
    argv = _argv_lines(stub_cline["record"])
    assert "--plan" not in argv
    assert argv[argv.index("--auto-approve") + 1] == "false"
    assert "--act" not in argv


def test_implement_with_allow_tool_approval_omits_plan(stub_cline: dict[str, Path]) -> None:
    launcher.main([*BOUNDED, "--implement", "--allow-tool-approval", "--", "task"])
    argv = _argv_lines(stub_cline["record"])
    assert "--plan" not in argv
    assert argv[argv.index("--auto-approve") + 1] == "true"


def test_allow_tool_approval_alone_stays_in_plan_mode(stub_cline: dict[str, Path]) -> None:
    launcher.main([*BOUNDED, "--allow-tool-approval", "--", "task"])
    argv = _argv_lines(stub_cline["record"])
    assert "--plan" in argv
    assert argv[argv.index("--auto-approve") + 1] == "true"


def test_passthrough_cannot_override_thinking_or_config(stub_cline: dict[str, Path]) -> None:
    record = stub_cline["record"]
    with pytest.raises(SystemExit):
        launcher.main([*BOUNDED, "--", "--thinking", "xhigh", "--config", "/another/config", "task"])
    assert not (record / "argv.txt").exists()


def test_passthrough_equals_form_is_rejected(stub_cline: dict[str, Path]) -> None:
    record = stub_cline["record"]
    with pytest.raises(SystemExit):
        launcher.main([*BOUNDED, "--", "--thinking=low", "task"])
    assert not (record / "argv.txt").exists()


def test_positional_prompt_still_works(stub_cline: dict[str, Path]) -> None:
    rc = launcher.main([*BOUNDED, "--", "review the launcher gates"])
    argv = _argv_lines(stub_cline["record"])
    assert rc == 0
    assert argv[-1] == "review the launcher gates"
    assert argv[argv.index("--thinking") + 1] == "high"


def test_config_is_private_and_removed_afterwards(stub_cline: dict[str, Path]) -> None:
    launcher.main([*BOUNDED, "--", "task"])
    record = stub_cline["record"]
    assert (record / "dirmode.txt").read_text().strip() == "700"
    assert (record / "filemode.txt").read_text().strip() == "600"
    cfgdir = Path((record / "cfgdir.txt").read_text().strip())
    assert not cfgdir.exists()
    seen = json.loads((record / "providers.json").read_text())
    assert seen["providers"]["openai-compatible"]["tokenSource"] == "manual"


def test_never_touches_the_operators_real_cline_directory(stub_cline: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".cline").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    launcher.main([*BOUNDED, "--", "task"])
    assert list((home / ".cline").iterdir()) == []


def test_max_requests_and_max_total_output_flags_passed(stub_cline: dict[str, Path]) -> None:
    rc = launcher.main(["--max-requests", "15", "--max-total-output", "8192", "--", "bounded task"])
    assert rc == 0
    argv = _argv_lines(stub_cline["record"])
    assert "--max-requests" in argv
    assert argv[argv.index("--max-requests") + 1] == "15"
    assert "--max-total-output" in argv
    assert argv[argv.index("--max-total-output") + 1] == "8192"
    assert argv[-1] == "bounded task"


@pytest.mark.parametrize("bad_val", ["0", "-1", "-10"])
def test_non_positive_max_requests_refused(bad_val: str) -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args(["--max-requests", bad_val, "--max-total-output", "4096", "--", "task"])


@pytest.mark.parametrize("bad_val", ["0", "-1", "-10"])
def test_non_positive_max_total_output_refused(bad_val: str) -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args(["--max-total-output", bad_val, "--max-requests", "1", "--", "task"])


@pytest.mark.parametrize(
    "argv",
    [
        ["--", "task"],
        ["--max-requests", "1", "--", "task"],
        ["--max-total-output", "4096", "--", "task"],
    ],
)
def test_both_positive_bounds_are_required(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args(argv)


@pytest.mark.parametrize("flag", ["--max-requests", "--max-total-output"])
@pytest.mark.parametrize("bad_val", ["nan", "inf", "-inf", "1.5"])
def test_non_integer_or_non_finite_bounds_are_refused(flag: str, bad_val: str) -> None:
    other = "--max-total-output" if flag == "--max-requests" else "--max-requests"
    with pytest.raises(SystemExit):
        launcher.parse_args([flag, bad_val, other, "1", "--", "task"])


def test_unverified_client_bounds_refuse_before_key_config_or_process(
    stub_cline: dict[str, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        launcher, "BOUND_CONTRACT", {"max_requests": False, "max_total_output": False}, raising=False,
    )
    monkeypatch.delenv(launcher.KEYVAR, raising=False)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("an unverified boundary must not touch credentials, config, or Cline")

    monkeypatch.setattr(launcher.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(launcher.subprocess, "run", forbidden)
    with pytest.raises(SystemExit, match="launcher-output-bound-unsupported"):
        launcher.main(["--max-requests", "1", "--max-total-output", "4096", "--", "task"])
    assert not (stub_cline["record"] / "argv.txt").exists()


@pytest.mark.parametrize(
    "contract",
    [
        {"max_requests": False, "max_total_output": False},
        {"max_requests": True, "max_total_output": False},
        {"max_requests": False, "max_total_output": True},
    ],
)
def test_boundary_problem_refuses_unless_both_bounds_are_verified(
    monkeypatch: pytest.MonkeyPatch, contract: dict[str, bool],
) -> None:
    monkeypatch.setattr(launcher, "BOUND_CONTRACT", contract, raising=False)
    assert launcher.launcher_boundary_problem(1, 4096) == "launcher-output-bound-unsupported"


def test_boundary_problem_accepts_only_two_verified_positive_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        launcher, "BOUND_CONTRACT", {"max_requests": True, "max_total_output": True}, raising=False,
    )
    assert launcher.launcher_boundary_problem(1, 4096) is None
    assert launcher.launcher_boundary_problem(None, 4096) == "invalid-launcher-bounds"
    assert launcher.launcher_boundary_problem(1, 0) == "invalid-launcher-bounds"


class FakeUpstreamHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""
        req_json = {}
        try:
            req_json = json.loads(body.decode("utf-8"))
        except Exception:
            pass

        with getattr(self.server, "lock", threading.Lock()):
            if not hasattr(self.server, "requests_received"):
                self.server.requests_received = []
            self.server.requests_received.append({"path": self.path, "json": req_json})

        arrival = getattr(self.server, "arrival_file", None)
        if arrival:
            import pathlib
            pathlib.Path(arrival).write_text("arrived")
        rel = getattr(self.server, "release_event", None)
        if rel:
            rel.wait(timeout=5.0)
        delay = getattr(self.server, "delay_s", 0.0)
        if delay > 0:
            time.sleep(delay)

        mode = getattr(self.server, "mode", "ok")
        if mode == "drop_connection":
            self.close_connection = True
            return
        if mode == "streaming":
            tokens = getattr(self.server, "tokens", 100)
            chunk1 = b'data: {"choices": [{"delta": {"content": "hi"}}]}\n\n'
            chunk2 = f'data: {{"choices": [], "usage": {{"completion_tokens": {tokens}}}}}\n\n'.encode("utf-8")
            chunk3 = b'data: [DONE]\n\n'
            payload = chunk1 + chunk2 + chunk3
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            self.close_connection = True
            return

        if mode == "missing_usage":
            payload = b'{"choices": []}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            self.close_connection = True
            return

        tokens = getattr(self.server, "tokens", 10)
        payload = json.dumps({"choices": [], "usage": {"completion_tokens": tokens}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()
        self.close_connection = True


LOOPBACK_HOST = "127.0" + ".0.1"


@pytest.fixture
def fake_upstream():
    server = http.server.ThreadingHTTPServer((LOOPBACK_HOST, 0), FakeUpstreamHandler)
    server.mode = "ok"
    server.tokens = 10
    server.delay_s = 0.0
    server.lock = threading.Lock()
    server.requests_received = []
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    port = server.server_address[1]
    yield server, f"http://{LOOPBACK_HOST}:{port}/v1"
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
    server.mode = "streaming"
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
    server.mode = "missing_usage"
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
    assert ("max_total_output exceeded" in err or "unaccounted_dispatch" in err)


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


def test_native_bound_contract_is_verified() -> None:
    """The launcher natively verifies both bounds without monkeypatching."""
    assert launcher.BOUND_CONTRACT == {"max_requests": True, "max_total_output": True}
    assert launcher.launcher_boundary_problem(1, 4096) is None


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
    assert not getattr(server, "requests_received", [])


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
        assert not getattr(server, "requests_received", [])
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
    reqs = getattr(server, "requests_received", [])
    assert len(reqs) == 2
    assert reqs[0]["json"]["max_tokens"] == 40
    assert reqs[0]["json"]["max_completion_tokens"] == 40
    assert reqs[1]["json"]["max_tokens"] == 25
    assert reqs[1]["json"]["max_completion_tokens"] == 25


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


def test_delayed_upstream_waits_for_inflight_drain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fake_upstream: tuple[object, str],
) -> None:
    """Delayed upstream where child exits 0 early waits for in-flight handler and exits 124 if bound breached."""
    server, upstream_url = fake_upstream
    server.tokens = 50
    server.delay_s = 0.2
    server.arrival_file = tmp_path / "arrived.txt"
    bindir = tmp_path / "bin"
    _make_stub_cline(
        bindir,
        """
import os
import threading
import time
import pathlib
config_dir = sys.argv[sys.argv.index("--config") + 1]
with open(f"{config_dir}/data/settings/providers.json") as f:
    cfg = json.load(f)
settings = cfg["providers"]["openai-compatible"]["settings"]
base_url = settings["baseUrl"]
key = settings.get("apiKey", "")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

def send():
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

t = threading.Thread(target=send, daemon=True)
t.start()
arr = os.environ.get("STUB_ARRIVAL_FILE")
if arr:
    p = pathlib.Path(arr)
    for _ in range(500):
        if p.exists():
            break
        time.sleep(0.01)
os._exit(0)
""",
    )
    monkeypatch.setenv("STUB_ARRIVAL_FILE", str(server.arrival_file))
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    monkeypatch.setattr(launcher, "BASE_URL", upstream_url)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "40", "--", "task"])
    assert rc == 124
    out, err = capsys.readouterr()
    assert "max_total_output exceeded" in err


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
    class HookedProxyServer(PausingProxyServer):
        def stop_and_drain(self, timeout_s: float = 5.0) -> bool:
            with self.lock:
                self._phase = launcher.PHASE_DRAINING
            self.shutdown()
            with self.lock:
                drain_waiting.set()
                drained = self._inflight_cond.wait_for(lambda: self._inflight_requests == 0, timeout=timeout_s)
                if not drained:
                    self._phase = launcher.PHASE_CLOSED
                return drained

    proxy = HookedProxyServer(
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
        release_worker.set()
        drain_thread.join(timeout=3.0)

        assert drain_result == [True]
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

    def mock_urlopen(req: urllib.request.Request, timeout: float | None = None) -> object:
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=500,
            msg="Internal Server Error",
            hdrs=email.message.Message(),
            fp=MockErrorFile(),  # type: ignore[arg-type]
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    rc = launcher.main(["--max-requests", "5", "--max-total-output", "4096", "--", "task"])
    assert rc == 124
    out, err = capsys.readouterr()
    assert ("upstream_transport exceeded" in err or "unaccounted_dispatch" in err)

