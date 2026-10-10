# R4 safety, compatibility and platform — reference set

**Date:** 2026-10-10 (UTC). **Status:** approved by the operator; implementation remains
gated by the execution plan and its evidence requirements. Documentation
and planning only. This set authorizes no code, pin change, publication of a runtime,
production egress or provider spend.

This directory turns the operator's R4 draft
([`source/`](source/ORAMASYS-R4-SAFETY-COMPATIBILITY-PLATFORM-DRAFT-ADR-PLAN-HANDOFF-2026-10-10.md),
preserved byte-for-byte) into discrete canonical references. Each file owns one
contract, so each can be reviewed, amended and ratified on its own. The source draft
stays as the historical input; where it and these files differ, these files govern
after review and the difference is listed in the [review record](REVIEW-RECORD.md).

## Priority order (operator confirmed)

1. **Safety.** 2. **Compatibility**, forward to LangChain/LangGraph and backward to
permitted v1 concepts. 3. **Platform self-consistency and interoperability.**
A lower priority never weakens an invariant of a higher one.

## Reading order

| # | File | Owns |
| --- | --- | --- |
| 1 | [ADR-D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md) | Umbrella decision, arbitration, ownership, per-contract status |
| 2 | [CONTRACT-ARTIFACT-ADMISSION](CONTRACT-ARTIFACT-ADMISSION.md) | `ArtifactBinding`, admission results, trust |
| 3 | [CONTRACT-DURABLE-HITL-EFFECTS](CONTRACT-DURABLE-HITL-EFFECTS.md) | Approval, grant, reservation, effect state machines |
| 4 | [CONTRACT-FOREIGN-PROVIDER-TRANSPORT](CONTRACT-FOREIGN-PROVIDER-TRANSPORT.md) | One-cell provider transport and containment |
| 5 | [CONTRACT-DURABLE-CONTINUATION](CONTRACT-DURABLE-CONTINUATION.md) | `DurableCheckpointV1`, recovery algorithm |
| 6 | [CONTRACT-COMPATIBILITY-REPLACEMENT](CONTRACT-COMPATIBILITY-REPLACEMENT.md) | Matrix, packaging modes, diagnostics tiers |
| 7 | [REGISTER-RETAINED-V1-CONCEPTS](REGISTER-RETAINED-V1-CONCEPTS.md) | Permitted backward-v1 vocabulary and dispositions |
| 8 | [CONTRACT-MULTI-HOST-STAGES](CONTRACT-MULTI-HOST-STAGES.md) | H0/H1/H2 deployment stages |
| 9 | [PLAN-R4-EXECUTION](PLAN-R4-EXECUTION.md) | Tasks T0–T11, milestones, gates, file map |
| 10 | [REGISTER-TRACEABILITY](REGISTER-TRACEABILITY.md) | Requirement-to-task map, rev-2 crosswalk, sources |
| 11 | [REVIEW-RECORD](REVIEW-RECORD.md) | Code-review findings, human checklist, handoff |

## What is and is not true today

- R3 mechanics (fan-out regions, reducers, joins, schema "2") are merged in Core and
  Oramasys. Production Core in Oramasys is still pinned at the pre-R3 commit; pin
  promotion is a separate, evidence-gated step ([plan](PLAN-R4-EXECUTION.md) §P0).
- The current resume path starts at `START` with loaded state. It is not durable
  continuation ([continuation contract](CONTRACT-DURABLE-CONTINUATION.md) §1).
- Durable approvals, effect reservations, production foreign transport, durable
  continuation and full upstream replacement are **unimplemented**. Nothing here
  says otherwise.

## Boundaries held by every file here

Orama `docs/v2` is normative design authority with no schema or runtime code. Core
stays dependency-minimal with one scheduler, `CompiledGraph._run()`. Oramasys is the
code target. Telos owns endpoint security, Phylax generic admission and
monitorability, Agate hardware evidence. LangChain, LangGraph and Pydantic AI are
never default or published-extra dependencies. v1 stays independent of v2 runtime
dependencies. Records name categories only; no private identity, credential, device,
endpoint or workstation literal appears in tracked content.

## Relationship to existing records

Additive. [Doc 57](../../57-minigraph-final-reconciliation.md) §10–§11 gain
qualification notes; erratum E13 records the corrections; the
[revision-2 plan](../remaining-capabilities/IMPLEMENTATION-PLAN-REV2-2026-10-10.md)
and [R3 audit](../remaining-capabilities/R3-AUDIT-REPLAY-AND-COMPATIBILITY-2026-10-10.md)
stay as historical records, mapped by the [crosswalk](REGISTER-TRACEABILITY.md#rev-2-crosswalk).

P0 follow-up: the [corrected P0 implementation plan](PLAN-P0-CORE-PIN-PROMOTION.md)
and its [review and post-P0 roadmap](P0-REVIEW-AND-NEXT-STEPS-2026-10-10.md) define
the promotion gates. Canonical registry promotion is not production enablement.

The corrected [P0 through T2 execution plan](P0-THROUGH-T2-EXECUTION-PLAN-2026-10-10.md)
separates qualified P0 consumer promotion from the later T1 admission and T2 observation/
budget slices.
