"""Fixed evaluator for live pair loop 3: two defects the outer seat reported in turn 2 and the operator-side reviewer verified by reproduction.

The cases below are taken from the reviewer's own stated inputs (comment on seat_contracts.py line 30:
delta=10**400, trace metrics, stall_report; comment on line 22: a digest with a trailing newline).
metric = failed_reviewer_cases + 100 * failed_existing_tests      (lower is better)
Neither seat may edit this file. The candidate replaces only the function `_finite`.
"""
from __future__ import annotations

import ast
import os
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(os.environ.get("ORAMA_REPO", Path.cwd()))
COPY = [
    "bin/agents", "tests/test_seat_contracts.py", "tests/fixtures/mechanism_card",
    "docs/v2/references/biafra", "docs/v2/76-biafra-outer-seat-canonical-plan.md",
    "bin/orama-system/skills/cline-wandb/scripts", "bin/orama-system/skills/metaresearcher",
]
TARGET = "_owner_errors"
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("sandbox_run", REPO / "bin/agents/sandbox_run.py")
sandbox_run = _ilu.module_from_spec(_spec); sys.modules["sandbox_run"] = sandbox_run; _spec.loader.exec_module(sandbox_run)
ALLOWED_NAMES = {"Any", "FIXED_WALLS", "_text", "_owner_folded", "_OWNER_SHAPE", "re"}
PENALTY = 1000.0
FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "os", "sys", "subprocess", "socket", "shutil",
    "pathlib", "importlib", "builtins", "globals", "locals", "input", "breakpoint",
}


def extract_code(answer: str):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", answer, flags=re.S)
    return blocks[0].strip("\n") if blocks else None


def vet(source: str) -> list:
    """Allowlist vet: only a small explicit subset of Python is accepted (first gate, not isolation)."""
    return sandbox_run.vet_allowlist(source, TARGET, ALLOWED_NAMES)


def build_tree(function_source):
    tmp = Path(tempfile.mkdtemp(prefix="evalreal-"))
    for rel in COPY:
        src, dst = REPO / rel, tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
    if function_source is not None:
        target = tmp / "bin/agents/seat_contracts.py"
        text = target.read_text()
        new, count = re.subn(
            rf"def {TARGET}\(.*?(?=\n\n\ndef )", lambda m: function_source.rstrip("\n"), text, count=1, flags=re.S
        )
        if count != 1:
            raise RuntimeError("could not splice " + TARGET)
        target.write_text(new)
    return tmp


