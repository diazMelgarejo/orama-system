"""Fixed evaluator for the outer seat's review turn: is the review well-formed and grounded in the diff?

metric = format violations (lower is better). A review is well-formed when it has at most 3 lines of the
form `FINDING <n>: <identifier>: <what, with a reproducing input>` where <identifier> occurs in the diff
shown to her, and exactly one `VERDICT: ready` or `VERDICT: not-ready` line. Content is vetted by the
operator-side reviewer by reproduction, not by this evaluator. Neither seat may edit this file.
"""
import os
import re
import subprocess
from pathlib import Path

REPO = Path(os.environ.get("ORAMA_REPO", Path.cwd()))


def diff_text():
    return subprocess.run(
        ["git", "diff", "-U2", "origin/2026-11-17-001-biafra-seat-canonical", "--", "bin/agents/biafra_cycle.py"],
        cwd=REPO, capture_output=True, text=True, check=False, timeout=30,
    ).stdout


def evaluate_answer(answer):
    diff = diff_text()
    violations = []
    findings = re.findall(r"^FINDING (\d): ([\w./]+): (.{15,})$", answer or "", flags=re.M)
    loose = re.findall(r"^FINDING\b.*$", answer or "", flags=re.M)
    if len(loose) != len(findings):
        violations.append("malformed FINDING line")
    if len(findings) > 3:
        violations.append("more than 3 findings")
    for _, where, _ in findings:
        if where.split(".")[-1].split("/")[-1] not in diff:
            violations.append(f"ungrounded identifier {where}")
    verdicts = re.findall(r"^VERDICT: (ready|not-ready)$", answer or "", flags=re.M)
    if len(verdicts) != 1:
        violations.append("need exactly one VERDICT line")
    return {"metric_after": float(len(violations)), "detail": {"violations": violations, "findings": findings,
                                                              "verdict": verdicts}}
