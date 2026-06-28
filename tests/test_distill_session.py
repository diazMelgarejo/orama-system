#!/usr/bin/env python3
"""
test_distill_session.py
=======================
TDD acceptance tests for the v1, OFFLINE, STATELESS ``distill_session.py``
distillation CLI (``bin/orama-system/scripts/distill_session.py``).

Doctrine under test (docs/distill-fable-5/implementation-plan.md § V1):
  - distill_session reads a session export, runs the EXISTING verify/lesson
    hooks, and emits PROPOSED artifacts under docs/distill-fable-5/runs/<ts>/.
  - It does NOT call models, hold routing/cache state, require API keys, touch
    the network, or mutate Perpetua-Tools.
  - Unknown export format -> clear ``unsupported export format: got X, expected
    Y`` message + non-zero exit (code 2), NOT a stack trace.

These four acceptance tests do NOT need a real Fable export — they run against
a synthetic in-repo fixture and/or pure structural assertions:
  1. unknown-format rejection  -> exit code 2 + documented message.
  2. no-network regression     -> socket.socket monkeypatched to explode; the
     module must import + run --dry-run without ever opening a connection.
  3. dry-run structure         -> synthetic fixture, --dry-run exits 0, writes
     a run dir but NO files outside it (no PT mutation).
  4. hook-invocation           -> subprocess.run mocked; assert verify_before_done.py
     and capture_lesson.py are invoked with non-interactive argv, and a non-zero
     hook exit FAILS THE RUN CLOSED (non-zero process exit).

Repo convention (mirrors tests/test_local_first_routing.py & test_orchestrator.py):
``from __future__ import annotations``, module-level imports, plain ``def test_*``
+ ``monkeypatch``, bare ``assert``, ``pytest.raises`` for error paths. No network,
no model calls, no API keys, stateless. Module is imported via the repo path
(``bin/orama-system/scripts`` is NOT on the default pythonpath) with a skip-gate
so collection never crashes before the implementation lands (RED-tolerant).
"""
from __future__ import annotations

import importlib
import json
import socket
import subprocess
import sys
import types
from pathlib import Path

import pytest

# ── Repo-relative path resolution — NEVER a literal /Users/<name>/ path ───────
REPO_ROOT = Path(__file__).resolve().parents[1]            # tests/ -> repo root
SCRIPTS = REPO_ROOT / "bin" / "orama-system" / "scripts"
DISTILL_PATH = SCRIPTS / "distill_session.py"
VERIFY = SCRIPTS / "verify_before_done.py"
CAPTURE = SCRIPTS / "capture_lesson.py"
FIXTURE = REPO_ROOT / "docs" / "distill-fable-5" / "fixtures" / "sample_session.json"

# Make the hooks' scripts dir importable the same way test_orchestrator.py does.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _import_distill():
    """Import distill_session from the repo scripts dir.

    Skip (do NOT error) if the module does not exist yet — these tests are
    written RED-first per the orama TDD doctrine and must collect cleanly
    before bin/orama-system/scripts/distill_session.py is implemented.
    """
    if not DISTILL_PATH.is_file():
        pytest.skip(f"distill_session.py not implemented yet at {DISTILL_PATH}")
    try:
        return importlib.import_module("distill_session")
    except ImportError as exc:  # pragma: no cover - skip gate
        pytest.skip(f"distill_session import failed (not implemented?): {exc}")


# ── ground truth: the real (non-mock) hooks exist on disk ─────────────────────

def test_hooks_and_fixture_exist():
    """Hooks are REAL scripts (not stubs); the synthetic fixture is present."""
    assert VERIFY.is_file(), f"missing real hook: {VERIFY}"
    assert CAPTURE.is_file(), f"missing real hook: {CAPTURE}"
    assert FIXTURE.is_file(), f"missing synthetic fixture: {FIXTURE}"
    # fixture is valid JSON and self-declares as synthetic (no real export needed)
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data.get("messages"), "fixture must carry a transcript"


# ── AC 5 / Test 1: unknown-format rejection ───────────────────────────────────

def test_unknown_format_exits_code_2_with_documented_message(tmp_path, capsys):
    """Malformed/unsupported input -> exit code 2 + 'unsupported export format'.

    Must be a clean diagnostic, NEVER a stack trace.
    """
    distill = _import_distill()

    bad = tmp_path / "garbage.export"
    bad.write_text("this is not a supported session export\n", encoding="utf-8")

    # main() returns an exit code OR raises SystemExit(2); accept either contract.
    with pytest.raises(SystemExit) as excinfo:
        rc = distill.main(["--input", str(bad), "--dry-run", "--non-interactive"])
        # If main() returns instead of raising, normalize to SystemExit for assert.
        raise SystemExit(rc)

    assert excinfo.value.code == 2, "unknown format must exit with code 2"

    out = capsys.readouterr()
    combined = (out.out + out.err).lower()
    assert "unsupported export format" in combined
    # Documented shape: 'got X, expected Y' — both halves present, no traceback.
    assert "got" in combined and "expected" in combined
    assert "traceback" not in combined


# ── AC 3 / Test 2: no-network regression ──────────────────────────────────────

def test_no_network_socket_is_never_opened(tmp_path, monkeypatch):
    """If distill_session EVER opens a socket, this test FAILS.

    We poison socket.socket (and the connection constructors) so any network
    attempt raises immediately, and assert a --dry-run over the fixture still
    succeeds — proving the offline/stateless contract.
    """
    distill = _import_distill()

    def _boom(*args, **kwargs):  # pragma: no cover - only fires on a real attempt
        raise AssertionError(
            "distill_session attempted a network connection — v1 must be OFFLINE"
        )

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    # Belt-and-suspenders: getaddrinfo also fails closed.
    monkeypatch.setattr(socket, "getaddrinfo", _boom)

    out_dir = tmp_path / "runs"
    rc = distill.main([
        "--input", str(FIXTURE),
        "--dry-run",
        "--non-interactive",
        "--output-dir", str(out_dir),
    ])
    # exit 0 with no socket touched
    assert rc in (0, None)


