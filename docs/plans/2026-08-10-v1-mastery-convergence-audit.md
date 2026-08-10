# v1 ORAMASYS-MASTERY P0-P2 Convergence Audit

**Date:** 2026-08-10  
**Stack:** PR2, based directly on PR1 (`feat/v1-mcp-first-run-readiness`)  
**Source plan:** `docs/v2/29-oramasys-mastery-implementation-plan.md`  
**Human reference:** `docs/v2/references/ORAMASYS-MASTERY-v3.md`

## Decision

Do not replay the historical implementation plan literally against the newer v1 tree.
Use its governing principles instead:

- zero duplication;
- minimal diff;
- current spine prevails;
- human-facing mastery and agent-facing runtime remain separate;
- P3 remains untouched.

## Verified current state

| Layer | Result | Canonical v1 home |
|---|---|---|
| P0 agent-methodology wrapper | Already satisfied | `.claude/skills/agent-methodology/SKILL.md` |
| M1 Spec Contract | Already materialized | `bin/orama-system/SKILL.md` |
| M2 Amplifier Objective Tree | Already materialized | `bin/orama-system/SKILL.md` + `references/amplifier-principle.md` |
| M3 Collaborative Reasoning Safety | Already materialized | `references/collaborative-reasoning-safety.md` |
| M4 Output Discipline | Already materialized | `bin/orama-system/SKILL.md` Stage 5 output shape |
| M5 Lessons Architecture | Already materialized as an architecture | root `SKILL.md`, `docs/LESSONS.md`, `scripts/capture_lesson.py`, lessons template |
| M6 Communication Guidelines | Already materialized | `references/communication-guidelines.md` |

The two §3 reference files already exist and contain the required semantics. Recreating them would violate the plan's own zero-duplication rule.

## What this PR adds

1. `bin/orama-system/references/mastery-runtime-map.md`
   - one pointer-only ownership map for M1-M6;
   - no copied M3/M5/M6 prose;
   - explicit P3 no-touch boundary.
2. `scripts/verify_mastery_convergence.py`
   - executable ownership/semantic gate;
   - checks P0 thin-wrapper status;
   - checks M1-M6 canonical contracts;
   - checks the human mastery reference exists;
   - fails if representative P3 scaffold paths appear.
3. `tests/test_mastery_convergence.py`
   - makes the convergence contract part of normal test discovery.

## Why this is stronger than the historical patch

The original plan described roughly 50 lines to add because M1-M6 were missing in June 2026. By August 2026, most of those semantics already exist. Re-adding the historical text would create parallel versions and future drift.

The stronger current solution is to verify canonical ownership and preserve one source of truth per concern.

## P3 hard boundary

This PR does not create or modify:

- the v2 flat repository scaffold;
- `skills/prompt-engineering/SKILL.md`;
- `skills/spec-contract/SKILL.md`;
- v2 `core/frugality_router.py`;
- `.github/workflows/mastery-eval.yml`;
- any new v2-only §5c skill.

## Verification

```bash
python3 scripts/verify_mastery_convergence.py
python -m pytest -q tests/test_mastery_convergence.py
```

Expected gate output:

```text
OK: ORAMASYS mastery v3 is materialized in v1 through P2; P3 untouched
```

## Migration gate

P3/v2 topology work remains blocked until PR1, this PR2, and the Perpetua-Tools P4 closure are merged and the cross-repo acceptance matrix is green.
