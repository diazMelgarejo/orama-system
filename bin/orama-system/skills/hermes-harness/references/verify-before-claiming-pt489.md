# Verify-before-claiming — coordination protocol reference (PT 489)

Source of authority: Perpetua-Tools PR 489 (merged; head verified ancestor of
PT origin/main) - the operating checklist lives at
`Perpetua-Tools/.agent/protocols/verify-before-claiming.md` with the dated
miss catalogue in `memory/semantic/HANDWAVING_CATALOGUE_AND_AVOIDANCE_2026-11-10.md`.
This file points orama-system peer agents to the checklist and keeps the rules
specific to coordination work.

## The checklist

The checklist is kept once, in orama-system
[`docs/verify-before-claiming.md`](../../../../../docs/verify-before-claiming.md); the
Perpetua-Tools protocol stays the source. This file no longer carries a second wording of it.

## Harness rule kept from the port

- **Claims and receipts**: an assignment or a merged PR is not a result; a
  reviewer disposition or an owner go needs its own record. Claim only what
  you can evidence; state identity_verified=false and endorsement=none on
  self-reported notes.

## Application to orama-system peer coordination

- Board notes and LAN drops follow items 3 and 6: every status line carries
  the artifact filename and its sha256.
- Task claims (task_claims rows) follow item 6: claim only after reading the
  enqueue payload and the referenced evidence; state blockers with the
  missing-input owner.
- Cross-references: PT 489 (Perpetua-Tools), D-0 decision record
  (docs/v2/queue-fencing-and-recovery/decision-record.md), the Q-68b
  numbering clarification.
