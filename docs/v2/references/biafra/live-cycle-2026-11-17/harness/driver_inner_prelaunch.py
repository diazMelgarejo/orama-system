"""REAL live inner-seat turn 5: redesign the pre-launch decision table (PR 519 review, three comments, one root cause)."""
import importlib.util
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SB = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ORAMA_REPO", Path.cwd()))
sys.path.insert(0, str(SB / "verifier"))
import evaluator_prelaunch as ev  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


req = urllib.request.Request(
    "https://api.inference.wandb.ai/v1/models",
    headers={"Authorization": "Bearer " + os.environ["DEEPSEEK_V4_FLASH_WANDB"]},
)
with urllib.request.urlopen(req, timeout=20) as r:
    ids = {m["id"] for m in json.load(r)["data"]}
if "deepseek-ai/DeepSeek-V4.1-Flash-1017" not in ids:
    sys.exit("ABORT: model not listed")
print("re-probe ok")

sc = load(REPO / "bin/agents/seat_contracts.py", "seat_contracts")
inner = load(REPO / "bin/agents/autoresearch-inner/program.py", "inner_program")
sg = load(REPO / "bin/agents/spend_guard.py", "spend_guard")
guard = sg.SpendGuard()
digest = sc.evaluator_digest([SB / "verifier/evaluator_prelaunch.py"])
before = ev.evaluate_function(None)["metric_after"]
print("baseline metric:", before)

src = (REPO / "bin/agents/biafra_cycle.py").read_text()
func = re.search(r"def _launch_decision\(.*?(?=\n\n\ndef _prelaunch)", src, flags=re.S).group(0)
FENCE = "```"
prompt = f"""You are the inner-seat AutoResearcher. One hypothesis, one change, one measurement.

OBSERVED DEFECTS (real, from the operator-side review of `live_cycle`, reproduced on the current code):
1. NO SPEND GUARD IS REQUIRED. With the gate and arm open and `spend_guard=None`, a live request is launched
   with no attestation check and no budget reservation. A live launch must be refused when no guard is supplied.
2. A BAD `effort` IS FOUND TOO LATE. `effort="xhigh"` (outside EFFORTS) is only detected after budget was
   reserved, so the reservation leaks. It must be refused up front, before anything is reserved.
Both belong in this pure decision table, because every refusal knowable before the request is made here.

TARGET ARTIFACT: the function `_launch_decision` below. It receives facts the caller already computed and
returns {{}} when the attempt may start, else {{"reason": <text>, ...}} for the FIRST failing check.
`efforts` is the tuple ("medium", "high", "low"); `effort` is one of them or None (None means "launcher default"
and is valid). `has_guard` is True when a spend guard object was supplied.

{FENCE}python
{func}
{FENCE}

REQUIRED BEHAVIOUR (the fixed evaluator checks exactly these, in a sandbox with no network):
- Keep every existing check and its reason text, in the existing order.
- After the trace check, refuse with reason exactly "spend-guard-required" when `has_guard` is False.
- After that, refuse with reason exactly "invalid-effort" when `effort` is not None and not in `efforts`
  (so "xhigh", "max", "ultra" and "" are refused; "medium", "high", "low" and None pass).
- A closed gate still outranks everything: with the gate closed, the answer is "gate-closed" even if the
  guard is missing and the effort is bad.
- An attempt with every check satisfied returns {{}}. The function has no side effect and never raises.
- The existing repository tests must still pass.

RULES: Reply with ONE fenced {FENCE}python block containing ONLY the complete replacement function named
`_launch_decision` with the same signature. Use only plain Python constructs: no imports, no lambda, no while
loop, no try, no global, no underscore attributes. No file, network or process access, no exec or eval.
After the code block add at most three sentences naming the single assumption your change makes.
Do not call tools, edit files or run commands."""
result = inner.run_live(
    "harden", prompt, SB / "turn5-inner-log", ev.evaluate_answer, before,
    artifact="biafra_cycle._launch_decision", evaluator_digest=digest,
    hypothesis="Require a spend guard and validate effort in the pure pre-launch decision table, before any reservation",
    metric_name="failed_prelaunch_cases", effort="high", spend_guard=guard,
    ledger_path=SB / "turn5-ledger.jsonl",
)
out = {k: v for k, v in result.items() if k != "answer"}
(SB / "turn5-inner-answer.txt").write_text(result.get("answer") or "")
(SB / "turn5-inner-result.json").write_text(json.dumps(out, indent=2, default=str))
d = result.get("detail") or {}
print("ok:", result["ok"], "reason:", result.get("reason"), "decision:", result.get("decision"))
print("metric before/after:", before, (result.get("trace") or {}).get("metric_after"))
print("failed cases:", d.get("failed_cases"), "| failed tests:", d.get("failed_existing_tests"), "| vet:", d.get("vet_failed"))
print("spend keys:", {k: result.get(k) for k in ("spent", "estimated_usd", "spend") if k in result})
