#!/usr/bin/env python3
"""
oramasys_trigger_eval.py — AC8 harness for the oramasys-method skill.

Parses trigger phrases from the real SKILL.md description and runs a
fixed eval set. Used by GOAL.md AC8 and CI.

Exit 0 if Precision == 1.00 and Recall >= 0.90.
Exit 1 otherwise (prints failing cases).

Usage:
    python scripts/eval/oramasys_trigger_eval.py
"""
import pathlib
import re
import sys

SKILL_PATH = pathlib.Path(__file__).parents[2] / \
    "bin/orama-system/skills/oramasys-method/SKILL.md"

EVAL = [
    # positives
    {"id": "pos-ultrathink",  "exp": True,  "q": "ultrathink this: refactor the auth module"},
    {"id": "pos-legacy",      "exp": True,  "q": "ultrathink harder on the caching strategy"},
    {"id": "pos-oramasys",    "exp": True,  "q": "apply oramasys to design the pipeline"},
    {"id": "pos-deep",        "exp": True,  "q": "think deeply, give me a systematic approach to this migration"},
    {"id": "pos-arch",        "exp": True,  "q": "rigorous multi-step plan for re-architecting the orchestrator"},
    {"id": "pos-overhaul",    "exp": True,  "q": "plan a complete overhaul of our deployment pipeline"},
    {"id": "pos-ipso",        "exp": True,  "q": "improve orama-system using the oramasys-method skill, eat our own dog food"},
    # hard negatives
    {"id": "neg-trivial",     "exp": False, "q": "what time is it in Tokyo?"},
    {"id": "neg-lookup",      "exp": False, "q": "read this PDF and tell me the title"},
    {"id": "neg-chitchat",    "exp": False, "q": "thanks, that worked great!"},
    {"id": "neg-format",      "exp": False, "q": "convert this CSV to JSON"},
]

PHRASES = [
    "ultrathink", "oramasys", "think deeply", "5-stage", "systematic approach",
    "multi-step", "re-architect", "architecture", "refactor", "overhaul",
    "rigorous", "design-heavy", "non-trivial", "problem solving", "plan",
]

def load_triggers():
    text = SKILL_PATH.read_text()
    desc = load_frontmatter_description(text).lower()
    return [p for p in PHRASES if p in desc]

def load_frontmatter_description(text):
    """Extract a folded YAML frontmatter description without a PyYAML dependency."""
    match = re.search(r"^description:\s*>-\s*\n(?P<body>(?:[ \t]+.*\n)+)", text, re.MULTILINE)
    if match:
        return " ".join(line.strip() for line in match.group("body").splitlines())
    match = re.search(r'^description:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    if match:
        return match.group(1)
    raise SystemExit(f"description not found in {SKILL_PATH}")

def fires(q, trigger_phrases):
    ql = q.lower()
    hit = any(ph in ql for ph in trigger_phrases)
    # Substantive = long enough OR contains any methodological intent keyword.
    # 7-word threshold covers short-but-dense queries like
    # "rigorous multi-step plan for re-architecting the orchestrator" (7 words).
    INTENT = ["ultrathink", "oramasys", "5-stage", "multi-step", "re-architect",
              "overhaul", "refactor", "rigorous", "architecture", "systematic"]
    substantive = len(ql.split()) >= 7 or any(x in ql for x in INTENT)
    return hit and substantive

def main():
    trigger_phrases = load_triggers()
    tp = fp = tn = fn = 0
    failures = []
    for c in EVAL:
        f = fires(c["q"], trigger_phrases)
        ok = f == c["exp"]
        if f and c["exp"]: tp += 1
        elif f and not c["exp"]: fp += 1
        elif not f and not c["exp"]: tn += 1
        else: fn += 1
        if not ok:
            failures.append(f"  FAIL [{c['id']}]: expected={c['exp']} fired={f}")

    total = len(EVAL)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    accuracy = (tp + tn) / total

    print(f"Accuracy:  {tp+tn}/{total} = {100*accuracy:.0f}%")
    print(f"Precision: {precision:.2f}  Recall: {recall:.2f}")
    if failures:
        print("Failures:")
        for f in failures:
            print(f)
    passed = precision == 1.00 and recall >= 0.90
    if passed:
        print("AC8 PASS")
    else:
        print(f"AC8 FAIL — precision={precision:.2f} recall={recall:.2f} (need P=1.00 R>=0.90)")
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
