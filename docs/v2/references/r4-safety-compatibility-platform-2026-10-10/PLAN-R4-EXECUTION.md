# Plan — R4 preparation and execution (T0–T11)

**Status:** approved execution plan under D-LG-7. No task here is authorized to
start. After human review, execute approved tasks with `superpowers:executing-plans`;
delegate only if the operator selects delegation. An unchecked box is not a shipped
capability. Decision source: [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).

## Operating rules

Review amendment proposal: [P0-T2 revision 3](P0-THROUGH-T2-EXECUTION-PLAN-REV3-2026-10-10.md)
supersedes the detailed first P0-T2 roadmap and [revision 2](P0-THROUGH-T2-EXECUTION-PLAN-REV2-2026-10-10.md)
for review. It qualifies candidate heads before registry promotion, separates durable T2
accounting from T5 graph continuation, and specifies one neutral dispatch gate with bounded
delivery. T1/T2 contract refinements remain proposals until reviewed; this note does not
ratify them.

- Every implementation task: reproduce a named failing invariant, implement the minimal
  reviewed change, run focused and affected suites, review the diff, commit one logical
  batch. Commands come from the actual checkout, with import paths recorded.
- Proposed paths below are design decisions, not existing files. At T0 map them to current
  instructions and layout; preserve the `src` execution standard and record justified
  relocations before implementation.
- New implementation PRs start from confirmed merged baselines. Never force-push, delete
  history, close an existing PR to simplify coordination, or push to a merged PR's branch.
- Report implemented, verified, published, reviewed, merged and enabled separately.
  Pending is not passed; a local commit is not a publication.

## File map (proposed)

| Repo | Existing seam | Proposed additions |
| --- | --- | --- |
| Core | `src/perpetua_core/graph/{engine,spec,lint}.py`, `graph/plugins/` | Neutral continuation records/protocols beside the checkpointer; durable-resume tests in `src/tests/graph/` |
| Oramasys | `src/orama/graph/perpetua_graph.py`, provider and gateway contracts | `src/orama/graph/{admission,approvals,effects,recovery}.py` where no equivalent exists; transaction adapter outside the engine |
| Oramasys | Framework bridges and compatibility tests | `src/orama/compat/{manifest,diagnostics,activation}.py`; matrix runner |
| Oramasys | Provider contracts and ledgers | `src/orama/providers/foreign_transport.py` and focused adapters |
| Oramasys | Accepted controller home | Extend `src/orama/orchestrator_controller/`; no duplicate claim writer |
| Orama | `docs/v2/references/` | This set; amendments link rather than duplicate authority |
| PT | `.agent/tools/learn.py`, memory | Additive per-slice evidence and lessons through tooling |
| Telos / Phylax / Agate | Canonical owning interfaces | Only verified missing contracts, in their own repos, with consumer qualification |

## Interface vocabulary (proposed; fully typed and schema-versioned before code)

Functions return discriminated outcomes, never truthy Booleans.

| Interface | Consumes | Produces / owner |
| --- | --- | --- |
| `admit_artifact(binding, context)` | `ArtifactBinding` + authenticated context | `AdmissionDecision`; Oramasys using Phylax/Agate |
| `request_exception(operation, refusal)` | Operation key + eligible refusal | `ApprovalRequestId`; Oramasys |
| `decide_exception(request_id, decision)` | Authenticated decision | `GrantReceipt`; Oramasys |
| `reserve_effect(intent, grant_ref, expected_version)` | Intent + optional grant + CAS version | `ReservationOutcome`; Oramasys |
| `authorize_dispatch(reservation_id, epoch)` | Valid reservation + live gates | `DispatchPermit` or refusal; Oramasys |
| `dispatch_effect(permit, request)` | Bound request + permit | `ProviderOutcome`; adapter through Telos |
| `reconcile_effect(operation_key)` | Logical identity + stored evidence | `ProviderOutcome`; Oramasys/adapter |
| `prepare_continuation(checkpoint_id, context)` | Checkpoint + resume context | `ResumeDecision` + neutral cursor; Oramasys |
| Core continuation entry | Validated cursor + state + protocols | Same scheduler observations; signature fixed in the R4 subsystem spec |

