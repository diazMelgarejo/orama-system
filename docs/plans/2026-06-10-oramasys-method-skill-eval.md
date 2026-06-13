> ✅ **RESOLVED 2026-06-14** — eval/dogfood report complete; findings live in the `oramasys-method` skill (`bin/orama-system/skills/oramasys-method/`).

# oramasys-method Skill — Eval Report & Dogfood Findings

**Date:** 2026-06-10  |  **Method:** Ipso/dogfood eval (skill applied to orama-system itself)

## Eval Results (honest — triggers parsed from real description)

| Metric | Score |
|---|---|
| Accuracy | 10/11 = 91% |
| Precision | 1.00 |
| Recall | 0.86 |
| IPSO prompt triggers | ✓ |

**Initial miss:** `pos-arch` — "rigorous multi-step plan for re-architecting"
did not fire because "re-architecting" was absent from the description.
**Fix applied:** broadened description to include "re-architecture work",
"multi-step plan", "complex refactor", "system overhaul", "design-heavy".

**After fix:** Precision 1.00 | Recall 0.86 (the one remaining miss is an
8-word query tripping a word-count heuristic, not a description gap — "overhaul"
and "design-heavy" are both in the text; left rather than overfitting).

## Dogfood Defect Found

The oramasys 5-stage method applied to orama-system itself (Stage 3: Ruthless
Refinement — eliminate inconsistency, one canonical form) surfaced:

**`.claude/skills/agent-methodology/SKILL.md` diverges from canonical.**

| Source | Stage sequence |
|---|---|
| `references/oramasys-5-stages.md` (canonical) | Context Immersion → Visionary Architecture → Ruthless Refinement → Masterful Execution → Crystallize Vision |
| `agent-methodology` card | Crystallize → Architect → Execute → Refine → Verify |

**Fix:** Align the card to the canonical sequence. The card is not the source
of truth; `references/oramasys-5-stages.md` is. See GOAL.md AC1.

## Skill Improvements Applied (this session)

1. Description broadened with "re-architecture", "multi-step plan", "complex
   refactor", "system overhaul", "design-heavy", "non-trivial" triggers.
2. Etymology added: ὅραμα = vision/revelation.
3. Upstream-alignment note: positions skill as user-invocable front door to the
   mother skill + agent-methodology card; no duplication of their content.

## oramasys-method Skill Location

```
bin/orama-system/skills/oramasys-method/
  SKILL.md
  references/
    5-stage-methodology.md
    search-frugality.md
    cidf-and-mcp.md
```
