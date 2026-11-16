"""Model-written code must run with no secrets, no network, no writes outside a scratch root."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("sandbox_run", ROOT / "bin/agents/sandbox_run.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["sandbox_run"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sb():
    return _load()


needs_sandbox = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("sandbox-exec") is None,
    reason="kernel sandbox is macOS sandbox-exec",
)


def _py(code: str) -> list[str]:
    return [sys.executable, "-I", "-c", textwrap.dedent(code)]


# --- environment -------------------------------------------------------------------------------


def test_scrubbed_env_drops_secrets_and_keeps_a_minimal_path(sb, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB", "s3cret")
    monkeypatch.setenv("SOME_API_KEY", "s3cret")
    monkeypatch.setenv("GITHUB_TOKEN", "s3cret")
    monkeypatch.setenv("BIAFRA_ORCHESTRATOR_GATE", "approved")
    env = sb.scrubbed_env()
    assert "s3cret" not in env.values()
    assert not any(k.startswith("BIAFRA_") for k in env)
    assert set(env) <= {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE"}
    assert env["PATH"] == "/usr/bin:/bin"


@needs_sandbox
def test_the_child_cannot_see_the_parents_secrets(sb, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB", "s3cret")
    r = sb.run_isolated(_py("import os; print(sorted(os.environ))"), cwd=tmp_path, timeout=30)
    assert r.returncode == 0 and "DEEPSEEK" not in r.stdout and "s3cret" not in r.stdout + r.stderr


# --- kernel sandbox ----------------------------------------------------------------------------


@needs_sandbox
def test_the_network_is_denied(sb, tmp_path) -> None:
    code = """
        import socket
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            print("CONNECTED")
        except OSError as exc:
            print("DENIED", type(exc).__name__)
    """
    r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30)
    assert "DENIED" in r.stdout and "CONNECTED" not in r.stdout


@needs_sandbox
def test_writes_are_allowed_inside_the_scratch_root_and_denied_outside(sb, tmp_path) -> None:
    outside = Path("/private/tmp") / f"sandbox-probe-{tmp_path.name}"
    code = f"""
        from pathlib import Path
        Path("inside.txt").write_text("ok")
        try:
            Path({str(outside)!r}).write_text("escaped")
            print("ESCAPED")
        except OSError:
            print("CONFINED")
    """
    r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30)
    assert "CONFINED" in r.stdout and not outside.exists()
    assert (tmp_path / "inside.txt").read_text() == "ok"


@needs_sandbox
def test_reads_of_listed_secret_locations_are_denied(sb, tmp_path) -> None:
    canary = tmp_path.parent / f"canary-{tmp_path.name}"
    canary.mkdir()
    (canary / "token.txt").write_text("top-secret")
    code = f"""
        from pathlib import Path
        try:
            print(Path({str(canary / 'token.txt')!r}).read_text())
        except OSError:
            print("BLOCKED")
    """
    try:
        r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30, deny_read=[canary])
    finally:
        shutil.rmtree(canary, ignore_errors=True)
    assert "BLOCKED" in r.stdout and "top-secret" not in r.stdout


@needs_sandbox
def test_a_runaway_child_is_killed_at_the_timeout(sb, tmp_path) -> None:
    with pytest.raises(sb.SandboxTimeout):
        sb.run_isolated(_py("import time; time.sleep(60)"), cwd=tmp_path, timeout=2)


def test_it_fails_closed_when_no_sandbox_is_available(sb, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sb.shutil, "which", lambda name: None)
    with pytest.raises(sb.SandboxUnavailable):
        sb.run_isolated(_py("print(1)"), cwd=tmp_path, timeout=5)


def test_unsandboxed_runs_need_an_explicit_flag_and_still_scrub_the_env(sb, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sb.shutil, "which", lambda name: None)
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB", "s3cret")
    r = sb.run_isolated(_py("import os; print(sorted(os.environ))"), cwd=tmp_path, timeout=30, allow_unsandboxed=True)
    assert r.returncode == 0 and "DEEPSEEK" not in r.stdout and r.sandboxed is False


# --- allowlist vet -----------------------------------------------------------------------------

NAMES = {"Any", "FIXED_WALLS", "_text", "_owner_folded", "_OWNER_SHAPE", "re"}

GOOD = '''def _owner_errors(owners: Any) -> list[str]:
    """Errors."""
    if not isinstance(owners, list) or not owners:
        return ["owner_slices must be a non-empty list"]
    folded = {o: _owner_folded(o) for o in owners}
    walls = sorted({w for f in folded.values() if f for w in FIXED_WALLS if w in f})
    bad = [o for o in owners if not _OWNER_SHAPE.fullmatch(o)]
    return ["x: " + ", ".join(repr(o[:72]) for o in bad)] if (walls or bad) else []'''


def test_the_allowlist_accepts_an_ordinary_small_function(sb) -> None:
    assert sb.vet_allowlist(GOOD, target="_owner_errors", allowed_names=NAMES) == []


# NOTE: the strings below are hostile INPUTS for the vetter to reject. They are parsed, never run.
@pytest.mark.parametrize(
    "body",
    [
        "g = getattr\n    return []",                                    # the denylist bypass
        "return ().__class__.__bases__",                                # dunder attribute
        "import os\n    return []",                                     # import
        "return open('x').read()",                                      # forbidden call
        "return eval('1')",                                             # eval
        "return [c for c in ().__class__.mro()]",                       # dunder via comprehension
        "return type(owners)",                                          # type escape
        "return vars()",                                                # introspection
        "return __builtins__",                                          # builtins
        "f = lambda: 1\n    return []",                                 # lambda
        "global X\n    return []",                                      # global
        "return re.compile('x').__class__",                             # dunder on allowed module
        "while True:\n        pass",                                    # unbounded loop
        "return owners.__dict__",                                       # dunder attribute
        "return re.os.system('x')",                                     # attribute not on the allowlist
    ],
)
def test_the_allowlist_rejects_escape_routes(sb, body: str) -> None:
    src = f"def _owner_errors(owners):\n    {body}"
    assert sb.vet_allowlist(src, target="_owner_errors", allowed_names=NAMES), body


def test_the_allowlist_requires_exactly_the_target_function(sb) -> None:
    assert sb.vet_allowlist("x = 1", target="_owner_errors", allowed_names=NAMES)
    assert sb.vet_allowlist(GOOD + "\n\ndef other():\n    return 1", target="_owner_errors", allowed_names=NAMES)
    assert sb.vet_allowlist("def _owner_errors(owners):\n    return [", target="_owner_errors", allowed_names=NAMES)


def test_a_nested_helper_function_is_allowed(sb) -> None:
    src = '''def _owner_errors(owners):
    def ok(o):
        return bool(_OWNER_SHAPE.fullmatch(o))
    return [o for o in owners if not ok(o)]'''
    assert sb.vet_allowlist(src, target="_owner_errors", allowed_names=NAMES) == []


# --- security review follow-up: scope-aware vet --------------------------------------------------


@pytest.mark.parametrize(
    "src",
    [
        "def _owner_errors(owners, getattr=getattr):\n    return getattr(owners, 'x')",
        "def _owner_errors(owners, eval=eval):\n    return eval('1')",
        "def _owner_errors(owners, g=len):\n    return []",             # any default is refused
        "def _owner_errors(owners, *, k=1):\n    return []",            # keyword-only default
        "def _owner_errors(*owners):\n    return []",                   # varargs
        "def _owner_errors(owners, **kw):\n    return []",              # kwargs
        "def _owner_errors(owners, open):\n    return []",              # parameter shadows a builtin
        "def _owner_errors(owners):\n    type = 1\n    return []",     # assignment shadows a builtin
        "def _owner_errors(owners):\n    def getattr(x):\n        return x\n    return []",
        "def _owner_errors(owners):\n    return [vars for vars in owners]",  # comprehension target
    ],
)
def test_the_vet_refuses_shadowing_and_defaults(sb, src: str) -> None:
    assert sb.vet_allowlist(src, target="_owner_errors", allowed_names=NAMES), src


# --- security review follow-up: deny-by-default sandbox --------------------------------------------


@needs_sandbox
def test_the_profile_is_deny_by_default(sb, tmp_path) -> None:
    profile = sb.sandbox_profile(tmp_path, read_roots=[], exec_paths=[])
    assert "(deny default)" in profile and "(allow default)" not in profile
    assert "(deny network*)" in profile


@needs_sandbox
def test_an_unlisted_home_file_cannot_be_read(sb, tmp_path) -> None:
    canary = tmp_path.parent / f"unlisted-{tmp_path.name}.txt"
    canary.write_text("top-secret")
    code = f"""
        from pathlib import Path
        try:
            print(Path({str(canary)!r}).read_text())
        except OSError:
            print("BLOCKED")
    """
    try:
        r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30)
    finally:
        canary.unlink(missing_ok=True)
    assert "BLOCKED" in r.stdout and "top-secret" not in r.stdout


@needs_sandbox
@pytest.mark.parametrize("tool", ["/usr/bin/osascript", "/usr/bin/open", "/bin/echo", "/usr/bin/curl"])
def test_the_child_cannot_launch_other_programs(sb, tmp_path, tool: str) -> None:
    code = f"""
        import subprocess
        try:
            r = subprocess.run([{tool!r}, "-e", "1"], capture_output=True, timeout=10)
            print("RAN", r.returncode)
        except (OSError, subprocess.SubprocessError) as exc:
            print("DENIED", type(exc).__name__)
    """
    r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30)
    assert "DENIED" in r.stdout and "RAN" not in r.stdout, r.stdout + r.stderr


@needs_sandbox
def test_python_and_pytest_still_run_inside_the_sandbox(sb, tmp_path) -> None:
    r = sb.run_isolated([sys.executable, "-I", "-m", "pytest", "--version"], cwd=tmp_path, timeout=60)
    assert r.returncode == 0 and "pytest" in (r.stdout + r.stderr).lower(), r.stdout + r.stderr
    (tmp_path / "test_x.py").write_text("def test_ok():\n    assert 1 + 1 == 2\n")
    r2 = sb.run_isolated([sys.executable, "-I", "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_x.py"],
                         cwd=tmp_path, timeout=60)
    assert r2.returncode == 0 and "1 passed" in r2.stdout, r2.stdout + r2.stderr
