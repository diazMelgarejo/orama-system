# Reconciliation Plan — OSSF-1 Saga → 2026-09-12 v2 Skill Construction Guide

**Status:** applied 2026-09-16 (operator-directed harmonization). /PLAN origin;
§3 edits landed in `2026-09-12-v2-skill-construction-guide.md`.
**Convergence target:** `2026-09-12-v2-skill-construction-guide.md`
(informative hub) + **OSSF draft suite** (normative target):
[`2026-09-16-ossf-part0-introduction.md`](2026-09-16-ossf-part0-introduction.md).
Foundation = **Open Standard Skill Format (core)** (Part 1). Composable atoms
use **OSSF (Atomic Skill Card Format Extension)** (Part 2). Composites use
core + Part 3 only.
**Sources reconciled:** OSSF-1 saga (PT internal saga record, 2026-08-07 —
fusion inventory, pilot wave, pre-commit enforcement; not a public path,
cited by date and description rather than workspace-local location) +
construction guide + doc 44 + doc 46 + skillify authoring references.

## 1. Lineage declaration (additive — names the chain, retires nothing)

OSSF-1 (2026-08-07, machine-checkable subset: frontmatter + Boundaries
body + ≤500 lines, enforced by `scripts/hooks/check_ossf1_skill_md.py`)
→ doc 44 "planning baseline" (folder shape, ≤200/≤500 size policy, dry-run
rule, acceptance criteria) → **Open Standard Skill Format (core)** (Part 1)
→ **OSSF (Atomic Skill Card Format Extension)** (Part 2, `composable-atom`
profile only) → **composite consumer profile** (Part 3). Earlier working
names "Oramasys Standard Skill Format" / "Oramasys Atomic Skill Card Format"
are renamed to **OSSF** for vendor-neutral publication. Nothing from the
OSSF-1 implementation draft is dropped; core Part 1 inherits it wholesale.

## 2. Concrete gaps found in the construction guide (all OSSF-1 requirements the guide omitted)

1. **Mandatory `## Boundaries` body section** with the three subsections
   `### Always Do` / `### Ask First` / `### Never Do` — OSSF-1's core
   enforcement and the exact thing the pre-commit gate checks. The guide's
   S4 card template omits the body structure entirely.
2. **`description` minimum length ≥20 chars** (OSSF-1 floor; the guide only
   carries the ≤1,536 listing cap).
3. **`agent_compatibility` as an accepted alternative to `compatibility`**
   (overlay cards per OSSF-1).
4. **Gate continuity rule:** one validator only. The Wave-1 boundary lint
   and format contract tests must extend
   `scripts/hooks/check_ossf1_skill_md.py` (or supersede it wholesale with
   the OSSF-1 checks as a subset of the new validator) — never a second
   parallel implementation (same lesson as the namespace-collision script).

## 3. Applied edits to the construction guide (on approval)

- S4: add the mandatory body structure — `## Purpose` (or `## When to
  Use`), then `## Boundaries` with the three OSSF-1 subsections, as
  required card sections for every altitude (A/B/C).
- S4: add `description` floor ≥20 chars; note `agent_compatibility` as the
  overlay-card alternative to `compatibility`.
- S4/S9: point to **OSSF (core)** Part 1 and **OSSF (Atomic Skill Card Format
  Extension)** Part 2; single-validator rule (Part 4).
- S9: manifest contract tests inherit the OSSF-1 checks as a subset
  (frontmatter + Boundaries + ≤500 lines are prerequisites of the new
  lint, not competitors to it).
- S10: add the OSSF-1 saga to the source list with its evidence anchors
  (commits `9fb770fd`/`e5e2cc51`/`a04de3a6`, PT `lesson_adda4d2b02c3`).

## 4. Saga open-items disposition (updated by this reconciliation)

- ~~"Promote OSSF-1 from hook docstring to docs/v2 decision record"~~ →
  RESOLVED by OSSF draft suite Parts 1–4 (2026-09-16); alexandria ratification
  remains the formal publication gate.
- "Expand hook to `.agents/` mirrors after v2 cutover" → SUPERSEDED: v2
  cutover happened; Kungfu's contract-test lint replaces per-mirror hooks.
- "PT P2 wrappers" → still open, routed through the Kungfu manifest
  (Wave 2 adapters), not the hook.
- "Re-anchor AlphaClaw faf894f2" → unchanged, still optional/operator.

## 5. Execution order

1. ✅ Apply §3 edits to the construction guide (2026-09-16).
2. ✅ Post completion note to the coordination board (compact lineage).
3. ✅ Leave the OSSF-1 saga file untouched (append-only memory discipline);
   disposition lives in this plan + construction guide §0 lineage + board log.
4. No push, no repo creation, no Wave-0 manifest work — those wait on the
   kungfu bootstrap gate and pending human reviews.

## 6. Harmonized standard (one sentence)

**Open Standard Skill Format (core)** = Part 1 normative draft; **OSSF (Atomic
Skill Card Format Extension)** = Part 2 optional profile for composable atoms;
composite consumers = Part 1 + Part 3 only — suite index
[`2026-09-16-ossf-part0-introduction.md`](2026-09-16-ossf-part0-introduction.md);
onboarding hub remains
[`2026-09-12-v2-skill-construction-guide.md`](2026-09-12-v2-skill-construction-guide.md).
