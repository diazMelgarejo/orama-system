"""Run model-written code with no secrets, no network and no writes outside a scratch root.

A name filter is not a sandbox. This module gives two independent controls:
  * `run_isolated` starts the child with a scrubbed environment inside a macOS `sandbox-exec`
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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_PATH = "/usr/bin:/bin"


class SandboxUnavailable(RuntimeError):
    """No kernel sandbox is available and the caller did not allow an unsandboxed run."""


class SandboxTimeout(RuntimeError):
    """The child exceeded its time limit and was killed."""


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
        "(allow process-fork)",
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


def _interpreter_paths() -> tuple[list[Path], list[Path]]:
    """Read roots and exec paths the current interpreter needs, as real paths."""
    exe = Path(sys.executable)
    roots = {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), exe.resolve().parent.parent}
    try:
        import site
        roots.update(Path(p).resolve() for p in site.getsitepackages())
    except Exception:  # site may be unavailable in odd builds; the prefixes above still apply
        pass
    execs = {exe, exe.resolve()}
    return sorted(roots), sorted(execs)


def run_isolated(
    argv: list[str],
    cwd: str | Path,
    timeout: float = 60,
    deny_read: Iterable[Path] | None = None,
    allow_unsandboxed: bool = False,
) -> IsolatedResult:
    """Run `argv` in `cwd` isolated. The scratch root is `cwd`; writes outside it are denied."""
    root = Path(cwd).resolve()
    use_sandbox = sys.platform == "darwin" and shutil.which("sandbox-exec") is not None
    if not use_sandbox and not allow_unsandboxed:
        raise SandboxUnavailable("no kernel sandbox available; refusing to run model-written code")
    tmp = root / ".tmp"
    tmp.mkdir(exist_ok=True)
    env = scrubbed_env(home=root, tmpdir=tmp)
    cmd = list(argv)
    if use_sandbox:
        roots, execs = _interpreter_paths()
        cmd = [
            "/usr/bin/sandbox-exec", "-p",
            sandbox_profile(root, roots, execs, deny_read=list(deny_read or [])),
            *argv,
        ]
    proc = subprocess.Popen(
        cmd, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise SandboxTimeout(f"child exceeded {timeout}s and was killed") from None
    return IsolatedResult(proc.returncode, out, err, use_sandbox)


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


def _bound_names(func: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.FunctionDef) and node is not func:
            names.add(node.name)
    return names


def vet_allowlist(source: str, target: str, allowed_names: Iterable[str]) -> list[str]:
    """Reasons to reject `source`; empty means it uses only the allowlisted subset.

    The source must be exactly one top-level function named `target`. Only listed node types,
    builtins, attribute names and the caller's `allowed_names` may appear. No import, lambda,
    while loop, global, try, with, class, dunder or underscore-prefixed attribute is allowed.
    Parameters may not have defaults and may not be variadic, and no parameter, assigned or
    comprehension name may shadow any builtin: a name bound in the function is never a way to
    make a builtin readable, because binding a builtin's name is itself refused.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg}"]
    problems: list[str] = []
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef) or tree.body[0].name != target:
        return [f"source must be exactly one top-level def {target}"]
    func = tree.body[0]
    if func.decorator_list:
        problems.append("decorators are not allowed")
    a = func.args
    if a.defaults or any(d is not None for d in a.kw_defaults):
        problems.append("parameter defaults are not allowed")
    if a.vararg or a.kwarg:
        problems.append("variadic parameters are not allowed")
    bound = _bound_names(func)
    for name in sorted(bound & _BUILTIN_NAMES):
        problems.append(f"binding a builtin name is not allowed: {name}")
    permitted = bound | set(allowed_names) | _SAFE_BUILTINS
    for node in ast.walk(func):
        if not isinstance(node, _ALLOWED_NODES):
            problems.append(f"node not allowed: {type(node).__name__}")
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in permitted:
            problems.append(f"name not allowed: {node.id}")
        elif isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr not in _SAFE_ATTRS):
            problems.append(f"attribute not allowed: {node.attr}")
    return sorted(set(problems))
