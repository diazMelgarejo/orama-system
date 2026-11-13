# Queue Fencing and Recovery — Work Package

> **Status:** D-0 documentation work package, assembled 2026-11-11 on branch
> `qf/d0-documentation`. This directory carries plan, decision and
> amendment-draft records only; this PR ships no runtime change.
> **Parent register:** the [master closure register](../MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md)
> is the one register for the closure arc; this is a subordinate work package of it, not
> a competing register, and every task below maps to an existing master row.
> Master-register row appends remain with the integrator and are not part of
> this PR.

## 1. Scope

The [plan](plan.md) consolidates the 2026-11-10 authenticated-queue plan, its
review, and the 2026-11-11 reconciled draft into one execution plan (AFRP
Type C, Expert, Mode 2; `oramasys-method` with the contract-migration method
as the structure of the contract ledger). On acceptance it replaces, as
recommendations only, those three inputs; all three stay preserved as
historical inputs. The v1 side is owned by Perpetua-Tools and the v2 side by
oramasys; orama-system owns the design docs this package amends.

## 2. The three design ideas

1. **Acquisition continuity.** Every acquisition has a persistent,
   never-reset generation (v1) or the existing lease fence (v2). Every
   release, completion, renewal and recovery re-reads canonical state inside
   the write transaction and compares the whole acquisition and the versions,
   not the agent name.
2. **Reuse, do not invent.** The v1 ledger follows the existing
   `dispatch_guard` private-state pattern; v2 extends the existing
   Controller. No new cryptography, no new daemon, no second authority.
3. **Smallest independent fix first.** The cleanup race has a narrow interim
   repair (L-1a) that needs no migration, so it lands before the ledger and
   is later subsumed by the authority boundary.

## 3. Ratification

The operator ratified the consolidated plan and accepted **every section 3
gate** as proposed: Q-D23, Q-TOPO, Q-D1, Q-D2, Q-68, Q-AGE, Q-RET, Q-LAYOUT
and Q-SQLITE. The recorded decisions and what each gate blocks are in the
[decision record](decision-record.md).

**Q-68b** uses the operator-confirmed numbering: attempt 1 is the original
request, attempt 2 is the first verified retry and may return the raw lease
token, and attempt 3 and later return token-free receipts under the stricter
replay policy. There is no attempt 0. Full admission is required at every
stage. The first-retry allowance is consumed atomically and durably before
returning the token; concurrency and restart must not restore that allowance.
This limited replay decision does not authorize other slice-A work. See the
[decision record](decision-record.md) for enforcement and migration gates.

## 4. Tasks and current status

Local task labels from plan section 5, mapped to master-register rows; not
new register rows. Order and gating follow the plan; the slice-A tasks wait
for their own premise decision.

| Task | Owner and parent row | Current status |
| --- | --- | --- |
| V1-1 | PT and integrator, C2/C4/C5 | COMPLETE (2026-11-11): read-only audit, exit 0, PT tree clean at 1020b58; all three L-1a premises confirmed; L-1a GO |
| V2-1 | Oramasys and integrator, C2/C3a–C3d | Windows-side cross-evidence complete (oramasys audit at f33d809; deliverables written); canonical V2-1 assigned to Antigravity on the Mac; integration pending |
| D-0 | Orama design owner and operator, C1/C2 | This PR |
| L-1a | PT, C2/C5 | Implemented and tested on the Mac/POSIX branch; local commit remains unpushed pending operator-held push and merge. Windows drafts remain held as cross-evidence; no live cleanup run is authorized by this row. |
| V1-2 | PT, C2/C4/C5 | Gated (needs D-0 accepted gates and Q-SQLITE) |
| V1-3 | PT, C2/C5 | Gated (needs V1-2) |
| L-1b | PT, C2/C5 | Gated (needs V1-2) |
| V1-4 | PT and verified Orama callers, C2/C4/C5/C8 | Gated (needs V1-3, L-1b, Q-D2) |
| C3d-base | Operator, C3d | Open (operator) |
| V2-2 | Oramasys, C2a/C3a/C3c | Gated (needs V2-1, Q-68, C3d-base, Q-SQLITE) |
| V2-3 | Oramasys, C3/C3b/C3c | Gated (needs V2-2, Q-68) |
| V2-4 | Oramasys and operator, C3d/C7–C11 | Gated (needs V2-2, V2-3) |
| V1-0 | PT and host owners, C4/C8 | Gated (slice-A premise decision, still open) |
| A-V1 | PT, new C2 child | Gated (needs V1-0) |
| P-H1 | Phylax and Telos, C3a child | Gated (slice-A premise decision, still open) |
| K-Q | PT memory writers | Gated (needs verification) |

## 5. Contents of this directory

- [plan.md](plan.md) — verbatim copy of the consolidated plan
  (`QUEUE-FENCING-AND-RECOVERY-CONSOLIDATED-PLAN-2026-11-11.md`).
- [decision-record.md](decision-record.md) — verbatim copy of the D-0
  decision record (`D0-DECISION-RECORD-2026-11-11.md`).
- [amendment-drafts.md](amendment-drafts.md) — the Q-68 and Q-68b amendment
  drafts taken from the V2-1 audit, marked **DRAFT**: the design owner still
  pins the authoritative recipient field names and the old-client refusal
  code before the Q-68 amendment text is finalized.

The source records are preserved as historical inputs. The dated status notes in
this work package are additive remediation: they identify superseded operational
status without rewriting the source history. Markdown lint applies to the files
as published here.

## 6. Amendments applied in docs/v2 by this PR

- [doc 68](../68-orchestrator-controller-satellite.md) — dated additive banner
  note (2026-11-11): a partial runtime implementation of the claim store,
  request envelope, refusal vocabulary, Telos and Phylax ports with deny-all
  defaults, the transactional outbox and the opt-in expiry worker exists in
  the oramasys repository under `src/orama/orchestrator_controller/`; not
  reviewed, not deployed, not activated, no serving path composes it. Nothing
  rewritten; the prior wording is preserved as history.
- [doc 61](../61-pt-coordination-principal-identity-design.md) — additive
  amendment recording the Q-D2 decision: shim names retained; changed
  availability and handle requirements for mutations observed first, then
  enforced; no fallback writer after cutover.

## 7. Not in this PR; owner-held

- Short pointers in `Perpetua-Tools/docs/next/` and in oramasys docs
  (proposed home per plan section 1) belong to those repositories and are
  not part of this PR.
- Canonical V2-1 (Antigravity, Mac) integration into the decision record is
  pending run completion; the Windows-side cross-evidence is already
  recorded.
- The slice-A premise decision (V1-0, A-V1, P-H1) remains open.
- Everything else stays owner-held per plan section 11.
