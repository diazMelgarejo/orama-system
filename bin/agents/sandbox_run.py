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
    """The default secret denials followed by any caller-supplied ones, without duplicates."""
    merged = default_deny_read()
    for p in extra or []:
        if Path(p) not in merged:
            merged.append(Path(p))
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


def _kill_group(proc: subprocess.Popen) -> None:
    """Kill the child's own process group. Only called while the leader is still unreaped, so the
    group id cannot have been reused by an unrelated process."""
    if proc.returncode is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
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
    exit the child's own process group is killed and the reader threads are joined before the error
    propagates. On the sandboxed path the profile also denies forking, so no descendant can outlive the
    run. With `allow_unsandboxed=True` no profile runs: a descendant may keep a pipe open after the leader
    exits and the output may then be partial; that path is for trusted code only. `cwd` is the scratch
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
    proc = subprocess.Popen(
        cmd, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    chunks: dict[str, bytearray] = {"out": bytearray(), "err": bytearray()}
    lock = threading.Lock()
    state = {"total": 0, "over": False}

    def drain(stream, key: str) -> None:
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

    readers = [
        threading.Thread(target=drain, args=(proc.stdout, "out"), daemon=True),
        threading.Thread(target=drain, args=(proc.stderr, "err"), daemon=True),
    ]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + timeout
    try:
        while proc.poll() is None:
            if state["over"]:
                raise SandboxOutputLimit(f"child wrote more than {max_output_bytes} bytes and was killed")
            if time.monotonic() > deadline:
                raise SandboxTimeout(f"child exceeded {timeout}s and was killed")
            time.sleep(0.005)
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
        self.allowed = allowed
        self.scopes: list[set[str]] = []
        self.problems: set[str] = set()

    # -- bindings and reads ------------------------------------------------------------------
    def _bind(self, name: str) -> None:
        if name.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {name}")
        elif name in _BUILTIN_NAMES:
            self.problems.add(f"binding a builtin name is not allowed: {name}")
        self.scopes[-1].add(name)

    def _read(self, name: str) -> None:
        if name.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {name}")
        elif not (any(name in scope for scope in self.scopes) or name in self.allowed or name in _SAFE_BUILTINS):
            self.problems.add(f"name not allowed: {name}")

    # -- dispatch ----------------------------------------------------------------------------
    def visit(self, node: ast.AST):
        if not isinstance(node, _ALLOWED_NODES):
            self.problems.add(f"node not allowed: {type(node).__name__}")
            return None
        return super().visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._bind(node.id)
        else:
            self._read(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_") or node.attr not in _SAFE_ATTRS:
            self.problems.add(f"attribute not allowed: {node.attr}")
        self.visit(node.value)

    def visit_keyword(self, node: ast.keyword) -> None:
        if node.arg and node.arg.startswith("__"):
            self.problems.add(f"dunder names are not allowed: {node.arg}")
        self.visit(node.value)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
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
        self._comprehension(node, [node.elt])

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._comprehension(node, [node.elt])

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._comprehension(node, [node.elt])

    def visit_DictComp(self, node: ast.DictComp) -> None:
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
