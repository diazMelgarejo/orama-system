"""REAL live outer-seat turn 5: Biafra reviews the final redesign of live_cycle (read-only advice)."""
import importlib.util, json, os, subprocess, sys, urllib.request
from pathlib import Path

SB = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ORAMA_REPO", Path.cwd()))
sys.path.insert(0, str(SB / "verifier"))
import evaluator_review as ev  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


req = urllib.request.Request("https://api.inference.wandb.ai/v1/models",
                             headers={"Authorization": "Bearer " + os.environ["DEEPSEEK_V4_FLASH_WANDB"]})
with urllib.request.urlopen(req, timeout=20) as r:
    ids = {m["id"] for m in json.load(r)["data"]}
if "deepseek-ai/DeepSeek-V4.1-Flash-1017" not in ids:
    sys.exit("ABORT: model not listed")
print("re-probe ok")
sc = load(REPO / "bin/agents/seat_contracts.py", "seat_contracts")
outer = load(REPO / "bin/agents/metaresearch-outer/program.py", "outer_program")
sg = load(REPO / "bin/agents/spend_guard.py", "spend_guard")
guard = sg.SpendGuard()
digest = sc.evaluator_digest([SB / "verifier/evaluator_review.py"])
before = 3.0
diff = ev.diff_text()
FENCE = "```"
prompt = f"""You are the outer-seat reviewer (Biafra): a stern, specific, evidence-first thesis adviser.

CONTEXT. A pair redesigned the launch path of `live_cycle` after a code review. The inner seat wrote the pure
decision table `_launch_decision` (kept, 7 failed cases to 0). The operator then hand-wrote the lifecycle:
`argv` built before any budget reservation, and a try/finally that guarantees the reservation ends settled or
released on every exit including an interrupt. The spend guard is now mandatory. Tests were written first.

THE DIFF UNDER REVIEW (git diff against the pushed branch, one file):
{FENCE}diff
{diff}
{FENCE}

TASK. Find real defects that remain, in this diff only. Think about: a reservation left open on some exit;
a path where a request is sent but never settled; double settle or double release; the marker claimed with
nothing recorded; an exception escaping `_settle`; behaviour that changed silently for callers.
Do not praise. Do not invent code you were not shown. Each finding must name an identifier that appears in the
diff and give a concrete reproducing input or call sequence.

OUTPUT FORMAT (a fixed evaluator checks it): at most 3 lines, each exactly
FINDING <n>: <identifier>: <what is wrong and the reproducing input>
then exactly one final line `VERDICT: ready` or `VERDICT: not-ready`. If you find nothing, write only the
VERDICT line. No other text. Do not call tools, edit files or run commands."""
result = outer.run_live(
    "harden", prompt, SB / "turn5-outer-log", ev.evaluate_answer, before,
    artifact="search-rule", evaluator_digest=digest,
    hypothesis="Review the redesigned live_cycle launch lifecycle for remaining defects",
    metric_name="review_format_violations", effort="high", spend_guard=guard,
    ledger_path=SB / "turn5-ledger.jsonl",
)
(SB / "turn5-outer-answer.txt").write_text(result.get("answer") or "")
(SB / "turn5-outer-result.json").write_text(json.dumps({k: v for k, v in result.items() if k != "answer"}, indent=2, default=str))
d = result.get("detail") or {}
print("ok:", result["ok"], "reason:", result.get("reason"), "decision:", result.get("decision"))
print("violations:", d.get("violations"), "| verdict:", d.get("verdict"))
print("spend:", result.get("estimated_usd"))
