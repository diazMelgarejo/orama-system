# Cross-Repo Out-of-Scope Closure — Plan Register Resolution

**Date:** 2026-07-22
**Status:** ACTIVE — closure ledger, partially executed same session
**Scope:** every item in `references/tiered-model-implementation-navigator.md`
§ "Cross-Repo Plan Register" — the plans flagged as "not topically related
to frugality/privacy" while tracing the P3 reconciliation trail, deliberately
kept out of `docs/plans/2026-07-22-frugality-privacy-reconciliation-and-
navigator-closeout.md`'s scope. This plan closes the loop on those instead
of leaving them scattered.

**Governing directive (user, 2026-07-22, same session):** "all unimplemented
or ambiguous parts of the plans will be implemented in v2 oramasys repos
AFTER migration, nothing holds us back but we implement everything we can
now." Applied below as the disposition rule: concrete, unblocked,
low-risk items get implemented now; genuinely ambiguous or blocked items
get explicitly deferred to v2 with the blocking reason named — never left
as silently-stale "active."

**Methodology reused, not reinvented:** PT's own
`Perpetua-Tools/docs/references/phase0-and-orama-open-work-closure-plan-
2026-07-18.md` already defines the right frame — every open/ambiguous doc
resolves to exactly one of four honest states: (1) implemented and
verified, (2) superseded with a pointer, (3) deliberately deferred with
owner/trigger/gate, or (4) retired with recorded rationale. Applied here.

---

## Closure Ledger