No task may rely on an undefined record or an unapproved seam.

## T0 — Inventory and contract freeze

**Deliverable:** immutable source/evidence manifest and subsystem specs. **Dependency:**
human review. No production feature is enabled.

- [ ] Read root and nested instructions and the active PR inventory; resolve merged
  baselines and surviving branches. Do not revive merged PRs.
- [ ] Re-check the D-LG-7 number; capture exact source versions, tree and fixture digests,
  dependency manifests, workflow pins, environment locks and import locations.
- [ ] Enumerate every deferred requirement from docs 57–59, D-LG-1–7, the rev-2 plan and
  named adjacent designs; give each an ID, owner, disposition, dependency and test.
- [ ] Inventory Python and JS API/version cohorts and the retained-v1 concepts.
- [ ] Check production and candidate pins, complete registry profiles and combined-branch
  behaviour. Plan P0 below as a bounded prerequisite.
- [ ] Freeze T1–T5 typed records, schema migrations, failure taxonomy, the
  [clock policy][clock-policy] and exact file and test commands. Review them.
- [ ] Clean bootstrap, build and import; run affected exact-head suites. Missing required
  fixtures or oracle cells fail. Record environment failures apart from bugs.

**Gate:** every known requirement has a disposition, no competing owner, no stale pin or
status claim. Attach a source-coverage map; do not assert every repository-wide deferred
item was found if its source was not reviewed.

## P0 — Bounded R3 pin promotion (prerequisite to M1)

Production Core in Oramasys stays at the pre-R3 commit until this passes; the candidate
file is test-only. Steps: confirm the merged immutable Core commit; promote the production
pin; flip the registry (planned → implemented for the R3 fields, add the new records, drop
the provisional join edge kind) together with the byte-identical snapshot and pinned digest
in one reviewed step; clean-install against the committed pin and run the complete affected
suites. Candidate overlays prove candidates only; preserve earlier profiles as history.

## T1 — Artifact admission and policy binding

**Contract:** [admission](CONTRACT-ARTIFACT-ADMISSION.md). **Owner:** Oramasys, Phylax
interfaces.

- [ ] Write and run the failing tests named in the contract (§5).
- [ ] Implement canonical artifact binding and actual owner decisions; validate before
  indexing. Callable reference strings never import or authenticate code.
- [ ] Add runtime route and budget checks and revalidation triggers; test stale provider
  contracts and absent enforcement services.
- [ ] Run focused tests, owner and consumer regressions, conformance; review; commit.

## T2 — Observation criticality, budgets and cancellation

**Owner:** Core for neutral delivery; Oramasys for terminal policy and accounting.

- [ ] Failing tests: critical-checkpoint outage, listener mutation, slow telemetry and
  backpressure, cancellation with partial streams, repeated restarts.
- [ ] One rich-observation drain with detached payloads. Critical persistence failure
  blocks progress; non-critical telemetry fails visibly and separately.
- [ ] Preserve ordering and post-commit provenance; no observer schedules nodes. Bound
  buffering and define consumer disconnect behaviour.
- [ ] Persist run-wide step, time, cost and effect budgets; retries, nested runs and
  restart never reset them. Distinguish completed, interrupted, cancelled, refused, budget
  and unknown.
- [ ] Prove a stop prevents the next dispatch, not merely hides the stream. Review; commit.

## T3 — Approval and effect transaction spine

**Contract:** [durable HITL and effects](CONTRACT-DURABLE-HITL-EFFECTS.md). Reuses
controller ownership, not its key space.

- [ ] Failing tests before code: concurrent single-use, wrong digest, restart-pending,
  denied/expired/revoked, changed artifact, every crash window in the contract table.
- [ ] Versioned SQLite schema and migrations, unique logical operation keys, immutable
  events, CAS projections, scoped grants and reservations, dispatch outbox.
