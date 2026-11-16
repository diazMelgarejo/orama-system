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
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_PATH = "/usr/bin:/bin"
_DEFAULT_DENY_READ = (".ssh", ".aws", ".gnupg", ".config", ".openclaw", ".claude", ".gbrain", ".netrc", ".npmrc")


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


def sandbox_profile(root: Path, deny_read: Iterable[Path]) -> str:
    """macOS sandbox profile: allow by default, then deny network, outside writes and secret reads."""
    lines = [
        "(version 1)",
        "(allow default)",
        "(deny network*)",
        f'(deny file-write* (require-not (require-any (subpath {_sbpl_quote(root)}) (literal "/dev/null"))))',
    ]
    lines += [f"(deny file-read* (subpath {_sbpl_quote(Path(p))}))" for p in deny_read]
    return "\n".join(lines)


def _default_deny_read() -> list[Path]:
    home = Path(os.path.expanduser("~"))
    return [home / name for name in _DEFAULT_DENY_READ]


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
        denied = list(_default_deny_read() if deny_read is None else deny_read)
        cmd = ["/usr/bin/sandbox-exec", "-p", sandbox_profile(root, denied), *argv]
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
_ALLOWED_NODES = (
    ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.If,
    ast.For, ast.Expr, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Attribute,
    ast.Subscript, ast.Slice, ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict, ast.ListComp,
    ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension, ast.IfExp, ast.JoinedStr,
    ast.FormattedValue, ast.Pass, ast.Break, ast.Continue, ast.keyword, ast.Load, ast.Store,
    ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd, ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.FloorDiv,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
)


def vet_allowlist(source: str, target: str, allowed_names: Iterable[str]) -> list[str]:
    """Reasons to reject `source`; empty means it uses only the allowlisted subset.

    The source must be exactly one top-level function named `target`. Only listed node types,
    builtins, attribute names and the caller's `allowed_names` may appear. No import, lambda,
    while loop, global, try, with, class, dunder or underscore-prefixed attribute is allowed.
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
    local = {a.arg for a in ast.walk(func.args) if isinstance(a, ast.arg)}
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            local.add(node.id)
        elif isinstance(node, ast.FunctionDef) and node is not func:
            local.add(node.name)
    permitted = local | set(allowed_names) | _SAFE_BUILTINS
    for node in ast.walk(func):
        if not isinstance(node, _ALLOWED_NODES):
            problems.append(f"node not allowed: {type(node).__name__}")
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in permitted:
            problems.append(f"name not allowed: {node.id}")
        elif isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr not in _SAFE_ATTRS):
            problems.append(f"attribute not allowed: {node.attr}")
    return sorted(set(problems))
