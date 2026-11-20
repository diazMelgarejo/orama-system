"""Run model-written code with no secrets, no network and no writes outside a scratch root.

A name filter is not a sandbox. This module gives two independent controls:
  * `run_isolated` starts the child with a scrubbed environment inside a macOS kernel-sandbox
    profile that denies network access, denies file writes outside the scratch root and denies
    reads of listed secret locations. It fails closed when no sandbox is available.
  * `vet_allowlist` accepts only a small, explicit subset of Python for a single function, so a
    candidate is rejected before anything runs. It is a first gate, not the isolation.
"""

from __future__ import annotations

import ast
import builtins
import os
import shutil
import signal
import select
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_PATH = "/usr/bin:/bin"
_KERNEL_SANDBOX_TOOL = "/usr/bin/sandbox-exec"  # the one place the platform tool is named
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000
_SECRET_DIRS = (".ssh", ".aws", ".gnupg", ".config", ".openclaw", ".claude", ".gbrain", ".netrc", ".npmrc")
_MIN_ROOT_DEPTH = 3  # a read root must be at least three components deep, e.g. /opt/homebrew/opt


class SandboxUnavailable(RuntimeError):
    """No kernel sandbox is available and the caller did not allow an unsandboxed run."""


class SandboxTimeout(RuntimeError):
    """The child exceeded its time limit and was killed."""


class SandboxOutputLimit(RuntimeError):
    """The child wrote more than the combined output cap and was killed."""


@dataclass(frozen=True)
class IsolatedResult:
    """The outcome of an isolated run: exit code, decoded output and whether a kernel sandbox was used."""
    returncode: int
    stdout: str
    stderr: str
    sandboxed: bool


