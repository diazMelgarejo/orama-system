# Envelope Standard — Provenance and History (2026-09-27)

**Companion to:** [`69-agent-envelope-standard.md`](../69-agent-envelope-standard.md)
(the normative standard). **Document owner:** `orama-system`.
**Status:** reference only. Nothing here is normative; where this file and doc 69
disagree, doc 69 wins.

This file records **how the standard was assembled**, so the reasoning survives
without carrying working material into the specification. Autoplan transcripts,
voice sections, and review chatter are deliberately excluded.

## 1. Why the standard exists

The same envelope shape grew independently in three places: PT memory prose
(`agent-envelope:` lines), `HandoffPacketV1`, and the doc 68 controller request.
Each had solved part of the identity problem, and none of them shared a header.
The consolidation question was whether one header could serve all three without
becoming a fourth contract.

## 2. Chronology

| When | What happened | Outcome |
| --- | --- | --- |
| 2026-06 → 2026-08 | Memory envelopes accumulate in PT `.agent` | Evidence that `agent=` named the **author**, not the writer |
| 2026-08-24 | `references/observability/12-…` defines four envelope planes | Planes classify *where*; kinds classify *what* |
| 2026-09-04 | Approved standalone `CoordinationRoundEnvelopeV1` design | Rounds stay a sibling; no inline round payload |
| 2026-09-26 | Agent-vs-author evidence found in PT `.agent` (six classes) | Divergence is real, not hypothetical |
| 2026-09-26 | Board proposals `AUTHOR_ACTOR_PROPOSAL` / `AUTHOR_ACTOR_HARMONIZED` | `author` + `actor` + conditional `lineage` |
| 2026-09-26 | Codex read-only review of the working synthesis | 9 findings; all fixed in the proposal text |
| 2026-09-27 | Board read surfaced three gaps in the controller invariants | Non-supersession scope, canonical projections, `IC-28`/`IC-29` |
| 2026-09-27 | Operator promotion decision (this file's reason to exist) | Doc 69 published; roles split (doc 69 §1) |

## 3. Decisions that shaped the standard

- **Two faces, one card.** `author` is who the work is about; `actor` is who
  presents the record. `lineage` exists only when the ids differ, so its presence
  *is* the divergence signal and no extra boolean is needed.
- **Observation is never mutation.** `availability` (`active`/`inactive`/
  `unknown`) is what the actor saw at write time. It never updates a heartbeat
  store and never moves a claim; only the controller mutates claim state.
- **Canonical owners for projections.** Delivery `task_id`/assignee belong to
  `HandoffPacketV1`; claim `task_id`/`principal` belong to doc 68 §4.2; raw
  `round_id` belongs to the standalone round record. Projections must match
  exactly and reject before lookup.
- **Tier discipline.** Tier U carries no default; Tier C must be declared, not
  omitted, under `extra="forbid"`.
- **Non-supersession.** The standard may take over the header, dedup, the
  redaction receipt, correlation naming, and kind mapping — and nothing else.

## 4. Corrections kept visible

- An earlier draft described the v1 branches as "unpushed"; they were pushed and
  open as PT PRs #401/#402. Corrected 2026-09-27.
- An earlier review claim that a governing section `§20.0` was missing was wrong;
  it exists in the working synthesis. The false positive is recorded on the board.
- The controller's home was first documented as a "proposed satellite"; the
  operator fixed it as the `oramasys/oramasys` internal module (doc 68 §2).

## 5. Working material (off-repo)

The 838-line working synthesis and its codex review remain outside the repository
as deliberation records. They are inputs to this history, not authorities.
