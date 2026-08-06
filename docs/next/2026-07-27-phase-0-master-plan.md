# Phase 0 Master Plan — Orama Pointer (2026-07-27)

> **Canonical document:** Perpetua-Tools  
> [`docs/phase-0-specifications/PHASE-0-MASTER-PLAN-2026-07-27.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PHASE-0-MASTER-PLAN-2026-07-27.md)

The STM/swarm security knowledge graph lives in PT `docs/phase-0-specifications/`
with LLM-wiki under `wiki/`. This file records **orama-specific disposition** and links
so both-repo agents land in one checklist.

**Verified `main`:** orama `41b77300` · PT `4f1a9936` · 2026-07-27.

---

## Orama disposition snapshot

| Area | Tag | Pointer |
| --- | --- | --- |
| Mesh Phase A (#223) | **DONE** | Prep on `main` |
| Mesh Phase C (#224) | **DONE** | P5/P6, `mesh_gate`, discovery trust, swarm approval |
| Mesh Phase B (#222) | **IN PROGRESS** | IP expunge + `docs/v2/50-mesh-security-migration-ladder.md` — merge last |
| Mesh Phase D | **DEFERRED v2** | Strict cutover at v2 launch |
| Identity Phases 1–2 (#220) | **DONE** | `audit_engine` on `main` |
| Identity Phases 3–4 | **NOW** | PT sync PR + remove legacy lists |
| Hermes Mac staging | **DONE** | [`docs/plans/2026-07-26-hermes-openclaw-staging-execution.md`](../plans/2026-07-26-hermes-openclaw-staging-execution.md) |
| Hermes Win operator smoke | **NOW** | [`docs/plans/2026-07-26-hermes-openclaw-migration-operator.md`](../plans/2026-07-26-hermes-openclaw-migration-operator.md) |
| Hermes envelope reconciliation (T-ENG-1 + Wave 1–2) | **DONE — local, push deferred** | Branch `2026-08-05-002-hermes-graft-plan-reference-fix` (`e90cb16d`…`e17aad66`); 38/38 tests; SoT `hermes-universal-invocation-protocol.md`; coord-036 inbox `mac-2026-08-06-hermes-envelope-reconciliation.md`; [`docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md`](../plans/2026-08-03-hermes-openclaw-graft-audit-plan.md) |
| Hermes Appendix C (task API, fleet mgr, verifier, scheduler, recursive, HITL) | **DEFERRED v2.1++** | Stubbed as `not_yet_implemented` in `hermes-status --json`; plotted in graft plan Appendix C stub map |
| Peer-mesh TLS/auth (49) | **MINIMUM DONE** | Bearer-not-on-plain-HTTP; rest **DEFERRED v2** |
| G7 portal hub MVP | **NOW** (optional) | [`fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`](fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) |
| Fleet Phases 8–10+ | **DEFERRED v2** | [`fleet-mesh/README.md`](fleet-mesh/README.md) |
| PR #224 finality | **DONE** | Integrated in PT master plan §12; [source report](fleet-mesh/2026-07-26-pr224-mesh-security-finality-report.md) |

---

## Superseded trackers

- [`2026-07-25-pending-work-tracker.md`](
  2026-07-25-pending-work-tracker.md) → use canonical master plan §4
- [`2026-07-25-docs-scan-and-integrity-report.md`](
  2026-07-25-docs-scan-and-integrity-report.md) → HEAD was `5b05f545`; refreshed in master plan

---

## Status legend

**DONE** · **IN PROGRESS** · **NOW** (pre-v2) · **DEFERRED v2** · **REFERENCE** · **SUPERSEDED**

Full file-by-file registry: canonical master plan §5–§8.
