# MiniGraph external compatibility convergence

**Status:** direction confirmed by the user on 2026-10-09; implementation unproved
**Scope:** v1 evidence and v2 architecture only; no runtime implementation

**Revision 3:** [execution index and preserved inputs](../references/loop-graph-compatibility-2026-10-09/README.md)
and [current resolutions](../references/loop-graph-compatibility-2026-10-09/REVISION-3-RESOLUTIONS.md)
qualify every historical statement below. Core's bounded adapter fix is local,
not yet published at that revision-3 cutoff. The subsequent four open PRs and
approved D-LG-1/D-LG-4 implementation are qualified by
[revision 4](../references/loop-graph-compatibility-2026-10-09/EXECUTION-REVISION-4.md).
The full replacement program is not implemented.

## Purpose

The target is best-effort external LangChain/LangGraph parity through our
compatibility layer, including unchanged caller fixtures in replacement mode.
All existing hardware, authorization, and egress rules take precedence. Every
supported package version, Python version, entry point, import path, observable
event, error, and persistence behavior needs independent evidence. Execute
automatically when allowed; document every refusal and provide HITL escalation
for the human operator to approve an authorized exception or policy change.

Until the release matrix below is complete, use the existing wording from doc
57: compatibility for the supported builder/topology and invoke/stream surface.
Do not use "100% drop-in compatible" for an adapter that only resembles an API
or exports topology into another scheduler.

## Corrections to carry forward

1. The current LangChain-shaped adapter executes the Core graph. It is not a
   topology-only exporter. `abatch()` honors `max_concurrency`; most other
   Runnable configuration semantics remain unproved.
2. The LangGraph exporter exports topology and node callables. Its compiled result executes under
   LangGraph's scheduler, not MiniGraph's: MiniGraph interrupt handling,
   `nodes_visited`, and `max_steps` behavior do not transfer.
3. Final state plus a total order of routing choices is not sufficient evidence
   of equivalence. LangGraph's superstep execution makes same-step writes
   invisible to other actors until the update phase. Parallel event ordering
   must be checked as a partial order where the public contract permits it.
4. Reducers and checkpoints are prerequisites for important behavior, but they
   do not alone establish full compatibility. Types, imports, configuration,
   streaming, failures, cancellation, composition, and persisted wire formats
   also belong to the external contract.
5. A package test extra declares a dependency. If normal packages must have no
   LangChain/LangGraph dependency metadata, run upstream oracle suites in
   separate locked development environments. Keep intentional lazy outward
   bridges explicitly allowed and isolated.

## Compatibility contract before implementation

The user confirmed both replacement compatibility and interoperability on
2026-10-09. V2 has no deployed users imposing a migration constraint; its
internal design can change freely to satisfy this contract. All public
LangChain/LangGraph calls are the destination, including events, checkpoint
interfaces, configuration, errors, streaming, and composition. Publish exact
upstream releases and interpreter versions as the proof boundary; version pins
make the claim testable and do not reduce the intended public API coverage.

| Scope | Meaning | Evidence needed |
| --- | --- | --- |
| Interoperability | Our adapter works with real installed framework objects | Bidirectional composition and integration fixtures |
| Namespace compatibility | Callers change imports to our namespace but retain logic | Public-symbol and behavior matrix |
| Replacement compatibility | Existing upstream imports and application code stay unchanged | Package/import identity, wheel metadata, and unchanged caller fixtures |

The user's later clarification on 2026-10-09 makes parity always best effort,
subordinate to all enforcement rules. Full public API coverage remains the
destination, but it is not an unconditional behavioral guarantee. Report exact
parity coverage, policy refusals, and implementation gaps separately for each
pinned matrix. LangGraph.js/oramaclaw has a separate contract and release matrix.

## Framework-free defaults and automatic interoperability

Normal installs declare no LangChain/LangGraph runtime requirement and execute
through our engine. An installed framework is detected lazily when a caller
enters its compatibility boundary. Inspect installed distribution metadata and
the caller's object/protocol; import only the specific bridge then needed.
Do not eagerly import every optional framework during normal startup.