- [ ] Revocation on both sides of dispatch authorization; operation-key reuse with a
  different request; corrupt records; UTC expiry after restart and clock regression.
- [ ] Backup, restore and redaction. Review schemas and security; commit. Grants alone
  never enable production transport.

## T4 — One qualified foreign-provider transport

**Contract:** [transport](CONTRACT-FOREIGN-PROVIDER-TRANSPORT.md). Consumes T3 permits.

- [ ] Failing tests named in the contract (§6).
- [ ] Real transport injection or a contained worker; enumerate SDK side paths; refuse any
  uncontained path. Never copy Telos security semantics.
- [ ] Deadlines, stable provider keys, dedupe retention limits, usage receipts, confirmed
  and unknown outcomes; reconciliation tested independently.
- [ ] Local controlled-server integration first; then explicitly authorized sandbox
  credentials for named cells. Default CI stays offline.
- [ ] Review network evidence and provider limits before opt-in; publish the cell contract.

## T5 — R4 cursor, frontier and effect-aware continuation

**Contract:** [continuation](CONTRACT-DURABLE-CONTINUATION.md). Consumes T1–T4 and merged R3.

- [ ] Failing tests named in the contract (§5).
- [ ] Neutral cursor and checkpoint protocols at the existing seam; storage adapter outside
  the engine; ordinary `invoke` preserved.
- [ ] Persist cursor, state and receipt application together, or a tested prepare/commit
  recovery. Kill and restart real subprocesses at every durable boundary.
- [ ] Delay-permutation, interrupt-precedence, unknown-effect, fencing, budget, migration,
  fork, custom-reducer and provenance tests; mutated unsafe variants must be caught.
- [ ] Review; commit. Promise no provider exactly-once.

## T6 — Replacement cohorts and retained-v1 register

**Contracts:** [compatibility](CONTRACT-COMPATIBILITY-REPLACEMENT.md),
[retained concepts](REGISTER-RETAINED-V1-CONCEPTS.md). Pure work may start after M0;
effectful cells wait for M3. Missing neutral mechanics need a Core ADR first.

- [ ] Matrix runner tests that fail for missing cells, silent skips, unsupported versions,
  stale artifacts, incomplete inventories.
- [ ] Pure facade primitives, then Runnable, config, callback and stream contracts, with
  unchanged pinned upstream fixtures beside native equivalence tests.
- [ ] Namespace, type, pickle, metadata, subprocess identity and cached-import refusal;
  tiered errors, finder-returning-None, `importorskip`, computed lazy imports.
- [ ] Golden fixtures for retained-v1 translations and prohibited ownership leakage; v1
  builds stay independent of v2 dependencies.
- [ ] Publish exact per-cohort counts, drift tests and rollback compatibility.

## T7 — Pydantic AI through the same effect boundary

Consumes T3/T4/T5. The agent provider stays an untrusted effect source even when a graph
tool is pure.

- [ ] Preserve the import-free graph-as-tool and one explicit lazy allowlisted agent import.
- [ ] Failing tests: mixed approved tools, edited arguments, pending restart, provider
  retries, usage exhaustion, streamed-tool cancellation.
- [ ] Map authenticated durable outcomes into pinned deferred-tool results; approve only
  exact individual requests. New arguments invalidate the old grant.
- [ ] Offline TestModel/FunctionModel oracles with sockets blocked, then qualified sandbox
  cells. Unsupported production cells stay refused.

## T8–T10 — Follow-on slices

Each needs its own source-backed subsystem spec and approval before code.

