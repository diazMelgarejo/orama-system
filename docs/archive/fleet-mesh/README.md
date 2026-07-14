# Fleet Mesh — Archive

Status: completed / historical fleet-mesh records.

This folder indexes completed reports and historical ledgers from the SOLO / PAIR / FLEET → Phase 7–10+ lineage. Active unfinished work belongs in [`../../next/fleet-mesh/README.md`](../../next/fleet-mesh/README.md).

## Completed reports

| Document | Status | Why archived |
|---|---:|---|
| [`PHASE-6-IMPLEMENTATION.md`](PHASE-6-IMPLEMENTATION.md) | completed report | Phase 5–6 banner display and self-healing mesh implementation report. This is a milestone report, not the root plan. Its “Next Steps” section is the clue that points into Phase 7–10+. |

## Historical ledgers

| Document | Status | Why archived/indexed here |
|---|---:|---|
| [`2026-07-10-pr2-phase0-review-crossreference.md`](2026-07-10-pr2-phase0-review-crossreference.md) | historical ledger | Useful provenance ledger for cross-repo Phase 0/1/2 confusion, but not an active implementation plan. |

## Archive-to-Active Navigation Graph

The archive is evidence, not an authority inversion. Start from the active
index, then follow a direct archive edge only when a question needs completed
implementation evidence, a historical decision, or correction provenance.

| Archived node | Direct active or canonical edge | Correct use |
|---|---|---|
| [`PHASE-6-IMPLEMENTATION.md`](PHASE-6-IMPLEMENTATION.md) | [`phase-7-to-10-roadmap.md`](../../next/fleet-mesh/phase-7-to-10-roadmap.md) -> [`fleet-mesh active index`](../../next/fleet-mesh/README.md) | Evidence that Phase 5-6 work completed and why its next-step clue points onward. It is not the mother plan. |
| [`2026-07-10-pr2-phase0-review-crossreference.md`](2026-07-10-pr2-phase0-review-crossreference.md) | [`phase integration map`](../../next/fleet-mesh/2026-07-10-phase-integration-map.md) -> [`mother plan`](../../next/fleet-mesh/2026-07-08-self-healing-mesh-degradation-modes.md) | Provenance for Phase-numbering and review-status corrections. It must not override newer live verification. |
| Historical mesh evidence | [`docs/v2/`](../../v2/) -> [`43-gossipbus-mesh-transport.md`](../../v2/43-gossipbus-mesh-transport.md) | Reconcile old wording with canonical current architecture before carrying it into G7 or later mesh work. |
| Historical security claims | [`39-maestro-owasp-genai-reference.md`](../../v2/39-maestro-owasp-genai-reference.md) -> PT [swarm security analysis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md) | Preserve the old evidence, but validate security conclusions against the canonical hub and current PT threat-model record. |

```text
archive report or ledger
  -> active fleet-mesh index
  -> canonical docs/v2 authority
  -> current G7 research and implementation plan
```

This reverse edge is deliberate: archive material may explain a decision, but
new work flows from the active index and canonical `docs/v2/` documents.

## Archive rule

A document belongs here when it records a completed milestone or historical review ledger. It should not be used as the launchpad for new implementation unless the active index in `docs/next/fleet-mesh/README.md` explicitly points back to it.

When a local checkout is available, convert these index-only archive links into real `git mv` moves for any completed files the project wants physically relocated.
