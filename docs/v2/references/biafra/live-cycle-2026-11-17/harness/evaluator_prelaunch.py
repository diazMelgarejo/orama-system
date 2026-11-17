"""Fixed evaluator, pair loop 5: the pre-launch decision of live_cycle (`_prelaunch`).

Reviewer inputs: orama PR 519 review comments on biafra_cycle.py (guard mandatory before the marker;
an invalid effort must refuse before budget is reserved). metric = failed_cases + 100 * new_failed_tests.
Neither seat may edit this file. The candidate replaces only the function `_prelaunch`.
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(os.environ.get("ORAMA_REPO", Path.cwd()))
COPY = ["bin/agents", "tests/test_live_cycle.py", "tests/_offline.py", "tests/conftest.py",
        "tests/fixtures", "docs/v2/references/biafra", "bin/orama-system/skills/cline-wandb/scripts"]
TARGET = "_launch_decision"
_spec = _ilu.spec_from_file_location("sandbox_run", REPO / "bin/agents/sandbox_run.py")
sandbox_run = _ilu.module_from_spec(_spec); sys.modules["sandbox_run"] = sandbox_run; _spec.loader.exec_module(sandbox_run)
ALLOWED_NAMES = set()
PENALTY = 1000.0
BASELINE_TEST_FAILURES = 8  # permissive-guard artifact (402 classification), equal for baseline and reference


def extract_code(answer: str):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", answer, flags=re.S)
    return blocks[0].strip("\n") if blocks else None


def vet(source: str) -> list:
    return sandbox_run.vet_allowlist(source, TARGET, ALLOWED_NAMES)


def build_tree(function_source):
    tmp = Path(tempfile.mkdtemp(prefix="evalpre-"))
    for rel in COPY:
        src, dst = REPO / rel, tmp / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
    if function_source is not None:
        target = tmp / "bin/agents/biafra_cycle.py"
        text = target.read_text()
        new, n = re.subn(rf"def {TARGET}\(.*?(?=\n\n\ndef _prelaunch)", lambda m: function_source.rstrip("\n"),
                         text, count=1, flags=re.S)
        if n != 1:
            raise RuntimeError("could not splice " + TARGET)
        target.write_text(new)
    # The existing live tests run guardless; give them a permissive guard so only real regressions count.
    t = tmp / "tests/test_live_cycle.py"
    body = t.read_text()
    inject = ("    base.setdefault('spend_guard', type('PG', (), {'preflight': lambda s, n: {'ok': True, 'reservation': None},"
              " 'settle': lambda s, *a, **k: {}, 'release': lambda s, r: None, 'classify': lambda s, t: None})())\n")
    t.write_text(body.replace("    base.update(over)\n", inject + "    base.update(over)\n", 1))
    return tmp


_CASES = r"""
import importlib.util, json, os, sys
from pathlib import Path
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
sc = load("bin/agents/seat_contracts.py", "seat_contracts")
bc = load("bin/agents/biafra_cycle.py", "biafra_cycle")
DIGEST = sc.evaluator_digest([Path("bin/agents/seat_contracts.py")])
class G:
    calls = 0
    def preflight(self, n): G.calls += 1; return {"ok": True, "reservation": object()}
    def settle(self, *a, **k): return {}
    def release(self, r): pass
    def classify(self, t): return None
failed = []
def case(name, fn):
    try: ok = fn()
    except Exception as exc: ok = False; name += " RAISED " + type(exc).__name__
    if not ok: failed.append(name)
def call(**over):
    a = dict(seat="inner", mode="inner", artifact="seat_contracts._owner_folded", prompt="Improve X.",
             evaluator_digest=DIGEST, metric_before=3.0, hypothesis="h", metric_name="m", attempt_id=None,
             log_dir=Path("/tmp/evalpre-log"), mechanism_card=None, effort="high", spend_guard=G())
    a.update(over)
    return bc._prelaunch(**a)
def reason(**over):
    p, tb = call(**over)
    return (p or {}).get("reason")
os.environ.pop("BIAFRA_ORCHESTRATOR_GATE", None); os.environ.pop("BIAFRA_ALLOW_LAUNCH", None)
case("gate closed refuses first", lambda: reason() == "gate-closed")
case("gate closed outranks a missing guard and a bad effort", lambda: reason(spend_guard=None, effort="xhigh") == "gate-closed")
os.environ["BIAFRA_ORCHESTRATOR_GATE"] = "approved"; os.environ["BIAFRA_ALLOW_LAUNCH"] = "1"
case("a valid attempt may start and returns the trace base", lambda: call()[0] is None and call()[1]["seat"] == "inner")
case("no digest", lambda: reason(evaluator_digest=None) == "no-evaluator-digest")
case("non-finite metric", lambda: reason(metric_before=float("nan")) == "non-finite-metric")
case("empty prompt", lambda: reason(prompt="   ") == "empty-prompt")
case("non-string prompt", lambda: reason(prompt=None) == "empty-prompt")
case("malformed digest is an invalid trace", lambda: reason(evaluator_digest="A" * 64) == "invalid-trace")
case("a missing spend guard refuses", lambda: reason(spend_guard=None) == "spend-guard-required")
case("a missing guard is refused even for an otherwise valid attempt", lambda: call(spend_guard=None)[1] is None)
for e in ("xhigh", "max", "ultra", ""):
    case("invalid effort %r refuses" % e, lambda e=e: reason(effort=e) == "invalid-effort")
for e in ("medium", "high", "low", None):
    case("valid effort %r passes" % e, lambda e=e: call(effort=e)[0] is None)
def never_reserves():
    G.calls = 0
    for over in ({}, {"effort": "xhigh"}, {"spend_guard": None}, {"evaluator_digest": None}, {"prompt": ""}):
        call(**over)
    return G.calls == 0
case("the pre-launch decision never reserves budget", never_reserves)
def pure_refusal_shape():
    p, tb = call(effort="xhigh")
    return isinstance(p, dict) and tb is None and "reason" in p
case("a refusal is (dict with reason, None)", pure_refusal_shape)
print(json.dumps({"failed_cases": failed}))
"""


def run_cases(tree):
    out = sandbox_run.run_isolated([sys.executable, "-I", "-c", _CASES], cwd=tree, timeout=60)
    if out.returncode != 0:
        raise RuntimeError("cases run failed: " + out.stderr[-300:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def run_existing(tree):
    out = sandbox_run.run_isolated([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                    "tests/test_live_cycle.py"], cwd=tree, timeout=180)
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
    new_fail = max(0, failed_tests - BASELINE_TEST_FAILURES)
    return {"metric_after": float(n + 100 * new_fail),
            "detail": {**cases, "failed_existing_tests": failed_tests, "failed_case_count": n}}


def evaluate_answer(answer):
    code = extract_code(answer)
    if code is None:
        return {"metric_after": PENALTY, "detail": {"no_code_block": True}}
    result = evaluate_function(code)
    result["detail"]["candidate"] = code
    return result
