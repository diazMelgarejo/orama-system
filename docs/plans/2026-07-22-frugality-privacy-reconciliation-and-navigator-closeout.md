# Frugality/Privacy Reconciliation + Navigator Close-Out — Provisional Plan

**Date:** 2026-07-22
**Status:** PROVISIONAL — captures everything /autoplan's review of
`docs/plans/2026-07-22-p4-skill-trimming-p3-frugality-wiring.md` deferred,
plus the remaining open items in
`references/tiered-model-implementation-navigator.md`, so nothing found
today gets lost. Not yet executed — this is the "close all loose ends"
plan the user asked for after the Eng-phase scope revision.

**What already shipped today (not in this plan's scope — done):**
- P4: `mcp-orchestration/SKILL.md` (866→496 lines) and
  `fable5-tier-based-routing/SKILL.md` (795→499 lines) trimmed, content
  bundled into `references/`/`examples/`, both under the collision guard,
  both verified with zero orphaned pointers.
- P3 (safe additive slice only): `Perpetua-Tools/orchestrator/model_registry.py`'s
  `ModelTarget` dataclass gained an optional `frugality_tier: Optional[int] = None`
  field, read from `models.yml`'s `frugality_tier` key when present. Zero
  behavior change — nothing reads or filters on it yet. This unblocks Item 1
  below without requiring the full reconciliation first.
- `fable5-tier-based-routing/references/deployment-validation.md` corrected
  to state plainly that `resolve_route()` has zero real callers today (was
  previously silent on this, which is exactly the kind of doc-without-
  enforcement gap the CEO phase flagged).

---

## Item 1 — Frugality/Privacy Reconciliation (the deferred core of P3)

**Why this is its own item, not a quick follow-up:** the Eng phase found
three unreconciled implementations of "privacy_critical" routing (verified
by reading the real code, not assumed):
1. `orchestrator/frugality_router.py`'s `spec.privacy_critical` + `max_allowed_tier()`
2. `config/routing.yml`'s task_type-based cloud-role exclusion (no flag)
3. `src/perpetua_tools/orchestrator.py`'s own `req.privacy_critical` → Oramasys/LMStudio chain

### Design questions to resolve before any more code lands

- Which of the three is canonical? Codex's "single policy gate" proposal
  (classify every call target into a canonical policy record; every
  dispatch path asks the gate before the call, not just before building a
  fallback chain) is the strongest option surfaced so far — needs a real
  design doc, not a plan-file paragraph.
- `route_task(task_type, preferred_device)`'s signature cannot accept
  `privacy_critical`/`est_tokens`/`escalation_reason` — does the API shape
  change, or does the gate live outside `route_task()` entirely (e.g. a
  wrapper both `route_task()` and `/orchestrate` call before dispatch)?
- Does `resolve_route()` become the single gate, or get retired in favor of
  extending the existing `routing.yml` task_type-exclusion system? (Codex
  leaned toward the former; not yet decided.)
- `ModelTarget.frugality_tier` now exists (shipped today) but is unpopulated
  in `models.yml` — who owns backfilling it per-model, and what's the
  fallback for models without a tier set?

### Suggested execution shape (once design is settled)

1. Baseline (per the amended B3.1 from the CEO phase): capture current
   `route_task()` output and `/orchestrate` routing decisions for a
   representative set of task_types before any change.
2. Land the chosen gate architecture as its own PR, with the API-shape
   change (if any) called out explicitly in the PR description — not
   folded silently into a "wiring" commit.
3. Populate `frugality_tier` in `models.yml` for at least the models used
   by the baseline's task_types.
4. Contract tests: `ORAMASYS_OFFLINE=1` never returns paid/remote from
   whichever path becomes canonical; `privacy_critical` never escalates
   past local tiers from whichever path becomes canonical — Eng phase
   flagged the CURRENT code already lets `privacy_critical` reach tier 3,
   which may or may not be the intended final semantics — decide explicitly,
   don't inherit by accident.
5. Re-diff against the Item 1 baseline; both orama-system's
   `fable5-tier-based-routing/references/deployment-validation.md` wiring-
   gap note and this plan's own status get updated once real callers exist.

---

## Item 2 — Remaining navigator loose ends (from `references/tiered-model-implementation-navigator.md`)

Captured here so the navigator's own "pending" items don't scatter across
multiple follow-up conversations.

| Item | Current status (verified today where checked) | Next action |
|---|---|---|
| P2 — v2 repo scaffold depth | `github.com/oramasys/oramasys` confirmed to exist (HTTP 200); actual content depth NOT audited today | Clone and audit, or explicitly mark "not yet needed" if v1.1 work continues to suffice |
| `docs/2026-05-31-tri-repo-alignment-completion-plan.md` | Marked `🔄 active` in the 2026-06-14 completion tracker; not re-checked today | Re-verify current status before assuming still active — trackers this session have repeatedly been found stale |
| Periscope L4 integration | Marked `⏭️ deferred`, tracker's own words: "the only plan with real remaining implementation grunt" | Out of scope for this close-out; explicitly still deferred, not silently dropped |
| `mcp-orchestration`/`fable5-tier-based-routing` global-publish status | Not checked whether either syncs to `~/.claude/skills/` via `scripts/install-skills.sh` | Run `bash scripts/install-skills.sh` after this session's trim lands; confirm collision guard passes for both names (already verified clear today) |

---

## Explicit non-goals (name them, don't silently absorb)

- This plan does NOT commit to a timeline for Item 1 — the design
  questions need a human decision (likely another CEO/Eng review pass once
  the "single policy gate" proposal has an actual design doc to review).
- This plan does NOT re-open Periscope L4 or the tri-repo alignment plan —
  both stay in their own tracked status, referenced here only so this
  close-out doesn't accidentally imply they're resolved.
- This plan does NOT populate `models.yml`'s new `frugality_tier` field for
  any model yet — that's Item 1 step 3, gated on the design decision.