Detection selects a versioned translation bridge, never a replacement scheduler.
The presence of LangGraph must not silently cause our graphs to execute through
the upstream runtime. Use our facade when frameworks are absent and translate
real caller objects when supported frameworks are present. Both paths must pass
the same behavioral fixtures. An installed version with unproved compatibility
produces an actionable compatibility error when that bridge is requested; a
broken optional install must not be mistaken for an absent one or silently
change semantics.

Keep one compatibility implementation in `oramasys/oramasys`, with
neutral scheduler/state contracts and the two existing adapters in Core.
Build on those adapters rather than duplicate them. Offer both our explicit namespace
and an explicit replacement installation/launcher mode for unchanged upstream
imports. Automatic detection alone cannot reroute an application's existing
imports. Do not overwrite an installed framework's files or globally monkeypatch
it merely because it was detected. The precise replacement packaging is a
design task, not a shipped capability.

Provider integrations that need their own SDKs retain caller-supplied optional
dependencies. The default installation does not download frameworks, provider
SDKs, or credentials to manufacture interoperability.

## Earlier decisions and their resolution

| Record | Earlier statement | Resolution from the current direction |
| --- | --- | --- |
| Doc 25 section 5 | Real application tests behind the same interface prove the drop-in claim | Keep as an integration gate; one application's tests do not establish every public API |
| Doc 57 section 17 | Supported API only; exact events and saver serialization excluded/future | Keep as the honest current capability; full fidelity is now the destination, with these rows still unproved |
| PT observer reconciliation | One scheduler; Pydantic AI patterns without its runtime | Preserve the scheduler boundary and the Pydantic AI decision |
| Uploaded D-LG-2 sections 1 and 5 | Frameworks only as test targets; no non-test imports | Superseded for caller-installed LangChain/LangGraph bridges; default packages remain framework-free |
| Uploaded D-LG-2 section 3 | Runnable config accepted but unused | Correct: batch concurrency is implemented; most remaining config semantics are unproved |

Source records: [doc 25](../25-autoresearcher-doctrine-and-againtra-flagship.md),
[doc 57](../57-minigraph-final-reconciliation.md), and PT
`.agent/memory/semantic/MINIGRAPH_OBSERVER_PATTERN_RECONCILIATION_2026-08-27.md`.
The uploaded ADR and historical sources remain intact. This follow-up records
the user's later resolution. It does not extend the decision to Pydantic AI
runtime adoption or change the independence of v1 PT/Orama from v2.

The user resolved the enforcement boundary on 2026-10-09: apply ALL existing
hardware, authorization, and egress rules; upstream parity is always BEST EFFORT.
The earlier full-parity goal is qualified by this later instruction, while the
original historical records remain intact.

## Automatic admission, refusal evidence, and HITL escalation

1. Resolve the operation and run all applicable admission checks before its
   effects. Execute automatically when every required gate allows it.
2. For any disallowance, stop the affected operation before dispatch or egress.
   Produce a structured refusal plus an operator-readable explanation; expose
   an escalation request. Independent work may continue only where its own
   admission and dependency checks permit it.
3. Record operation/request identity, upstream API and version, policy version
   and rule IDs, refusal reason, expected upstream behavior, attempted action,
   remediation options, and escalation state. Preserve every returned denial;
   do not claim this necessarily enumerates all rules that would also deny a
   request. Keep raw secrets and sensitive topology out of exported evidence.
4. An authenticated human operator reviews the precise requested exception or
   policy change. Bind approval to operator identity, operation/request digest,
   policy revision, scope, expiry, and use limits through the new
   [durable approval contract](../references/2026-10-09-compatibility-refusal-hitl-contract.md),
   not an already-shipped mechanism. Until implemented, override paths remain
   denied/pending. Missing, rejected, expired, revoked, or out-of-scope approval
   leaves the operation denied. An agent or upstream caller cannot self-approve.
5. Re-run all gates under the approved policy/exception before execution and
   after resume or relevant target changes. Approval for one denial does not
   authorize another denial, redirect, destination, workload, or action.
6. Preserve the original refusal, approval/rejection, policy change, revalidation,
   and eventual outcome as linked append-only evidence. Avoid duplicate effects
   through the stable operation identity described below.