| Task | Scope | Sources / gate |
| --- | --- | --- |
| T8a | Dynamic Send, nested regions/subgraphs, optional early-cancel joins | Docs 57–59 + D-LG-6; reviewed mechanics and version semantics |
| T8b | Full LC/LG inventory; LangGraph.js/oramaclaw | T6 matrix; separately pinned runtimes |
| T8c | Evaluation, autoresearch, graph optimization | Doc 57 §14; fixed evaluator, held-out data, explicit promotion |
| T8d | Anamnesis, retrieval, private memory | Docs 20/41/56/67; provisioned backend, poisoning/privacy/deletion |
| T8e | Observability and monitorability hardening | Docs 55/60; sanitized projections, freshness, retention |
| T9a | Controller claims, identity/envelopes, renewal, emergency stop | Docs 49/50/61/68/69; one writer, stop and fencing tests |
| T9b | Portal cancel and approval rollback, mixed deploy | Doc 70 + cancel contract; only positively safe rollback restores a claim |
| T9c | Gateway placement, provider readiness/lifecycle | Docs 17/42/62/66; observed readiness, unknown-launch reconciliation |
| T9d | Optional MCP/A2A/mesh, skill/tool supply chain | Docs 23/24/32/43/50; least privilege, pinning, no projection authority |
| T10 | H1 remote workers, then H2 | [Multi-host](CONTRACT-MULTI-HOST-STAGES.md); docs 45/49/68 |

T8c researchers may mutate candidates, not the evaluator, safety policy or acceptance
tests; promotion is versioned and reversible, with no live topology rewrite from a
natural-language suggestion. Retrieval is not a prerequisite for the approval store;
public Class-0 documentation search stays its shipped read surface.

## Milestones

| Milestone | Tasks | Exit gate |
| --- | --- | --- |
| M0 | Human review + T0 | Reviewed contracts, current baselines, complete scoped inventory |
| M1 | P0, T1, T2 | Real admission, reliable observations, production consumer requalified |
| M2 | T3 | Restart-safe requests, grants, reservations, effect intents |
| M3 | T4, T5 | Qualified transport; true continuation with unknown-effect protection |
| M4 | T6, T7 | Declared cells proven; no unsupported parity label |
| M5 | Selected T8/T9 | Each adjacent capability independently qualified |
| M6 | T10 | Remote or larger deployment only for qualified stages |
| Closure | T11 | Pins, evidence, memory and handoff agree with shipped behaviour |

T5 neutral cursor work may develop beside T4 once T3 contracts stabilize, but production
recovery cannot ship without effect reconciliation. Avoid broad parallel implementation
against moving interfaces.

### Evidence tiers

Framework-free native contracts → pinned real offline upstream oracles → crash,
concurrency and mutation tests → controlled local transport → explicitly authorized
provider sandbox → H1/H2 multi-host qualification. Record each tier's artifact and
environment identity.

## T11 — Coordinated pins, publication, PT memory closure

Two pairs: **Core ↔ Oramasys** (runtime producer/consumer) and **Orama ↔ PT**
(design, evidence, memory). Coordination does not require unrelated edits in all four.

- [ ] Record a batch manifest of touched and unaffected surfaces and the next gate.
- [ ] Refresh the candidate SHA after every producer fix; R3/R4 cells run in their required
  lane. A missing dependency is never an accepted skip.
- [ ] Promote only a reviewed immutable merged producer revision; update the dependency,
  lock and source files actually in use, registry, snapshots, digests and docs workflow
  pins; keep earlier profiles as history.
- [ ] Clean-install the consumer against the committed production pin and run complete
  affected native and oracle suites.
- [ ] Publish canonical Orama evidence before PT memory. Use current PRs when scope fits;
  PT #432 remains the named memory destination while open.
- [ ] If shell Git auth fails, distinguish it from connector capability and record the
  actual publication method and verified remote tree identity.
- [ ] Re-read remote heads, CI and review threads after publication. A REST reply is not
  thread resolution; verify GraphQL or connector resolution separately.
- [ ] PT memory through its tooling: keep prior JSONL prefixes byte-for-byte, add superseding
  lessons, render only the canonical `LESSONS.md`.
- [ ] Record why each gate exists, what falsifies it and the next step. Documentation
  closure is never runtime closure.

Rollback uses reviewed forward or revert commits and the last qualified producer/consumer
pair. R4 checkpoints are not readable by older code by downgrading a pin.

[clock-policy]: CONTRACT-DURABLE-HITL-EFFECTS.md#5-clock-policy-approved-freeze-implementation-details-at-t0
