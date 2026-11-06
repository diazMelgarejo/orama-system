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
- Orama `docs/v2` owns the cited design decisions and the
  [ownership registry](references/loop-graph-compatibility-2026-10-09/ownership-registry.json);
  the [capability schema](../schemas/capability-record.schema.json) lives in
  `docs/schemas`. These are documentation and verification boundaries, not
  runtime dependencies on legacy Orama services.

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

## Status routes for documents not edited in place

Most documents below have existing formatting debt, or carry a generated
downstream pointer; their corrections are routed here without in-file edits.
The public plugin API authentication correction is also made in-file so direct
readers receive it. The per-finding ledger is
[C1 dispositions](closure/c1-orama-dispositions-2026-11-06.md).

| Document | Current reading |
| --- | --- |
| [04 build order](04-build-order.md) | Phase markers such as "← NEXT" are historical. The lift table's Core placement of policy YAML and selectors is superseded by ADR 62, [doc 42](42-agate-hardware-policy-orbit.md) and [doc 60](60-phylax-monitorability-design-spec.md). For closure work, the [master plan](MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md) is the sequencing register. |
| [05](05-feasibility-review.md), [09](09-comparative-analysis-and-merging-plan.md), [10](10-v1-hacks-automation-orbit.md), [12](12-xai-model-migration-2026-05.md), [18](18-master-alignment-v2-migration-plan.md) | Historical May 2026 records. "Active" labels and passed deadlines are not current status. |
| [07 Agate vision](07-agate-vision.md) | Vision text. Its hardware-owner references follow the Agate row below. |
| [14 supervisor patterns](14-supervisor-and-anthropic-patterns.md) | Section 8 is superseded: the v2 job queue, claims and recovery belong to the planned Oramasys controller in [doc 68](68-orchestrator-controller-satellite.md), not to PT. |
| [29 mastery plan](29-oramasys-mastery-implementation-plan.md) | Historical. Its section 5 layout does not match the Oramasys `src/orama/` tree; "Approved for execution" is not current status. |
| [30 multi-LLM router](30-multi-llm-router-caching-batching-decorator.md) | Scoped to v1 PT. It is not a v2 router; v2 endpoint security belongs to Telos under ADR 62. It is the canonical source of PT's generated ADR-002 pointer, so an in-file note needs a paired pointer regeneration in PT. |
| [02-modules index](02-modules/README.md) | The subgraph helper is `perpetua_core.graph.plugins.subgraphs.as_node`. |
| [Public plugin API module](02-modules/plugin-api-public.md) | Stub; authentication guidance corrected in-file against D16, docs 23 and 24, SECURITY.md and ADR 62. LAN locality is not authentication. Hardware routes belong to Agate. |
| [RAG and memory module](02-modules/rag-and-memory.md) | Superseded in practice by docs [56](56-anamnesis-runtime-memory-migration.md), [67](67-lancedb-duckdb-dense-info-layer-shape.md) and [20](20-rag-and-memory-design.md). |
| [AlphaClaw MCP smoke test](02-modules/alphaclaw-mcp-smoke-test.md) | v1 handshake specification; see [doc 40](40-oramaclaw-lifecycle-plugin.md) for the oramaclaw lifecycle. |
| [Security roadmap](plans/security-v2-roadmap.md), [execution plan](plans/security-v2-roadmap-part2.md), `plans/security-v2-cursor-manifest-part2.json` | Only the shared endpoint-policy package model is superseded by ADR 62. Other security requirements, including CSRF/origin protections and safe rendering, are not waived; check current owner sources and [SECURITY.md](../../SECURITY.md). |
| [HUMAN-IN-LOOP-ACCOUNTABILITY](references/HUMAN-IN-LOOP-ACCOUNTABILITY.md) | Historical, principles only. Its self-declared authority, PT identity-verification placement and August 2, 2026 deadline are not current. Bounded autonomy is governed by [ADR 71](71-operator-provisioning-and-autonomous-tier-adr.md), approved policy but not deployed. Current rules: the refusal/HITL contract and [CONTRACT-DURABLE-HITL-EFFECTS](references/r4-safety-compatibility-platform-2026-10-10/CONTRACT-DURABLE-HITL-EFFECTS.md). |
| [Agate MVP design](references/agate-mvp-design.md) | Superseded on ownership: Agate owns v2 hardware placement, and PT owns only the v1 policy. Its "ignore unknown keys" rule conflicts with the [graph policy contract](references/loop-graph-compatibility-2026-10-09/GRAPH-POLICY-CONTRACT.md), where unknown fields fail closed. |
