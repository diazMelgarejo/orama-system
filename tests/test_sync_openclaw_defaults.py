"""The vendored copy only changes after a human confirms the diff on a terminal; nothing else can run the sync."""

from __future__ import annotations

import hashlib
import json
import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts/sync-openclaw-defaults.py"
VENDORED = ROOT / "config/vendored/openclaw-defaults"


def _fake_pt(tmp: Path, **changes) -> Path:
    data = json.loads((VENDORED / "openclaw-defaults.json").read_text(encoding="utf-8"))
    data.pop("_vendor", None)
    data.update(changes)
    (tmp / "config").mkdir(parents=True)
    (tmp / "src/perpetua_tools").mkdir(parents=True)
    (tmp / "config/openclaw-defaults.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (tmp / "src/perpetua_tools/openclaw_defaults.py").write_text((VENDORED / "openclaw_defaults.py").read_text(encoding="utf-8"), encoding="utf-8")
    return tmp


def _vendored(tmp: Path) -> Path:
    out = tmp / "vendored"
    out.mkdir()
    for name in ("openclaw-defaults.json", "openclaw_defaults.py"):
        (out / name).write_text((VENDORED / name).read_text(encoding="utf-8"), encoding="utf-8")
    return out


def _digest(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.iterdir()):
        h.update(p.name.encode() + p.read_bytes())
    return h.hexdigest()


def _run(*args: str, stdin=subprocess.DEVNULL) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(SYNC), *args], capture_output=True, text=True, stdin=stdin)


def _drive_on_a_terminal(args: list[str], answer: str) -> tuple[int, str]:
    """Run the sync attached to a pseudo-terminal, as a human at a keyboard would, and type an answer to the prompt."""
    master, slave = pty.openpty()
    proc = subprocess.Popen([sys.executable, "-I", str(SYNC), *args], stdin=slave, stdout=slave, stderr=slave, close_fds=True)
    os.close(slave)
    out, sent, deadline = b"", False, time.time() + 30
    while time.time() < deadline:
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
            if not sent and b"Type the phrase" in out:
                os.write(master, (answer + "\n").encode())
                sent = True
        elif proc.poll() is not None:
            break
    rc = proc.wait(timeout=10)
    os.close(master)
    return rc, out.decode(errors="replace")


def test_check_mode_is_read_only_and_reports_in_sync(tmp_path: Path) -> None:
    pt, vend = _fake_pt(tmp_path / "pt"), _vendored(tmp_path)
    before = _digest(vend)
    done = _run("--check", "--pt-root", str(pt), "--vendored-dir", str(vend))
    assert done.returncode == 0 and "in sync" in done.stdout
    assert _digest(vend) == before


def test_check_mode_shows_the_diff_and_exits_1_when_the_live_file_moved_on(tmp_path: Path) -> None:
    pt, vend = _fake_pt(tmp_path / "pt", updated="2026-12-01"), _vendored(tmp_path)
    before = _digest(vend)
    done = _run("--check", "--pt-root", str(pt), "--vendored-dir", str(vend))
    assert done.returncode == 1
    assert "differs" in done.stdout and "-  \"updated\"" in done.stdout.replace("--- ", "") or "2026-12-01" in done.stdout
    assert _digest(vend) == before, "check must never write"


def test_apply_refuses_when_there_is_no_human_terminal_and_changes_nothing(tmp_path: Path) -> None:
    pt, vend = _fake_pt(tmp_path / "pt", updated="2026-12-01"), _vendored(tmp_path)
    before = _digest(vend)
    done = _run("--apply", "--pt-root", str(pt), "--vendored-dir", str(vend), stdin=subprocess.DEVNULL)
    assert done.returncode == 3
    assert "terminal" in (done.stdout + done.stderr).lower() and "human" in (done.stdout + done.stderr).lower()
    assert _digest(vend) == before


def test_apply_ignores_any_environment_bypass(tmp_path: Path) -> None:
    pt, vend = _fake_pt(tmp_path / "pt", updated="2026-12-01"), _vendored(tmp_path)
    before = _digest(vend)
    env = {**os.environ, "CI": "1", "YES": "1", "OPENCLAW_DEFAULTS_SYNC_CONFIRM": "yes", "FORCE": "1"}
    done = subprocess.run([sys.executable, "-I", str(SYNC), "--apply", "--pt-root", str(pt), "--vendored-dir", str(vend)], capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env)
    assert done.returncode == 3 and _digest(vend) == before


def test_a_wrong_phrase_on_a_terminal_aborts_without_writing(tmp_path: Path) -> None:
    pt, vend = _fake_pt(tmp_path / "pt", updated="2026-12-01"), _vendored(tmp_path)
    before = _digest(vend)
    rc, out = _drive_on_a_terminal(["--apply", "--pt-root", str(pt), "--vendored-dir", str(vend)], "yes")
    assert rc == 4 and "aborted" in out.lower()
    assert _digest(vend) == before


def test_the_right_phrase_on_a_terminal_writes_both_files_and_the_stamp_verifies(tmp_path: Path) -> None:
    pt, vend = _fake_pt(tmp_path / "pt", updated="2026-12-01"), _vendored(tmp_path)
    probe = _drive_on_a_terminal(["--apply", "--pt-root", str(pt), "--vendored-dir", str(vend)], "no")
    phrase = re.search(r"SYNC OPENCLAW DEFAULTS [0-9a-f]{8}", probe[1]).group(0)
    rc, out = _drive_on_a_terminal(["--apply", "--pt-root", str(pt), "--vendored-dir", str(vend)], phrase)
    assert rc == 0, out
    new = json.loads((vend / "openclaw-defaults.json").read_text(encoding="utf-8"))
    assert new["updated"] == "2026-12-01" and "_vendor" in new
    check = _run("--check", "--pt-root", str(pt), "--vendored-dir", str(vend))
    assert check.returncode == 0 and "in sync" in check.stdout


def test_the_sync_script_has_no_yes_flag_and_no_force_flag() -> None:
    text = SYNC.read_text(encoding="utf-8")
    assert not re.search(r"--yes|--force|--assume|--non-interactive|AUTO_CONFIRM", text)
    assert "isatty" in text