Every blocked parity operation can be presented for HITL review. Approval is
implemented through the authoritative policy's supported exception or change
path, not by skipping checks. Physical infeasibility, invalid authentication,
or an invariant with no permitted exception requires remediation or a separately
authorized policy design change; an approval flag cannot make it executable.
Noninteractive runs remain denied/pending until valid operator approval arrives;
they neither grant themselves an exception nor wait indefinitely.

Use existing [hardware enforcement](../17-hardware-policy-enforcement.md),
[security-first controls](../24-security-first-platform.md), and
[Telos/Phylax authority](../62-telos-phylax-authority-gate0-adr.md). Define one
upper-layer approval/refusal contract over these authorities, with no competing
policy implementation in the compatibility adapter or Core scheduler.

## Release matrix

| Surface | Required oracle cases | Current disposition |
| --- | --- | --- |
| Imports and symbols | Public paths, constants, signatures, subclass/type checks, wheel install | unproved |
| Runnable invocation | Input/output schemas, kwargs/config, invalid input, exception type/message | partial |
| Batch and cancellation | Per-input config, ordering, limits, cancellation, mixed success/failure | partial |
| Composition | Both pipe directions with real framework runnables, callable/mapping coercion | unproved |
| Streaming | First-event timing, incremental delivery, stream modes, filters, backpressure, cancellation | partial/unproved |
| Events | Public event schema and causal ordering; only documented nondeterminism normalized | unproved |
| Parallel graph semantics | Supersteps, reducers, joins, conflicts, `Send`, recursion accounting | deferred R3 |
| Interrupt/persistence | Thread identity, checkpoints/history, resume, pending writes, crash recovery | deferred R4 |
| Effects | Provider idempotency/reconciliation, retry, replay, authorization on resume | deferred R4 |
| Refusal/HITL | All disallowances documented; valid scoped approval, denial, expiry, revocation, revalidation, and noninteractive pending paths | planned; not implemented by this document |
| Pydantic AI | Native pattern adoption; optional real agent research fixtures | production bridge deferred to a separate decision |

## R3/R4 contract refinements

Preserve one scheduler. If full superstep behavior needs new universal execution
mechanics, put the smallest neutral seam in Core and keep framework translation
outside the kernel. Do not duplicate the scheduler in adapters.

Effect identity is `(run_id, logical_operation_id)`, plus canonical effect kind
and request digest. Retries reuse that identity; an `attempt_id` records each
try separately. A changed request under an existing logical operation fails
closed. A crash after an external operation but before local completion is an
unknown outcome: reconcile it with the provider or rely on the provider's
idempotency guarantee before retrying. A local "already recorded" flag alone
is not proof that an external effect did or did not happen.

Loop limits and authorization are runtime-owned checks. Node-produced counters
and router predicates can inform routing but cannot be the sole enforcement
mechanism. Revalidate authorization before each external effect and after a
resume.

## Implementation order

1. Inventory the full public API against exact upstream releases. Apply the
   resolved best-effort policy boundary and design the refusal/HITL vertical
   contract; resolve replacement packaging and GraphSpec policy ownership.
2. Build locked, isolated oracle environments. Run the same unchanged fixtures
   against upstream and candidate implementations.
3. Close low-risk adapter gaps: documented config subset, validation of
   concurrency limits, bidirectional composition, and truthful streaming
   behavior.

   B1 is concrete: reject zero/negative/bool/non-integer `max_concurrency`
   before effects, including empty batches. The Core regression tests cover
   async and sync paths. Both v0.x and v1.x upstream release lines remain oracle
   targets; no full parity follows from this neutral adapter fix.
4. Specify and test R3 reducers/joins plus scheduler semantics as one vertical
   contract. Then implement R4 checkpoint lineage and effect recovery.
5. Promote only symbols whose complete release-matrix row passes. Keep all
   others marked supported, partial, or blocked, and retain full public parity
   as the completion criterion. Test absent, installed, incompatible, and broken
   optional frameworks plus mixed real-object and native-facade composition.

## Relation to existing records

This plan adds acceptance evidence; it does not supersede the ownership and
kernel boundaries in [doc 57](../57-minigraph-final-reconciliation.md) or the
R3/R4 sequence in the existing reconciliation plan. Preserve historical
research and memory records, then attach this correction when they claim a
broader compatibility result than their evidence supports.