def scrubbed_env(home: str | Path = "/var/empty", tmpdir: str | Path | None = None) -> dict[str, str]:
    """A minimal environment: no parent variable is copied, so no key, token or gate survives."""
    env = {
        "PATH": _PATH,
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if tmpdir is not None:
        env["TMPDIR"] = str(tmpdir)
    return env


def _sbpl_quote(path: Path) -> str:
    """Quote a path as a profile string literal, escaping backslashes and double quotes."""
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


_SYSTEM_READ = ("/usr/lib", "/System", "/private/var/db/dyld", "/Library/Frameworks", "/usr/share")
_DEV_READ = ("/dev/null", "/dev/urandom", "/dev/random", "/dev/dtracehelper")


def sandbox_profile(
    root: Path,
    read_roots: Iterable[Path] = (),
    exec_paths: Iterable[Path] = (),
    deny_read: Iterable[Path] = (),
) -> str:
    """Deny-by-default macOS profile.

    Allowed: reading system libraries, the listed read roots and the scratch root; writing only the
    scratch root and /dev/null; executing only the listed interpreter paths. Everything else is denied,
    including network, Apple Events, other mach services and launching any other program. `deny_read`
    is layered on top for paths that sit inside an allowed root.
    """
    q = _sbpl_quote
    lines = [
        "(version 1)",
        "(deny default)",
        "(deny network*)",
        "(allow sysctl-read)",
        "(allow signal (target self))",
        "(allow file-read-metadata)",
        '(allow file-read-data (literal "/"))',  # path resolution needs the root entry; nothing below it
    ]
    reads = [Path(p) for p in _SYSTEM_READ] + [Path(root)] + [Path(p) for p in read_roots]
    lines.append("(allow file-read* " + " ".join(f"(subpath {q(p)})" for p in reads)
                 + " " + " ".join(f"(literal {q(Path(p))})" for p in _DEV_READ) + ")")
    lines.append(f'(allow file-write* (subpath {q(Path(root))}) (literal "/dev/null"))')
    for exe in exec_paths:
        lines.append(f"(allow process-exec (literal {q(Path(exe))}))")
    lines += [f"(deny file-read* (subpath {q(Path(p))}))" for p in deny_read]
    return "\n".join(lines)


def default_deny_read() -> list[Path]:
    """Secret locations under the user's home, denied on top of every allowed read root."""
    home = Path(os.path.expanduser("~"))
    return [home / name for name in _SECRET_DIRS]


def merge_deny_read(extra: Iterable[Path] | None) -> list[Path]:
    """Add caller spellings and their resolved paths, including missing descendants, without duplicates.

    Resolution failures propagate rather than silently omitting a denial. Paths should not be
    retargeted between profile construction and child access.
    """
    merged = default_deny_read()
    for p in extra or []:
        path = Path(p)
        for candidate in (path, path.resolve(strict=False)):
            if candidate not in merged:
                merged.append(candidate)
    return merged


def check_read_roots(roots: Iterable[Path]) -> None:
    """Refuse a read root that is `/`, the home folder, an ancestor of home, or too shallow."""
    home = Path(os.path.expanduser("~")).resolve()
    for root in roots:
        r = Path(root).resolve()
        if r == Path("/") or r == home or r in home.parents or len(r.parts) < _MIN_ROOT_DEPTH + 1:
            raise SandboxUnavailable(f"read root is too broad to allow: {r}")


def _interpreter_paths() -> tuple[list[Path], list[Path]]:
    """Exact read roots and exec paths the current interpreter needs, as real paths."""
    import sysconfig

    exe = Path(sys.executable)
    roots = {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()}
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        value = sysconfig.get_paths().get(key)
        if value:
            roots.add(Path(value).resolve())
    execs = {exe, exe.resolve()}
    return sorted(roots), sorted(execs)


def sandbox_available() -> bool:
    """True when the platform's kernel sandbox tool can be used on this machine."""
    return sys.platform == "darwin" and os.access(_KERNEL_SANDBOX_TOOL, os.X_OK)


class _KqueueExit:
    """Watches one process for exit through a kqueue held for the whole run. Never reaps the process."""

    def __init__(self, pid: int) -> None:
        """Register interest in `pid` exiting. ESRCH means it already exited; the leader is still
        unreaped then, so the group id is still reserved and that counts as exited."""
        self._kq = select.kqueue()
        self._done = False
        try:
            event = select.kevent(
                pid, filter=select.KQ_FILTER_PROC, flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                fflags=select.KQ_NOTE_EXIT,
            )
            self._kq.control([event], 0, 0)
        except ProcessLookupError:
            self._done = True
        except BaseException:
            self._kq.close()
            raise

    def exited(self) -> bool:
        """True once the exit event has been delivered or registration found the process already gone."""
        if not self._done:
            self._done = bool(self._kq.control(None, 1, 0))
        return self._done

    def close(self) -> None:
        """Release the kqueue."""
        self._kq.close()


class _ProcExit:
    """Watches one process for exit by reading /proc/<pid>/stat. Never reaps the process."""

    def __init__(self, pid: int) -> None:
        """Remember the pid to watch."""
        self._pid = pid

    def exited(self) -> bool:
        """True when the process is a zombie or its /proc entry is gone."""
        try:
            with open(f"/proc/{self._pid}/stat", encoding="utf-8") as fh:
                return fh.read().rsplit(")", 1)[1].split()[0] == "Z"
        except FileNotFoundError:
            return True

    def close(self) -> None:
        """Nothing to release."""


def _require_exit_probe() -> None:
    """Raise SandboxUnavailable unless this platform can watch a child's exit without reaping it.

    Called before the child starts, so a platform with no waitid, kqueue or /proc fails closed before any
    model-written code runs.
    """
    if hasattr(os, "waitid") or hasattr(select, "kqueue") or Path("/proc/self/stat").exists():
        return
    raise SandboxUnavailable("cannot observe the child's exit without reaping it on this platform")


def _open_exit_probe(proc: subprocess.Popen):
    """The non-reaping exit probe for this platform, or None where `os.waitid` does the job.

    Order: waitid (Linux; macOS only from CPython 3.13), then kqueue (macOS/BSD), then /proc, otherwise
    SandboxUnavailable. There is no `ps` fallback: polling it every few milliseconds would launch a
    process per poll, and every platform that lacks waitid and /proc has kqueue.
    """
    if hasattr(os, "waitid"):
        return None
    if hasattr(select, "kqueue"):
        return _KqueueExit(proc.pid)
    if Path("/proc/self/stat").exists():
        return _ProcExit(proc.pid)
    raise SandboxUnavailable("cannot observe the child's exit without reaping it on this platform")


def _exited(proc: subprocess.Popen, probe=None) -> bool:
    """True once the leader has exited, WITHOUT ever reaping it, so its pid (and so the group id) stays
    reserved until the group has been killed. Uses `os.waitid(WNOWAIT)` where available, otherwise the
    `probe` from `_open_exit_probe`. It never calls poll(), which would reap the leader before the group
    was signalled."""
    if probe is None:
        return os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    return probe.exited()


def _kill_group(proc: subprocess.Popen) -> None:
    """Kill the child's own process group. Only called while the leader is still unreaped, so the
    group id cannot have been reused by an unrelated process."""
    if proc.returncode is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # The group is ours, so nothing is left to kill: Linux says ESRCH, macOS says EPERM when only
            # the exited, unreaped leader remains.
            pass


def run_isolated(
    argv: list[str],
    cwd: str | Path,
    timeout: float = 60,
    deny_read: Iterable[Path] | None = None,
    allow_unsandboxed: bool = False,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> IsolatedResult:
    """Run `argv` in `cwd` isolated. The scratch root is `cwd`; writes outside it are denied.

    The runner owns the child's whole lifecycle: stdout and stderr are drained concurrently and their
    combined size is capped (SandboxOutputLimit), the time is capped (SandboxTimeout), and on any abnormal
    exit, and on a normal exit too, the child's own process group is killed before the leader is reaped
    and the reader threads are joined, so no descendant outlives the run. Cleanup is armed immediately
    after the child is created, so a failure starting a reader thread still kills and reaps it. The leader
    is never reaped before its group has been signalled, on every platform. The sandboxed path also denies
    forking. With `allow_unsandboxed=True` no profile runs, so that path is for trusted code only. `cwd` is the scratch
    root and must be a dedicated directory; the home folder, its ancestors and `/` are refused.
    """
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be a positive integer")
    root = Path(cwd).resolve()
    check_read_roots([root])
    use_sandbox = sandbox_available()
    if not use_sandbox and not allow_unsandboxed:
        raise SandboxUnavailable("no kernel sandbox available; refusing to run model-written code")
    tmp = root / ".tmp"
    tmp.mkdir(exist_ok=True)
    env = scrubbed_env(home=root, tmpdir=tmp)
    cmd = list(argv)
    if use_sandbox:
        roots, execs = _interpreter_paths()
        check_read_roots(roots)
        cmd = [
            _KERNEL_SANDBOX_TOOL, "-p",
            sandbox_profile(root, roots, execs, deny_read=merge_deny_read(deny_read)),
            *argv,
        ]
    _require_exit_probe()  # before any model-written code runs
    proc = subprocess.Popen(
        cmd, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    # Cleanup is armed the moment the child exists: nothing below may raise outside this try.
    readers: list[threading.Thread] = []
    probe = None
    try:
        probe = _open_exit_probe(proc)
        chunks: dict[str, bytearray] = {"out": bytearray(), "err": bytearray()}
        lock = threading.Lock()
        state = {"total": 0, "over": False}

        def drain(stream, key: str) -> None:
            """Copy one pipe into its buffer until EOF, stopping and flagging when the combined cap is hit."""
            try:
                while True:
                    data = os.read(stream.fileno(), 65536)
                    if not data:
                        return
                    with lock:
                        state["total"] += len(data)
                        if state["total"] > max_output_bytes:
                            state["over"] = True
                            return
                        chunks[key].extend(data)
            except OSError:
                return

        for stream, key in ((proc.stdout, "out"), (proc.stderr, "err")):
            reader = threading.Thread(target=drain, args=(stream, key), daemon=True)
            reader.start()  # only a started thread is recorded, so cleanup never joins an unstarted one
            readers.append(reader)
        deadline = time.monotonic() + timeout
        while not _exited(proc, probe):
            if state["over"]:
                raise SandboxOutputLimit(f"child wrote more than {max_output_bytes} bytes and was killed")
            if time.monotonic() > deadline:
                raise SandboxTimeout(f"child exceeded {timeout}s and was killed")
            time.sleep(0.005)
        _kill_group(proc)  # a descendant may outlive the leader: end the group before the leader is reaped
        proc.wait()
        for reader in readers:
            reader.join(timeout=5)
        if state["over"]:
            raise SandboxOutputLimit(f"child wrote more than {max_output_bytes} bytes")
    except BaseException:
        _kill_group(proc)
        proc.wait()
        for reader in readers:
            reader.join(timeout=5)
        raise
    finally:
        if probe is not None:
            probe.close()
        for stream in (proc.stdout, proc.stderr):
            try:
                stream.close()
            except OSError:
                pass
    return IsolatedResult(
        proc.returncode,
        chunks["out"].decode("utf-8", errors="replace"),
        chunks["err"].decode("utf-8", errors="replace"),
        use_sandbox,
    )


# --- allowlist vet -----------------------------------------------------------------------------

_SAFE_BUILTINS = frozenset({
    "isinstance", "list", "tuple", "set", "dict", "str", "int", "bool", "len", "any", "all", "sorted",
    "repr", "min", "max", "range", "enumerate", "zip", "reversed", "True", "False", "None",
})
_SAFE_ATTRS = frozenset({
    "fullmatch", "match", "search", "sub", "split", "compile", "escape", "startswith", "endswith",
    "join", "strip", "lstrip", "rstrip", "lower", "upper", "casefold", "isascii", "isalnum", "isdigit",
    "isalpha", "values", "items", "keys", "get", "append", "add", "translate", "replace", "count", "find",
})
_BUILTIN_NAMES = frozenset(dir(builtins))
_ALLOWED_NODES = (
    ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.If,
    ast.For, ast.Expr, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Attribute,
    ast.Subscript, ast.Slice, ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict, ast.ListComp,
    ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension, ast.IfExp, ast.JoinedStr,
    ast.FormattedValue, ast.Pass, ast.Break, ast.Continue, ast.keyword, ast.Load, ast.Store,
    ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd, ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.FloorDiv,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
)


class _Vet(ast.NodeVisitor):
    """Scope-aware allowlist walk. A name is readable only if it is bound in an enclosing scope of the
    function being vetted, or is an allowed name or safe builtin. Nothing may bind or read a dunder
    name, bind a builtin's name, take parameter defaults, or be variadic, in any scope."""

    def __init__(self, allowed: frozenset[str]) -> None:
        """Create a walker that accepts only the given extra names."""
        self.allowed = allowed
        self.scopes: list[set[str]] = []
        self.problems: set[str] = set()

    # -- bindings and reads ------------------------------------------------------------------
    def _bind(self, name: str) -> None:
        """Record a name bound in the current scope, flagging dunder and builtin names."""
        if name.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {name}")
        elif name in _BUILTIN_NAMES:
            self.problems.add(f"binding a builtin name is not allowed: {name}")
        self.scopes[-1].add(name)

    def _read(self, name: str) -> None:
        """Check that a name read is bound in scope, allowed, or a safe builtin."""
        if name.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {name}")
        elif not (any(name in scope for scope in self.scopes) or name in self.allowed or name in _SAFE_BUILTINS):
            self.problems.add(f"name not allowed: {name}")

    # -- dispatch ----------------------------------------------------------------------------
    def visit(self, node: ast.AST):
        """Visit a node, rejecting any node type outside the allowlist."""
        if not isinstance(node, _ALLOWED_NODES):
            self.problems.add(f"node not allowed: {type(node).__name__}")
            return None
        return super().visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Treat a name as a binding when stored and as a read otherwise."""
        if isinstance(node.ctx, ast.Store):
            self._bind(node.id)
        else:
            self._read(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Allow only listed, non-underscore attribute names."""
        if node.attr.startswith("_") or node.attr not in _SAFE_ATTRS:
            self.problems.add(f"attribute not allowed: {node.attr}")
        self.visit(node.value)

    def visit_keyword(self, node: ast.keyword) -> None:
        """Refuse dunder keyword names and visit the value."""
        if node.arg and node.arg.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {node.arg}")
        self.visit(node.value)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Vet a function: no decorators, defaults or variadics; bind parameters in a new scope."""
        if self.scopes:  # a nested def binds its name in the enclosing scope
            self._bind(node.name)
        elif node.name.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {node.name}")
        if node.decorator_list:
            self.problems.add("decorators are not allowed")
        a = node.args
        if a.defaults or any(d is not None for d in a.kw_defaults):
            self.problems.add("parameter defaults are not allowed")
        if a.vararg or a.kwarg:
            self.problems.add("variadic parameters are not allowed")
        params = [*a.posonlyargs, *a.args, *a.kwonlyargs]
        for arg in params:  # annotations are read in the enclosing scope
            if arg.annotation is not None:
                self.visit(arg.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        self.scopes.append(set())
        for arg in params:
            self._bind(arg.arg)
        for stmt in node.body:
            self.visit(stmt)
        self.scopes.pop()

    def _comprehension(self, node: ast.AST, elements: list[ast.AST]) -> None:
        """Walk a comprehension in its own scope so its targets do not leak."""
        self.scopes.append(set())
        for gen in node.generators:  # type: ignore[attr-defined]
            self.visit(gen.iter)
            self.visit(gen.target)
            for cond in gen.ifs:
                self.visit(cond)
        for element in elements:
            self.visit(element)
        self.scopes.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Vet a list comprehension."""
        self._comprehension(node, [node.elt])

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Vet a set comprehension."""
        self._comprehension(node, [node.elt])

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Vet a generator expression."""
        self._comprehension(node, [node.elt])

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Vet a dict comprehension."""
        self._comprehension(node, [node.key, node.value])


def vet_allowlist(source: str, target: str, allowed_names: Iterable[str]) -> list[str]:
    """Reasons to reject `source`; empty means it uses only the allowlisted subset.

    The source must be exactly one top-level function named `target`. Only listed node types,
    builtins, attribute names and the caller's `allowed_names` may appear. No import, lambda, while
    loop, global, try, with, class, dunder name or underscore-prefixed attribute is allowed, in any
    scope. Reads follow lexical scope: a name bound only inside a nested function is not readable
    outside it, and a comprehension's target does not leak.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg}"]
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef) or tree.body[0].name != target:
        return [f"source must be exactly one top-level def {target}"]
    walker = _Vet(frozenset(allowed_names))
    walker.visit(tree.body[0])
    return sorted(walker.problems)
