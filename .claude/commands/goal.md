---
name: goal
description: Load and continue working the active GOAL.md. Re-reads the goal, runs the baseline scan, checks which ACs pass, and iterates until all 10 are green.
---

# /goal — Continue Working Toward GOAL.md Completion

This command wires the active GOAL.md into your session.

## Steps (run immediately, in order)

```bash
# 1. Read the goal
cat GOAL.md

# 2. Run the baseline scan
grep -rn "ultrathink" \
  --include="*.py" --include="*.json" --include="SKILL.md" \
  --include="*.sh" --include="*.toml" \
  bin/ .claude/ .agents/ api_server.py \
  | grep -vi "legacy\|deprecated\|historical\|shim\|alias\|compat\|successor"

# 3. Run the full AC suite — see which pass today
echo "=== AC1 ===" && \
for s in "Context Immersion" "Visionary Architecture" "Ruthless Refinement" \
         "Masterful Execution" "Crystallize Vision"; do
  grep -q "$s" .claude/skills/agent-methodology/SKILL.md \
    || { echo "MISSING: $s"; break; }
done && echo "AC1 PASS"

echo "=== AC2 ===" && \
test ! -f bin/shared/ultrathink_core.py \
  && test -f bin/shared/oramasys_core.py \
  && ! grep -rn "ultrathink_core" --include="*.py" bin/ \
  && echo "AC2 PASS" || echo "AC2 FAIL"

echo "=== AC3 ===" && \
! grep -rn "ultrathink-agent-network\|ultrathink multi-agent\|ultrathink-orchestrator" \
  bin/config/ bin/orama-system/config/ \
  && echo "AC3 PASS" || echo "AC3 FAIL"

echo "=== AC4 ===" && \
! grep -nP '\xc3\xa2' bin/orama-system/afrp/SKILL.md \
  && ! grep -ni "ultrathink" bin/orama-system/afrp/SKILL.md \
  && echo "AC4 PASS" || echo "AC4 FAIL"

echo "=== AC5 ===" && \
test -f bin/orama-system/references/oramasys-5-stages.md \
  && echo "AC5 PASS" || echo "AC5 FAIL"

echo "=== AC6 ===" && python -m pytest tests/ bin/orama-system/cidf/tests/ -q

echo "=== AC7 ===" && python scripts/review/repo_hygiene.py .

echo "=== AC8 ===" && python scripts/eval/oramasys_trigger_eval.py

echo "=== AC9 (PT) ===" && \
! grep -rn "ultrathink_core\|ultrathink-agent-network" \
  --include="*.py" --include="*.json" ../Perpetua-Tools/orchestrator/ \
  && echo "AC9 PASS" || echo "AC9 FAIL (check Perpetua-Tools)"

echo "=== AC10 ===" && \
grep -q "oramasys rename" .claude/lessons/LESSONS.md \
  && echo "AC10 PASS" || echo "AC10 FAIL"
```

## After running the suite

- Mark passing ACs in GOAL.md § 8 Progress Log.
- Pick the **highest-leverage failing AC** and fix it (one criterion per commit).
- Re-run the affected check, then the full gate.
- Repeat until all 10 print PASS.

## Stop condition

When all 10 pass:
1. Append a completion entry to GOAL.md § 8 Progress Log.
2. Append to `.claude/lessons/LESSONS.md`.
3. Commit: `docs(goal): GOAL COMPLETE — oramasys rename consistent`
4. Remove `§ 0` from `CLAUDE.md` and delete `GOAL.md` in the same commit.
5. Open or update the PR.
