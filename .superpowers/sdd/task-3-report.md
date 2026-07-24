# LLM-Council Task 3 Report — fable5-tier-based-routing update

**Status:** DONE (with two brief-asserted checks honestly marked absent)
**Commit:** 8d66fdfc (branch `2026-07-19-002-fleet-mesh-oob-fixes`)
**Date:** 2026-07-19

## What was done

- The skill already existed at 499 lines (hard ceiling ≤500 per
  retiring-fellow authoring rules), with a `references/` dir and a
  "Further Reading" router — so Task 3 was executed as an ADDITIVE
  reference, not a rewrite:
  `bin/orama-system/skills/fable5-tier-based-routing/references/operational-fallback-chain.md`
- That reference documents the brief's mandatory 4-tier operational chain
  (Ollama → Win LM Studio [SKIP if offline] → GLM-5.2 BigModel → Sonnet 5
  Medium, no fallback past Tier 4) as a vocabulary DISTINCT from the
  skill's existing code-grounded routing tiers (Local OSS → gbrain/CRG →
  HF Free → Proprietary Free). Both are real; conflating them was the
  latent doc bug this task actually needed to fix.
- All invariants restated verbatim: hard 10s killable-background timeout,
  NEVER `timeout N && cmd`, cost gate raises on deny, escalation_reason
  tracked, the three escalation triggers.

## Test / verification results

- Step-1 fact-check against PT `orchestrator/frugality_router.py`:
  - `_enforce_tier_policy` — EXISTS (line 94; call sites 174/242/251). ✓
  - `TIER_PROBE_TIMEOUT_S = 10.0` — **DOES NOT EXIST** anywhere in PT
    `orchestrator/` (`grep -rn TIER_PROBE_TIMEOUT` = empty). Recorded as
    absent in the reference; NOT fabricated into docs.
  - `cost_guard` integration in frugality_router — **NOT PRESENT** (module
    imports `backend_resolver`). Recorded as absent.
- Step-3 tier-progression testing: not executable as specified — the
  timeout/cost-gate constants the brief names don't exist in code to test
  against. The doctrine-level invariants are covered by the skill's
  existing `references/python-timeout-pattern.md` and the new reference's
  re-verification command.

## Concerns

1. The task brief contains stale/aspirational code facts (the two absences
   above). Whoever regenerates these council task briefs should re-ground
   them against current code first — see discrepancy D4 in
   `docs/next/fleet-mesh/2026-07-19-oob-completion-findings.md`.
2. SKILL.md is AT the 500-line ceiling; any future inline edits must trim
   or offload to references first.