| # | Document | Repo | Disposition | Evidence / Reason |
|---|---|---|---|---|
| 1 | `docs/plans/2026-06-14-plan-completion-tracker.md` | orama | **(2) Superseded** | Its own "COMPLETE" banner is stale — this plan + the navigator are now the live index for anything it used to track. No further action; not deleting (historical record). |
| 2 | `docs/plans/2026-06-24-optimization-priorities.md` — L6 schemas | orama | **(3) Deferred to v2** | Concrete deliverable (`schemas/topology.schema.json` + `devices.schema.json` + `skills.schema.json`) but is net-new authoring work, not a verification/wiring task — genuinely new scope, not "ambiguous," but also not "implementable in five minutes." Owner: whoever picks up v2 schema work. Trigger: v2 oramasys repo bootstrap. |
| 2b | same doc — Periscope L4 integration | orama | **(3) Deferred to v2** | Doc's own words: "52 open items, separate session." Explicitly out of scope here; already flagged deferred by its own tracker, not silently dropped. |
| 3 | `docs/plans/2026-07-14-orama-housecleaning-leftovers-next-steps.md` | orama | **(1) Implemented/verified (partial) + (3) deferred (rest)** | See "Housecleaning Leftovers — Resolved Today" below. |
| 4 | `docs/plans/2026-07-06-orama-skill-upgrade-roadmap.md` — PR1/PR2 | orama | **(1) Implemented and verified** | PR1 shipped; PR2 ("Low-Risk Skills") confirmed squash-merged to main via `0a4ebc9c docs(skills): PR2 low-risk skill standardization + gstack/glm52/whatsapp additions (#142)` (verified during this session's branch-cleanup audit). |
| 4b | same doc — PR3 (Medium-Risk Doctrine/Review), PR4 (Elevated-Risk Operational), PR5 (High-Risk Planning-Only) | orama | **(3) Deferred to v2** | Escalating-risk-tier skill changes by the roadmap's own design — PR4/PR5 explicitly touch operational and planning-only skills where this session already had one real collision incident (skillify/gstack) from moving too fast on skill changes. Deferring the higher-risk tiers to v2, with a clean migration, is lower-risk than rushing them now. |
| 5 | `Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md` | PT | **(1) Implemented (item #1) + (2) superseded (stale gap text) + (3) deferred (items #2/#3/#8)** | Already executed this session — see PT commit `4bf12868`: item #1 (local-agents + alphaclaw-mcp Gate 2 tests) confirmed 22/22 + 6/6 passing after `npm install`; stale "openclaw_config missing" paragraph corrected (code already carries it, per item #7 and live `control_plane.py:76` / `alphaclaw_manager.py:118,398`); items #2/#3/#8 marked deferred to v2 with named blocking reasons (sequencing dependency, architectural ambiguity, blocked-on-#3 respectively). |
| 6 | `Perpetua-Tools/docs/references/phase0-and-orama-open-work-closure-plan-2026-07-18.md` | PT | **(2) Superseded (methodology) + (3) deferred (content)** | Its own Gate 0 ledger was never executed ("planning handoff; no implementation or merge authorized by this file"). This closure plan adopts its four-state methodology directly rather than re-deriving one; the actual per-document ledger work it called for is what *this* table now does, scoped to the items this session's trail actually touched. Full companion 29-document audit it references is **not** re-run here — deferred to v2, genuinely large scope, would need its own dedicated pass. |
| 7 | `Perpetua-Tools/docs/next/2026-07-17-coordination-module-consolidation-plan.md` + review | PT | **(1) Implemented (Parts 1/1b/1c/1d) + (3) deferred (Part 2/3)** | Parts 1/1b/1c/1d confirmed squash-merged via `28c425f9 fix(coord): implement coordination-module consolidation Parts 1-1d + PR #260 review fixes (#263)` (verified during branch-cleanup audit). Part 2 stays gated: its own text requires "Phase 0F's live re-verification," and no `Phase 0F` document or artifact exists anywhere in the repo (checked: `find . -iname "*phase-0f*"` → empty) — genuinely ambiguous, not just unstarted, so it defers to v2 rather than being force-closed. Part 3 was already explicitly deferred by the plan's own text. |

---

## Housecleaning Leftovers — Resolved Today

`docs/plans/2026-07-14-orama-housecleaning-leftovers-next-steps.md`'s
review checklist and follow-up items, disposed individually:

- ✅ **"Delete or archive stale source branch `2026-07-12-001-gstack-safe-
  upgrade` after verifying no unique work remains"** — superseded by this
  session's much larger branch-hygiene audit; that specific branch was not
  in the 33-branch verified-superseded set, so it needs its own one-branch
  check before inclusion in `references/2026-07-22-branch-cleanup-
  verified-superseded.sh`. **(3) Deferred** — flag for a follow-up
  `git diff main..2026-07-12-001-gstack-safe-upgrade --stat` pass, not
  done in this session.
- **(3) Deferred to v2**, all requiring a human content judgment call, not
  a mechanical check: "Confirm Kimi independent-review guidance is still
  accurate," "Confirm gstack cross-link to Kimi... matches current review
  workflow," "Confirm shell-hygiene guidance... still wanted," "Confirm D23
  single-operator-LAN threat-model descope ADR belongs in v2 docs," "Confirm
  `docs/v2/references/patterns/README.md` is the desired home," "Confirm
  SECURITY.md case study... acceptable," "Confirm STM high-peer-count
  latency benchmark remains deferred to v2.5" — every one of these is a
  "does this still match reality" judgment call the plan's own author
  flagged as needing confirmation, not a task with a mechanical answer;
  genuinely belongs with whoever owns the v2 docs migration, since several
  explicitly ask "does this belong in v2 docs."
- **(3) Deferred**, PT-side: "Reconcile Perpetua-Tools `vendor/ecc-tools`
  submodule drift... after checking the submodule remote contains the
  referenced commit" — not checked this session, separate PT
  issue/branch per the item's own text.
- **(4) Retired**: "Consider a later docs index pass if reviewers want
  these leftover docs linked from a single landing page" — this closure
  plan + the navigator now serve that role; a separate landing page is
  redundant.

---

## What This Plan Does Not Cover

- The companion 29-document closure audit referenced by PT's
  `phase0-and-orama-open-work-closure-plan-2026-07-18.md` — not located or
  re-run; if it exists elsewhere, a future session should find and
  reconcile it against this ledger rather than starting a third parallel
  tracker.
- Any plan not already surfaced in the navigator's Cross-Repo Plan
  Register — this closure plan resolves exactly that list, not a fresh
  full-repo sweep. A genuinely exhaustive sweep of every `docs/plans/*.md`
  in both repos is itself the kind of large, well-defined-but-unstarted
  task that belongs in v2 per the governing directive, not bolted onto
  this pass.

---

**Cross-references:** `references/tiered-model-implementation-navigator.md`
§ "Cross-Repo Plan Register" (source list) · `docs/plans/2026-07-22-
frugality-privacy-reconciliation-and-navigator-closeout.md` (sibling plan,
frugality/privacy scope only) · `Perpetua-Tools/docs/2026-05-31-tri-repo-
alignment-completion-plan.md` (PT commit `4bf12868`) ·
`Perpetua-Tools/docs/next/2026-07-17-coordination-module-consolidation-
plan.md` (Parts 1-1d landed via `28c425f9`).
