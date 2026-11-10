"""Native Windows process evidence for the Cline controller (qualification item H08, evidence only).

These tests launch REAL child processes: a real ``cline.cmd`` shim next to a real node entry script. They check
shim resolution, that a prompt full of cmd metacharacters reaches the child byte for byte (it never passes through
cmd.exe), exit-code classification, spawn failure, and that a timed-out child is killed and gone. They skip off
Windows or without node. They do not qualify anything: one host, one run, no real Cline and no network.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cline_autoresearcher as car  # noqa: E402

pytestmark = pytest.mark.skipif(sys.platform != "win32" or shutil.which("node") is None,
                                reason="native Windows evidence needs Windows and node")

ENTRY_JS = """\
const fs = require('fs');
const out = process.env.FAKE_CLINE_OUT;
const mode = process.env.FAKE_CLINE_MODE || 'ok';
if (out) fs.writeFileSync(out, JSON.stringify({argv: process.argv.slice(2), pid: process.pid}));
if (mode === 'hang') { setInterval(() => {}, 1000); }
else if (mode === 'fail') { process.stderr.write('boom\\n'); process.exit(3); }
else { process.stdout.write('FAKE-OK\\n'); }
"""


@pytest.fixture()
def shim(tmp_path, monkeypatch):
    """Build a real npm-style layout (cline.cmd, node_modules/cline/bin/cline) and point CLINE_BIN at the shim."""
    entry = tmp_path / "node_modules" / "cline" / "bin" / "cline"
    entry.parent.mkdir(parents=True)
    entry.write_text(ENTRY_JS, encoding="utf-8")
    cmd = tmp_path / "cline.cmd"
    cmd.write_text("@echo off\r\nnode \"%~dp0node_modules\\cline\\bin\\cline\" %*\r\n", encoding="ascii")
    out = tmp_path / "out.json"
    monkeypatch.setenv("CLINE_BIN", str(cmd))
    monkeypatch.setenv("CLINE_WORKDIR", str(tmp_path / "work"))
    monkeypatch.setenv("FAKE_CLINE_OUT", str(out))
    monkeypatch.delenv("CLINE_ALLOW_ACT", raising=False)
    monkeypatch.delenv("CLINE_PROVIDER", raising=False)
    monkeypatch.delenv("CLINE_MODEL", raising=False)
    return {"cmd": cmd, "entry": entry, "out": out}


def _alive(pid: int) -> bool:
    """Return True when the process id still names a running process (tasklist, no extra dependency)."""
    res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
    return str(pid) in res.stdout


def test_shim_resolves_to_node_plus_entry_not_the_cmd(shim):
    """A cmd shim is never used to carry the prompt: the launcher is node plus the package entry script."""
    launcher = car._cline_launcher(str(shim["cmd"]))
    assert launcher is not None and len(launcher) == 2
    assert Path(launcher[0]).name.lower() in ("node.exe", "node")
    assert Path(launcher[1]) == shim["entry"]
    assert car.cline_available()["available"] is True


def test_metacharacter_prompt_reaches_the_child_byte_for_byte(shim):
    """A prompt with cmd metacharacters, quotes and a percent variable arrives unchanged (no shell re-parse)."""
    prompt = 'review "this" & echo PWNED | more ^ %PATH% > nul <x (a) !b!'
    res = car.dispatch_cline(prompt)
    assert res["outcome"] == "completed", res
    seen = json.loads(shim["out"].read_text(encoding="utf-8"))
    assert prompt in seen["argv"]
    assert "--plan" in seen["argv"] and seen["argv"][seen["argv"].index("--auto-approve") + 1] == "false"
    assert "PWNED" not in res["output"].replace(prompt, "")


def test_nonzero_exit_is_unknown_and_zero_is_completed(shim, monkeypatch):
    """A real nonzero exit is classified unknown (never retried), a real zero exit completed."""
    monkeypatch.setenv("FAKE_CLINE_MODE", "fail")
    bad = car.dispatch_cline("do the thing now")
    assert bad["outcome"] == "unknown" and bad["ok"] is False and "boom" in bad["output"]
    monkeypatch.setenv("FAKE_CLINE_MODE", "ok")
    good = car.dispatch_cline("do the thing now")
    assert good["outcome"] == "completed" and "FAKE-OK" in good["output"]


def test_spawn_failure_is_not_sent(tmp_path, monkeypatch):
    """A file that Windows cannot execute fails at spawn: nothing ran, so the outcome is not-sent."""
    junk = tmp_path / "cline.exe"
    junk.write_bytes(b"")
    monkeypatch.setenv("CLINE_BIN", str(junk))
    monkeypatch.setenv("CLINE_WORKDIR", str(tmp_path / "work"))
    res = car.dispatch_cline("do the thing now")
    assert res["outcome"] == "not-sent" and res["ok"] is False


def test_timed_out_child_is_killed_and_gone(shim, monkeypatch):
    """A hung child hits the timeout: outcome unknown, the node process is killed and no longer running."""
    monkeypatch.setenv("FAKE_CLINE_MODE", "hang")
    real_popen = subprocess.Popen

    class ShortTimeout(real_popen):
        """Real Popen whose communicate timeout is shortened so the test does not wait five minutes."""

        def communicate(self, input=None, timeout=None):  # noqa: A002
            """Delegate to the real communicate with a 3 second ceiling."""
            return super().communicate(input, timeout=3 if timeout else timeout)

    monkeypatch.setattr(car.subprocess, "Popen", ShortTimeout)
    res = car.dispatch_cline("do the thing now")
    assert res["outcome"] == "unknown" and "timed out" in res["output"]
    pid = json.loads(shim["out"].read_text(encoding="utf-8"))["pid"]
    deadline = time.time() + 5
    while _alive(pid) and time.time() < deadline:
        time.sleep(0.2)
    assert not _alive(pid), "the timed-out node child is still running"


@pytest.mark.parametrize("kind", ["cmd", "bat", "ps1"])
def test_shim_kinds_in_a_path_with_spaces_and_non_ascii(tmp_path, monkeypatch, kind):
    """cmd, bat and ps1 shims in a folder with spaces, parentheses and non-ASCII letters all launch node plus entry."""
    root = tmp_path / "Üser Tëst (x86) dir"
    entry = root / "node_modules" / "cline" / "bin" / "cline"
    entry.parent.mkdir(parents=True)
    entry.write_text(ENTRY_JS, encoding="utf-8")
    body = ('@echo off\r\nnode "%~dp0node_modules\cline\bin\cline" %*\r\n' if kind != "ps1"
            else 'node "$PSScriptRoot\node_modules\cline\bin\cline" $args\r\n')
    shim = root / f"cline.{kind}"
    shim.write_text(body, encoding="ascii")
    out = tmp_path / "out.json"
    monkeypatch.setenv("CLINE_BIN", str(shim))
    monkeypatch.setenv("CLINE_WORKDIR", str(tmp_path / "work"))
    monkeypatch.setenv("FAKE_CLINE_OUT", str(out))
    monkeypatch.setenv("FAKE_CLINE_MODE", "ok")
    prompt = 'check "quoted" & piped | caret ^ percent %PATH% (paren) done'
    res = car.dispatch_cline(prompt)
    assert res["outcome"] == "completed", res
    assert prompt in json.loads(out.read_text(encoding="utf-8"))["argv"]


def test_pathext_pick_prefers_a_launchable_shim(tmp_path, monkeypatch):
    """With cline.cmd and an empty cline.ps1 both on PATH the controller picks cline.cmd and can launch it."""
    entry = tmp_path / "node_modules" / "cline" / "bin" / "cline"
    entry.parent.mkdir(parents=True)
    entry.write_text(ENTRY_JS, encoding="utf-8")
    (tmp_path / "cline.cmd").write_text("@echo off\r\n", encoding="ascii")
    (tmp_path / "cline.ps1").write_text("", encoding="ascii")
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("CLINE_BIN", raising=False)
    picked = car._find_cline()
    assert picked is not None and Path(picked).name == "cline.cmd"
    assert car._cline_launcher(picked) is not None
