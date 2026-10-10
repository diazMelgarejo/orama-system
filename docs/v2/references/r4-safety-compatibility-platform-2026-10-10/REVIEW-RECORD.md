# Review record, human checklist and next-agent handoff

**Status:** review of the operator's R4 draft, performed while converting it into this
set (2026-10-10, `/code-review` per the oramasys-method). Findings were checked against live
sources; "verified" below means re-read from `main` on that date, not inferred.

## Method

AFRP: Type C, Practitioner, Mode 2. Stages: immerse (draft, rev-2 plan, R3 audit, doc 57,
errata, ADR index, live heads and pins) → architect (one file per contract) → refine
(remove duplication, keep the draft's wording where it was already exact) → execute (docs
only, lint and hygiene gates) → crystallize (this record). Additive throughout: nothing
was deleted; the draft is preserved under `source/`.

## Verified claims

| Claim in the draft | Result |
| --- | --- |
| `ainvoke(loaded_state)` restarts at `START` | Verified in Core `main`: `ainvoke` delegates to `_run`, which resolves the edge out of `START` |
| `first_success` selects the lowest-named success | Verified in D-LG-6 (join table) |
| Core #9, Oramasys #25, Orama #390 merged | Verified: merge commits `4d217f6`, `f4dbf33`, `10c09ee` |
| Production Core still pinned pre-R3; candidate at `34e4a8d` | Verified in Oramasys `main` |
| Oramasys requires Python ≥ 3.11 | Verified in `pyproject.toml` |
| D-LG-7 number is free | Verified: no occurrence under `docs/` |
| PT #432 open at `216efff` | Verified at review time (CI green, merge state clean) |
| PT #433 ancestry integrated into #432 | **Not independently verified**; recorded from the operator's comment. Check at T0 |
| Core 255 / candidate 333 / production 307+1 skip | **Not re-run**; historical, as the draft itself says |

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| F1 | High | Draft says rev-2 Tasks 0–11 "map to T0–T11"; numbers do not align (rev-2 Task 5 is done; Task 6 is T5; Task 7 is T6; and so on) | Fixed: explicit [crosswalk](REGISTER-TRACEABILITY.md#rev-2-crosswalk); erratum E13 |
| F2 | High | Doc 57 §10 still says reducers are "deferred R3 work"; §11 predates the checkpoint design | Fixed: additive qualification notes in doc 57 |
| F3 | Medium | One ADR bundles seven contracts, so rejecting one blocks all | Fixed: umbrella ADR plus one file per contract, each with its own status |
| F4 | High | Crash table omitted windows between handoff and provider acceptance, after a cancel request, and during reconciliation | Fixed: three rows added ([HITL §6](CONTRACT-DURABLE-HITL-EFFECTS.md#6-crash-windows-and-recovery)) |
| F5 | Medium | Expiry is required "UTC after restart" but a backward clock jump would silently extend a grant | Approved: high-water-mark rule ([HITL §5](CONTRACT-DURABLE-HITL-EFFECTS.md#5-clock-policy-approved-freeze-implementation-details-at-t0)); T0 freezes implementation details |
| F6 | Medium | Draft names dispatch milestones but never lists effect states, so tests could not name transitions | Proposed: explicit effect and grant machines ([HITL §3](CONTRACT-DURABLE-HITL-EFFECTS.md#3-state-machines)) |
| F7 | Medium | Pin promotion appears in M1 and T11 but is not a task; easy to skip | Fixed: named prerequisite P0 in the [plan](PLAN-R4-EXECUTION.md) |
| F8 | Low | H1 needs authenticated worker identity but the draft does not say which designs supply it | Fixed: dependency on docs 49/61 stated ([multi-host §4](CONTRACT-MULTI-HOST-STAGES.md#4-principals-and-trust)) |
| F9 | Low | Successor branches must use `yyyy-mm-dd-NNN-brief-summary` (doc 57; CLAUDE.md §6); the draft is silent | Applied to this docs branch; restated in the plan's operating rules |
| F10 | Low | Rev-2 plan sections now stale ("R3 gated", "PR open") | Left as historical; superseded by the crosswalk and status table |

No finding changed a safety invariant or an ownership decision.

## Human review checklist

State the approved revision and any exceptions.

- [ ] Accept the direction and priority order (already operator-confirmed).
- [ ] Accept [HITL §4](CONTRACT-DURABLE-HITL-EFFECTS.md#4-dispatch-protocol-and-the-linearization-boundary)
  dispatch/revocation linearization and unknown-outcome handling.
- [ ] Accept the [continuation contract](CONTRACT-DURABLE-CONTINUATION.md) and the
  legacy-snapshot rule.
- [ ] Accept [compatibility packaging](CONTRACT-COMPATIBILITY-REPLACEMENT.md) and the
  [retained-concept rubric](REGISTER-RETAINED-V1-CONCEPTS.md).
- [ ] Accept the [H0 → H1 → H2](CONTRACT-MULTI-HOST-STAGES.md) sequence.
- [ ] Confirm which T8/T9 follow-ons are in the first release; T0 selects provider and
  version cohorts from the source inventory.
- [x] Decide the F5 clock rule or amend it. Same decision as the Ratification section
  below, owned by the operator: fail-closed clock policy approved on 2026-10-10.

This checklist is the review record. It is not a request to approve work already authorized.

## Ratification (2026-10-10)

The operator approved this D-LG-7 revision, all named design contracts, the priority order
(safety → compatibility → platform interoperability), and the F5 fail-closed clock policy.
The accepted clock recovery requires audited trusted-time evidence before dispatch resumes.

Immediate continuity sequence: record this ratification in PT memory; complete T0's pinned
inventory and evidence refresh; execute P0 as a separate Core-to-Oramasys consumer
requalification; then begin T1/T2 and T3 in independently reviewed PR slices. No approval
turns a design contract into a provider-effect grant, and T4/T5 remain blocked by their
predecessor acceptance gates.

## Next-agent handoff

**Authorized so far:** the ratified documentation plus staged implementation beginning with
T0/P0. Every slice retains its own tests, review and release gates.
**Stop boundary:** do not bypass a predecessor gate, promote an unqualified pin, or enable
provider effects merely because the design is approved.

1. Read this set, then current root and nested instructions. Refresh live PRs first; this
   handoff goes stale.
2. Preserve the priority order, the single-scheduler rule and the R3 and resume limits. Do
   not reopen the ownership debate settled by D-LG-5; infer no authority from a summary,
   heartbeat, resume value, trace or idempotency declaration.
3. Record the review disposition against this directory and revision. Resolve amendments
   before implementation; begin T0 and freeze each slice's files, types and tests.
4. Start approved implementation PRs from verified merged predecessors. Core #9, Oramasys
   #25 and Orama #390 are merged; never push to them.
5. Do P0 first, with fresh full consumer evidence. Then T1/T2 → T3 → T4/T5; pure T6 cells
   may advance after inventory, effectful ones wait.
6. Keep an operation/effect crash log, a compatibility matrix and a requirement closure
   table. Update PT through its tooling per approved slice, append-only.
7. Finish each handoff with exact active PR heads and pins, commands and results,
   unresolved reviews and remaining gates.

**Remaining after this change:** human review; T0; P0; admission and reliable progress;
transactional HITL; production transport; true continuation; versioned LC/LG and v1
compatibility; the production Pydantic bridge; selected adjacent capabilities; H1/H2.