_CASES = r"""
import importlib.util, json, sys
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
sc = load("bin/agents/seat_contracts.py", "sc")
failed = []
NL, TAB = chr(10), chr(9)
def refused(owners):
    return bool(sc._owner_errors(owners))
def case(name, fn):
    try:
        ok = fn()
    except Exception as exc:
        ok = False; name += " RAISED " + type(exc).__name__
    if not ok:
        failed.append(name)
REAL = "the repository that owns bin/agents/seat_contracts.py and bin/orama-system/skills/metaresearcher/SKILL.md"
for label, owners in [
    ("real sentence from the outer seat", [REAL]),
    ("prose with spaces", ["orama system repo"]),
    ("two repos in one string", ["kungfu and anamnesis"]),
    ("leading space", [" kungfu"]),
    ("trailing space", ["kungfu "]),
    ("trailing newline", ["kungfu" + NL]),
    ("tab inside", ["kun" + TAB + "gfu"]),
    ("over 64 characters", ["a" * 65]),
    ("comma list in one string", ["kungfu,anamnesis"]),
    ("one good one prose", ["kungfu", "the other repo"]),
    ("empty list", []),
    ("not a list", "kungfu"),
    ("None", None),
]:
    case("refuses " + label, lambda o=owners: refused(o) is True)
for label, owners in [
    ("kungfu", ["kungfu"]), ("orama-system", ["orama-system"]), ("perpetua-tools", ["perpetua-tools"]),
    ("two repos", ["anamnesis", "alexandria"]), ("owner/repo", ["diazMelgarejo/orama-system"]),
    ("perpetua-core", ["perpetua-core"]), ("dots underscores", ["a.b_c-d"]), ("64 chars", ["a" * 64]),
]:
    case("accepts " + label, lambda o=owners: refused(o) is False)
for label, owners in [("phylax", ["phylax"]), ("telos glued", ["xtelosx"]), ("agate path", ["agate/fit"]),
                      ("accented", ["Ph" + chr(0xfd) + "lax"]), ("cyrillic", [chr(0x420) + "hylax"]),
                      ("empty after fold", ["---"])]:
    case("keeps refusing " + label, lambda o=owners: refused(o) is True)
case("fixed wall error names E_OWNER", lambda: any("E_OWNER" in e for e in sc._owner_errors(["phylax"])))

# turn 3: verified defects reported by the outer seat in turn 2
for label, owners in [
    ("trailing dot", ["a."]), ("trailing slash", ["a/"]), ("double slash", ["a//b"]),
    ("parent segment", ["a/../b"]), ("current segment", ["a/./b"]), ("dot segment alone", ["a/."]),
    ("segment starting with a dot", ["a/.hidden"]),
]:
    case("refuses degenerate identifier " + label, lambda o=owners: refused(o) is True)
for label, owners in [
    ("single letter", ["a"]), ("single digit", ["1"]), ("org/repo with dots", ["org/repo.name"]),
    ("inner dots", ["a.b.c"]), ("hyphen and underscore", ["x-y_z"]),
]:
    case("accepts " + label, lambda o=owners: refused(o) is False)
def msg(owners):
    return " ".join(sc._owner_errors(owners))
case("empty entry in a mixed list is not blamed on the list", lambda: "non-empty list" not in msg(["", "orama-system"]) and bool(msg(["", "orama-system"])))
case("blank entry alone is not blamed on the list", lambda: "non-empty list" not in msg(["   "]) and bool(msg(["   "])))
case("empty list still says non-empty list", lambda: "non-empty list" in msg([]))
case("non-list still says non-empty list", lambda: "non-empty list" in msg("kungfu"))
case("a non-string element does not raise and is refused", lambda: refused([123]) is True and refused([None]) is True)
case("an identifier error names the entry", lambda: "a//b" in msg(["a//b"]))

print(json.dumps({"failed_cases": failed}))
"""


def run_cases(tree):
    out = sandbox_run.run_isolated([sys.executable, "-I", "-c", _CASES], cwd=tree, timeout=60)
    if out.returncode != 0:
        raise RuntimeError("cases run failed: " + out.stderr[-300:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def run_existing(tree):
    out = sandbox_run.run_isolated(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_seat_contracts.py"],
        cwd=tree, timeout=180,
    )
    m = re.search(r"(\d+) failed", out.stdout)
    if out.returncode != 0 and not m:
        return 999
    return int(m.group(1)) if m else 0


def evaluate_function(source):
    if source is not None:
        problems = vet(source)
        if problems:
            return {"metric_after": PENALTY, "detail": {"vet_failed": problems}}
    tree = build_tree(source)
    try:
        cases = run_cases(tree)
        failed_tests = run_existing(tree)
    except Exception as exc:
        return {"metric_after": PENALTY, "detail": {"error": f"{type(exc).__name__}: {exc}"}}
    finally:
        shutil.rmtree(tree, ignore_errors=True)
    n = len(cases["failed_cases"])
    return {"metric_after": float(n + 100 * failed_tests),
            "detail": {**cases, "failed_existing_tests": failed_tests, "failed_case_count": n}}


def evaluate_answer(answer):
    code = extract_code(answer)
    if code is None:
        return {"metric_after": PENALTY, "detail": {"no_code_block": True}}
    result = evaluate_function(code)
    result["detail"]["candidate"] = code
    return result
