# docs/next/ — Index

**Added 2026-07-22** as part of the v1→v2 transition close-out. This
directory holds forward-looking analysis/design docs that predate a formal
plan file. Not all have been re-verified against current `main` — statuses
below are each doc's own self-reported status as of 2026-07-22, not a fresh
audit, unless marked "re-verified."

**Penultimate master plan (2026-07-27):**
[`2026-07-27-phase-0-master-plan.md`](2026-07-27-phase-0-master-plan.md)
→ canonical PT
[`PHASE-0-MASTER-PLAN-2026-07-27.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PHASE-0-MASTER-PLAN-2026-07-27.md).
Supersedes `2026-07-25-pending-work-tracker.md` and stale docs-scan HEAD.

**Coordination Phase 0F (PT):** [`2026-07-27-coordination-phase-0f-pointer.md`](2026-07-27-coordination-phase-0f-pointer.md)
→ PT autoplan
[`2026-07-27-coordination-phase-0f-part2-autoplan.plan.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/next/2026-07-27-coordination-phase-0f-part2-autoplan.plan.md)
(≠ STM Phase 0).

**v1→v2 closure entry points** (start here for "what's the overall status
of open work across both repos"):
- `../plans/2026-07-22-cross-repo-out-of-scope-closure.md` — closure ledger
  for every plan flagged as not directly frugality/privacy-related during
  this session's P3 trace; four-state disposition (implemented / superseded
  / deferred-to-v2 / retired) for each.
- `../../references/tiered-model-implementation-navigator.md` — the
  overarching index this closure work traces back to.
- `../plans/2026-07-22-frugality-privacy-reconciliation-and-navigator-closeout.md`
  — the sibling plan for the frugality/privacy-specific thread.

## Contents

| Doc | Topic | Status (as of 2026-07-27) |
|---|---|---|
| `2026-07-27-coordination-phase-0f-pointer.md` | PT coordination Phase 0F + autoplan pointer | **New** — links PT `docs/coordination/` and autoplan plan |
| `2026-07-27-phase-0-master-plan.md` | STM/swarm pre-v2 pointer | Links PT `PHASE-0-MASTER-PLAN-2026-07-27.md` |
| `2026-07-25-pending-work-tracker.md` | Cross-repo pending-work tracker | **Updated** — identity Phases 1–2 merged (#220); PT TLS #276/#278 merged |
| `2026-07-17-pr166-pr169-git-recovery-analysis.md` | Git recovery analysis for PR #166/#169 | Analysis and next moves only; no branch rewrite or merge performed |
| `2026-07-17-preserve-branch-pr-cleanup-plan.md` | Branch preservation before cleanup | Plan only, not executed — review before any deletion |
| `preserve-branch-manifest.md` | Manifest of 27 branches evaluated for preservation | Phase 1 complete 2026-07-17 |
| `fleet-mesh/` (5 docs + README) | GossipBus / OASN P2P mesh, G7 async notifications, self-healing degradation modes | See `fleet-mesh/README.md` — not re-audited this pass |
| `2026-07-24-plan-unified-identity-audit.md` | Consolidate 3 separate git-identity allowlists into one JSON config + one engine | **Phases 1-2 SHIPPED** (orama PR **#220** merged). Phases 3-4 (PT sync + stale list removal) still open. |

Everything in this table (and `fleet-mesh/`) is **out of scope** for the
2026-07-22 frugality/privacy and cross-repo-closure work — none were
topically related, none were re-verified this session. Listed here purely
as a navigation index so a future session doesn't have to rediscover what's
in this directory from scratch. If you pick one up, re-verify its status
against current `main` before trusting the table above — the whole point
of the closure ledger this session produced is that self-reported status
in a doc header decays fast.