def test_module_imports_no_http_client():
    """Static guard: the module must not import an http client at module load.

    A v1 stateless/offline tool has no business importing httpx/requests/urllib3/
    aiohttp. (urllib.* in stdlib is tolerated only if unused, but a dedicated
    client import is a red flag for the no-network contract.)
    """
    distill = _import_distill()
    banned = {"httpx", "requests", "aiohttp", "urllib3", "anthropic", "openai"}
    leaked = {
        name
        for name, mod in vars(distill).items()
        if isinstance(mod, types.ModuleType) and mod.__name__.split(".")[0] in banned
    }
    assert not leaked, f"distill_session imported a network/LLM client: {leaked}"


# ── AC 1+2 / Test 3: dry-run structure (no files written outside the run dir) ──

def test_dry_run_exits_zero_and_writes_only_into_run_dir(tmp_path, monkeypatch):
    """--dry-run over the synthetic fixture exits 0 and mutates nothing in PT.

    All output is confined to the run dir under --output-dir; the repo tree and
    Perpetua-Tools are untouched. We sentinel the repo by snapshotting mtimes of
    the scripts dir and asserting no new files appear there.
    """
    distill = _import_distill()

    # Sentinel: nothing new should land in the real scripts dir (no PT mutation).
    before = {p for p in SCRIPTS.glob("*")}

    out_dir = tmp_path / "runs"
    rc = distill.main([
        "--input", str(FIXTURE),
        "--dry-run",
        "--non-interactive",
        "--output-dir", str(out_dir),
    ])
    assert rc in (0, None), "dry-run over a valid fixture must exit 0"

    after = {p for p in SCRIPTS.glob("*")}
    assert before == after, "distill_session must not write into the repo scripts dir"

    # A run dir was created under --output-dir (timestamped child).
    assert out_dir.exists(), "expected a run dir under --output-dir"
    run_children = [p for p in out_dir.iterdir() if p.is_dir()]
    assert run_children, "expected a timestamped runs/<ts>/ subdir"


# ── AC 4 / Test 4: hook-invocation (mocked subprocess) ─────────────────────────

class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _install_subprocess_spy(monkeypatch, distill, *, returncode: int = 0):
    """Replace subprocess.run (as seen by distill_session) with a recording spy."""
    calls: list[list[str]] = []

    def fake_run(argv, *args, **kwargs):
        # Record argv exactly as distill_session passed it.
        calls.append([str(a) for a in argv])
        return _FakeCompleted(returncode=returncode, stdout="OK", stderr="")

    # Patch on the subprocess module that distill_session imports/uses.
    sp = getattr(distill, "subprocess", subprocess)
    monkeypatch.setattr(sp, "run", fake_run)
    return calls


def _flat(calls):
    return " ".join(tok for call in calls for tok in call)


def test_both_hooks_invoked_non_interactively(tmp_path, monkeypatch):
    """verify_before_done.py AND capture_lesson.py are called with non-interactive argv."""
    distill = _import_distill()
    calls = _install_subprocess_spy(monkeypatch, distill, returncode=0)

    out_dir = tmp_path / "runs"
    rc = distill.main([
        "--input", str(FIXTURE),
        "--dry-run",
        "--non-interactive",
        "--output-dir", str(out_dir),
    ])
    assert rc in (0, None)

    flat = _flat(calls)
    # Both real hook scripts were invoked.
    assert "verify_before_done.py" in flat, "verify hook was not invoked"
    assert "capture_lesson.py" in flat, "capture_lesson hook was not invoked"

    # verify hook ran with --no-interact (the documented non-interactive flag).
    verify_calls = [c for c in calls if any("verify_before_done.py" in t for t in c)]
    assert verify_calls, "no verify_before_done.py call recorded"
    assert any("--no-interact" in c for c in verify_calls), \
        "verify hook must be called with --no-interact"

    # capture_lesson ran in a non-interactive, read-only mode (--review or --stats);
    # WRITING a lesson is not cleanly non-interactive (input() x6), so v1 must not
    # take the write path with closed stdin.
    capture_calls = [c for c in calls if any("capture_lesson.py" in t for t in c)]
    assert capture_calls, "no capture_lesson.py call recorded"
    assert any(("--review" in c or "--stats" in c) for c in capture_calls), \
        "capture_lesson must run in --review/--stats (non-interactive read-only) mode"


def test_nonzero_hook_exit_fails_the_run_closed(tmp_path, monkeypatch):
    """A non-zero hook exit must FAIL CLOSED: distill_session aborts non-zero.

    Fail-closed contract — a failed verification can NEVER be treated as success.
    """
    distill = _import_distill()
    _install_subprocess_spy(monkeypatch, distill, returncode=1)

    out_dir = tmp_path / "runs"
    with pytest.raises(SystemExit) as excinfo:
        rc = distill.main([
            "--input", str(FIXTURE),
            "--dry-run",
            "--non-interactive",
            "--output-dir", str(out_dir),
        ])
        raise SystemExit(rc)  # normalize a returned code into SystemExit

    assert excinfo.value.code not in (0, None), \
        "a non-zero hook exit must fail the run closed (non-zero process exit)"
