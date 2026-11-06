# Architecture and migration status reconciliation — 2026-11-06

This routing note preserves earlier planning and evidence records. It does not
ratify a new architecture, establish deployment qualification, or authorize
activation. When a dated planning statement conflicts with an identified later
decision, use that decision for its specific scope and retain the older text as
historical evidence.

## Ownership and migration

- [D-LG-1](references/loop-graph-compatibility-2026-10-09/ADR-D-LG-1-POLICY-OWNERSHIP.md),
  amended by [D-LG-5](references/loop-graph-compatibility-2026-10-09/ADR-D-LG-5-REDUCER-JOIN-DECLARATIONS.md),
  assigns structural GraphSpec, lint and reducer/join declarations to Core;
  application policy can restrict them. Earlier September migration plans and
  docs 57–59 retain their original wording and are superseded only where they
  conflict with these later decisions.
- [D-LG-6](references/loop-graph-compatibility-2026-10-09/ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md)
  records the reducer/join design; its historical open-PR/pin statements are not
  a current release receipt. Core `6d75cfe08af95992dddffab13ae3019aa9c41350`
  is the Oramasys production dependency pin as observed on 2026-11-06.
- [ADR 62](62-telos-phylax-authority-gate0-adr.md) places endpoint/address
  security in Telos and principal/capability admission in Phylax. PT continues
  to own its v1 endpoint/security and hardware policy. Agate owns the v2
  hardware-placement boundary. Existing Core policy-related modules still exist;
  the target ownership does not claim all migration is complete.
- [Doc 68](68-orchestrator-controller-satellite.md) specifies a planned internal
  Oramasys job-claim controller; a standalone repository remains a later option
  only through its section 9 admission gate. Existing execution run-lease
  fencing is distinct. Earlier PT consolidation plans are v1 implementation
  history, not authority to port their job queue into the v2 controller.
- Orama `docs/v2` owns the cited design decisions and ownership-registry and
  capability-schema sources. This is a documentation and verification boundary,
  not a runtime dependency on legacy Orama services.

## Gate names and evidence

Graph compatibility R3/R4 refer to reducer/join and durable-resume work. The
Release 1–2 R1–R8 series is a different qualification sequence; matching numbers
are not matching gates. The [m1-gen2 receipt](references/m1-gen2-qualification-evidence-receipt-2026-10-18.md)
is a dated evidence record, not authorization for unrelated serving activation.
The [refusal/HITL contract](references/2026-10-09-compatibility-refusal-hitl-contract.md)
supersedes conflicting compatibility-refusal guidance in older accountability
material. Operator approval and actual host evidence remain distinct from CI.

Review the [root map](../../ARCHITECTURE.md), current owner source and exact
deployed revisions before executing an older plan. Historical index counts,
next-free numbers, statuses and PR references should be rechecked rather than
treated as a current schedule.

The [build order](04-build-order.md), [security roadmap](plans/security-v2-roadmap.md),
[security execution plan](plans/security-v2-roadmap-part2.md),
[initial Agate design](references/agate-mvp-design.md) and
[historical accountability document](references/HUMAN-IN-LOOP-ACCOUNTABILITY.md)
retain their earlier text. Their conflicting endpoint-package, hardware-owner
and compatibility-refusal claims are superseded in the scopes named above.
The original September instruction-audit inputs remain preserved; the
[errata](references/errata-corrections-to-preserved-documents.md) applies the
later ownership corrections to those inputs and their cross-reference plans.
