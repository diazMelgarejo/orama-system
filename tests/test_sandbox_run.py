"""Model-written code must run with no secrets, no network, no writes outside a scratch root."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.usefixtures("offline_guard")

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
    canary = tmp_path / "canary"
    canary.mkdir()
    (canary / "token.txt").write_text("top-secret")
    code = f"""
        from pathlib import Path
        try:
            print(Path({str(canary / 'token.txt')!r}).read_text())
        except OSError:
            print("BLOCKED")
    """
    control = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30)
    assert "top-secret" in control.stdout  # positive control: readable when not denied
    r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30, deny_read=[canary])
    assert "BLOCKED" in r.stdout and "top-secret" not in r.stdout


@needs_sandbox
def test_a_runaway_child_is_killed_at_the_timeout(sb, tmp_path) -> None:
    with pytest.raises(sb.SandboxTimeout):
        sb.run_isolated(_py("import time; time.sleep(60)"), cwd=tmp_path, timeout=2)


def test_it_fails_closed_when_no_sandbox_is_available(sb, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sb, "sandbox_available", lambda: False)
    with pytest.raises(sb.SandboxUnavailable):
        sb.run_isolated(_py("print(1)"), cwd=tmp_path, timeout=5)


def test_unsandboxed_runs_need_an_explicit_flag_and_still_scrub_the_env(sb, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sb, "sandbox_available", lambda: False)
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


# --- security review follow-up: read roots must never be broad ---------------------------------


def test_the_computed_read_roots_are_never_home_root_or_an_ancestor_of_home(sb) -> None:
    home = Path.home().resolve()
    roots, _execs = sb._interpreter_paths()
    assert roots
    for r in roots:
        assert r != Path("/") and r != home and r not in home.parents, r


@pytest.mark.parametrize("bad", ["/", "/Users", "HOME", "HOME_PARENT", "/private", "/usr", "/Library"])
def test_a_broad_read_root_is_refused(sb, bad: str) -> None:
    home = Path.home().resolve()
    root = {"HOME": home, "HOME_PARENT": home.parent}.get(bad, Path(bad))
    with pytest.raises(sb.SandboxUnavailable):
        sb.check_read_roots([root])


def test_ordinary_roots_are_accepted(sb) -> None:
    home = Path.home().resolve()
    sb.check_read_roots([home / ".local/share/python-default-3.13", Path("/Library/Frameworks/Python.framework/Versions/3.13")])


def test_a_broad_interpreter_layout_fails_closed(sb, tmp_path, monkeypatch) -> None:
    home = Path.home().resolve()
    monkeypatch.setattr(sb.sys, "prefix", str(home))
    monkeypatch.setattr(sb.sys, "base_prefix", str(home))
    with pytest.raises(sb.SandboxUnavailable):
        sb.run_isolated(_py("print(1)"), cwd=tmp_path, timeout=5)


def test_secret_locations_are_denied_by_default_even_inside_an_allowed_root(sb, tmp_path) -> None:
    home = Path.home().resolve()
    profile = sb.sandbox_profile(tmp_path, [home / ".local"], [], deny_read=sb.default_deny_read())
    for name in (".ssh", ".aws", ".gnupg", ".config", ".openclaw", ".claude", ".gbrain", ".netrc", ".npmrc"):
        assert str(home / name) in profile, name


def test_caller_denials_are_merged_with_the_defaults(sb) -> None:
    extra = Path("/private/tmp/extra-secret")
    merged = sb.merge_deny_read([extra])
    assert extra in merged and (Path.home() / ".ssh") in merged
    assert sb.merge_deny_read(None) == sb.default_deny_read()


def test_read_roots_are_exact_directories_not_a_parent_of_the_binary(sb) -> None:
    roots, execs = sb._interpreter_paths()
    exe = Path(sys.executable).resolve()
    assert exe.parent.parent not in roots or exe.parent.parent == Path(sys.base_prefix).resolve()


# --- redesign: the vet tracks lexical scope and refuses dunder names outright ----------------------------

SCOPE_NAMES = {"Any", "re"}


@pytest.mark.parametrize(
    "src",
    [
        # a nested function's parameter must not make the name readable in the outer function
        "def f(owners):\n    def g(__builtins__):\n        return 1\n    return __builtins__",
        "def f(owners):\n    def g(len):\n        return 1\n    return owners",              # shadows a builtin in a nested scope
        "def f(owners):\n    def g(helper):\n        return helper\n    return helper",         # bound only in g
        "def f(owners):\n    def g():\n        x = 1\n    return x",                            # assigned only in g
        "def f(owners):\n    return [x for x in owners] + [x]",                                # comprehension target does not leak
        "def f(owners):\n    return __builtins__",
        "def f(__owners):\n    return 1",                                                       # dunder parameter name
        "def f(owners):\n    __x = 1\n    return owners",                                      # dunder assignment
        "def f(owners):\n    def __g():\n        return 1\n    return owners",                  # dunder nested def
        "def f(owners):\n    return owners.get(__import__='x')",                               # dunder keyword
        "def f(owners):\n    def g(a=1):\n        return a\n    return owners",                 # default in a nested function
        "def f(owners):\n    def g(*a):\n        return a\n    return owners",                  # variadic in a nested function
    ],
)
def test_the_vet_is_scope_aware_and_refuses_dunder_names(sb, src: str) -> None:
    assert sb.vet_allowlist(src, target="f", allowed_names=SCOPE_NAMES), src


@pytest.mark.parametrize(
    "src",
    [
        "def f(owners):\n    def g(item):\n        return item.strip()\n    return [g(o) for o in owners]",
        "def f(owners):\n    out = []\n    for o in owners:\n        out.append(len(o))\n    return out",
        "def f(owners):\n    def inner(x):\n        return re.fullmatch('a', x)\n    return inner('a')",   # allowed_names reach nested scopes
        "def f(owners):\n    return {k: v for k, v in owners.items()}",
        "def f(owners) -> list[str]:\n    return sorted({o for o in owners})",
    ],
)
def test_ordinary_nested_helpers_and_comprehensions_are_allowed(sb, src: str) -> None:
    assert sb.vet_allowlist(src, target="f", allowed_names=SCOPE_NAMES) == [], src


# --- redesign: the runner owns the whole process lifecycle ------------------------------------------------


@needs_sandbox
def test_runaway_output_is_bounded_and_the_child_is_killed(sb, tmp_path) -> None:
    import time

    code = """
        import sys
        chunk = "x" * 65536
        while True:
            sys.stdout.write(chunk)
    """
    started = time.monotonic()
    with pytest.raises(sb.SandboxOutputLimit):
        sb.run_isolated(_py(code), cwd=tmp_path, timeout=30, max_output_bytes=200_000)
    assert time.monotonic() - started < 15


@needs_sandbox
def test_the_cap_counts_stdout_and_stderr_together(sb, tmp_path) -> None:
    code = """
        import sys
        sys.stdout.write("o" * 70000)
        sys.stdout.flush()
        sys.stderr.write("e" * 70000)
        sys.stderr.flush()
    """
    with pytest.raises(sb.SandboxOutputLimit):
        sb.run_isolated(_py(code), cwd=tmp_path, timeout=30, max_output_bytes=100_000)
    ok = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30, max_output_bytes=200_000)
    assert len(ok.stdout) == 70000 and len(ok.stderr) == 70000


@pytest.mark.parametrize("bad", [0, -1, True, None, "10", 1.5])
def test_a_bad_output_cap_is_refused(sb, tmp_path, bad) -> None:
    with pytest.raises(ValueError):
        sb.run_isolated(_py("print(1)"), cwd=tmp_path, timeout=5, max_output_bytes=bad)


@needs_sandbox
def test_the_child_cannot_fork_so_it_leaves_no_descendants(sb, tmp_path) -> None:
    code = """
        import os, subprocess
        for attempt in ("fork", "spawn"):
            try:
                if attempt == "fork":
                    pid = os.fork()
                    print("FORKED", pid)
                else:
                    subprocess.Popen(["/bin/sleep", "60"])
                    print("SPAWNED")
            except OSError as exc:
                print("DENIED", attempt, type(exc).__name__)
    """
    r = sb.run_isolated(_py(code), cwd=tmp_path, timeout=30)
    assert "DENIED fork" in r.stdout and "DENIED spawn" in r.stdout
    assert "FORKED" not in r.stdout and "SPAWNED" not in r.stdout


def _alive(pid: int) -> bool:
    import os

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@needs_sandbox
@pytest.mark.parametrize("how", ["timeout", "output"])
def test_the_process_is_gone_after_an_abnormal_exit(sb, tmp_path, how: str) -> None:
    import time

    code = f"""
        import os, sys, time
        open("child.pid", "w").write(str(os.getpid()))
        if {how!r} == "output":
            while True:
                sys.stdout.write("x" * 65536)
        time.sleep(120)
    """
    expected = sb.SandboxTimeout if how == "timeout" else sb.SandboxOutputLimit
    with pytest.raises(expected):
        sb.run_isolated(_py(code), cwd=tmp_path, timeout=2, max_output_bytes=150_000)
    pid = int((tmp_path / "child.pid").read_text())
    for _ in range(50):
        if not _alive(pid):
            break
        time.sleep(0.1)
    assert not _alive(pid), "the sandboxed process outlived the run"


@needs_sandbox
def test_reader_threads_do_not_leak(sb, tmp_path) -> None:
    import threading

    before = threading.active_count()
    for _ in range(3):
        sb.run_isolated(_py("print('hi')"), cwd=tmp_path, timeout=30)
        with pytest.raises(sb.SandboxTimeout):
            sb.run_isolated(_py("import time; time.sleep(60)"), cwd=tmp_path, timeout=1)
    assert threading.active_count() <= before + 1


def test_the_profile_does_not_allow_forking(sb, tmp_path) -> None:
    profile = sb.sandbox_profile(tmp_path, read_roots=[], exec_paths=[])
    assert "(allow process-fork)" not in profile
