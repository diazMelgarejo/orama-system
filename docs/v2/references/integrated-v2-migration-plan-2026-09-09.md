# Integrated v2 migration implementation and execution plan

Date: 2026-09-09. Read the [reconciliation](migration-harmonization-2026-09-09.md) first.
This is the approved planning baseline, not evidence that the runtime migration is finished.
The source repositories remain independent; no mixed-organization runtime regime is acceptable.

## Ownership and interfaces

| Repository | Owns | Must not silently absorb |
| --- | --- | --- |
| `oramasys/perpetua-core` | Small reusable execution/kernel primitives and stable contracts | Application policy, machine discovery, provider operations, private memory storage |
| `oramasys/oramasys` | Application orchestration, GraphSpec, control plane, integration API/UI, accounting and methodology | A replacement copy of every specialist implementation |
| `oramasys/agate` | Hardware inventory, capability/availability and fit decisions | Endpoint-use authorization or provider serving lifecycle |
| `oramasys/telos` | Endpoint-use semantics, scope, expiry, revocation and lifecycle contracts | Unreviewed expansion into every transport mechanism |
| `oramasys/phylax` | Admission, security enforcement, monitorability, provenance and reusable hygiene guards | Prompt-only assertions of safety or six manually divergent guard copies |
| `oramasys/anamnesis` | Portable memory contracts, sanitized records and derived retrieval | A raw copy of private v1 memory |
| `oramasys/Claude-Desktop-LLM` | Provider operation and health/readiness, subject to source verification | Hardware policy or global orchestration ownership |
| `oramasys/alexandria` | New current v2 documentation with source lineage | Bulk imported v1 archives or runtime implementation |

Contract ownership is singular; adapters may be multiple. Resolve the owner of the reusable
endpoint parser/dialer explicitly, preserving Telos semantics and Phylax admission separation.
Do not block independent inventory or documentation on that decision.

## Required coverage ledger

Create a machine-readable ledger in a successor repository. Each relevant source file and each
capability must be accounted for; file inventory alone cannot establish behavioral coverage.
Fields: source repository, source commit, path, symbol/capability, behavior, source tests,
destination owner/path, disposition, dependencies, target evidence, acceptance cases, status,
decision reference, and reviewer. One source may map to several explicit capability rows.

Allowed dispositions: extract, adapt, reimplement, consume specialist, retain a documented
compatibility facade, historical-only, or explicitly accepted exclusion. No unclassified row
may disappear through a file-count summary. An exclusion needs a reason and a decision record.
Statuses: inventoried, specified, implemented, verified, accepted exclusion, or blocked with
the exact missing input. Mark a row verified only for the tested artifact revision.

Inventory PT packages, orchestration, launchers, configuration, hardware, provider adapters,
memory protocols, contracts and test fixtures. Inventory Orama agents, skills, MCP interfaces,
API/UI, plugins, policy, documentation and generated adapters. Record binaries and inaccessible
private assets as explicit access gaps rather than inventing their contents.

## Execution waves and exit evidence

| Wave | Work and dependency | Reviewable output | Exit condition |
| --- | --- | --- | --- |
| M0: baseline | Pin all source/target revisions, active PRs and access; record regime authority | Snapshot/provenance manifest and boundary ADR | Source freeze and the narrow documentation exception are explicit; no access claim is assumed |
| M1: coverage | Inventory all files, contract surfaces, workflows and instructions | Complete classification ledger with evidence links | No unclassified in-scope source; omissions and exclusions visible |
| M2: foundations | Establish v2 owner guides, reproducible builds, declared commands, versions and CI | Small target PRs, dependency graph and governed adapter discovery | Each applicable target builds/tests without v1; layout exceptions documented |
| M3: contracts | Specify cross-package requests, events, results, identity and failure semantics | Versioned contracts and conformance fixtures | Producers/consumers agree; denial and malformed inputs are covered |
| M4: specialists | Implement Agate, Telos, Phylax, Anamnesis and provider slices | Independently testable packages and adapters | Real behavior, lifecycle, enforcement and negative cases verified |
| M5: Core | Mine PT contracts and keep only reusable kernel responsibilities | Thin kernel with state isolation and deterministic contracts | Compatibility and affected-consumer tests pass without application-policy leakage |
| M6: Oramasys | Integrate graph execution, control plane, budgets, accounting, effects, API and UI | End-to-end vertical slices | A complete user workflow runs with v2 packages only, including failure handling |
| M7: knowledge | Sanitize copied memory; regenerate derived data; synthesize new docs and skills | Private import evidence, public category report, v2 documentation and generated wrappers | Provenance/identity preserved; no unresolved leak; docs match verified behavior |
| M8: assembly | Build clean versioned release candidate with legacy repos absent | Compatibility matrix, artifact digests and integration evidence | Required release gates pass on the actual candidate and supported environments |
| M9: release | Prepare target/environment/effects/rollback packet; obtain required approval | Reviewed release packet and, after approval, rollout evidence | Approved effects succeed; recovery and final acceptance are verified |

M0 precedes M1. M2 and M3 define foundations for M4–M6. Contract-independent specialist work
may proceed concurrently when ownership is clear. M7 documentation and skill classification can
proceed early; memory import waits for sanitation and Anamnesis access. M8 requires all selected
release capabilities verified. M9 cannot substitute approval for missing M8 evidence.

Claude wave mapping: wave 0 maps to M0–M2; wave 1 to M2–M3; wave 2 to the memory part of M7;
wave 3 to Alexandria work in M7; wave 4 to skill classification/generation in M1/M7; wave 5 to
M8–M9. M4–M6 restore runtime work that the source plan understated.

## M3–M6: concrete implementation slices

Specify execution/routing requests, endpoint-use records, hardware snapshots, policy decisions,
memory operations, events and accounting. Define versions, principal identity, expiry, retries,
cancellation, typed errors, idempotency, backpressure and failure propagation. Unknown or
malformed mutating operations must not acquire permission by default.

Agate needs runtime inventory and decisions beyond its current schema scaffold. Telos needs
versioned endpoint-use lifecycle tests, including expired and revoked records. Phylax needs
actual call-path enforcement and adapter registration: prose plus a verifier function that is
never invoked does not establish admission. Anamnesis needs a reviewed import contract and
private storage boundary. Provider readiness must distinguish a live process from a usable
model endpoint. Its tree was inventoried here; provider runtime was not fully audited.

Classify Core graph/state/message/discovery/policy/LLM surfaces by reusable behavior before
moving code. Preserve intentional compatibility names without making v1 a dependency. Verify
state isolation, cancellation and deterministic execution where promised.

In Oramasys, implement graph gateway/control-plane integration with principal and source
references, heartbeats, safe transport, budgets, accounting and effect boundaries. Mine the
intent and fixtures behind legacy Gate 4 and PT PR382 into a v2 slice. Do not finish the legacy
implementation PR as a prerequisite of this migration. UI acceptance needs a rendered check
for the touched view plus programmatic behavior evidence.

## M7: approved memory procedure

1. Pin the PT source revision and obtain a read-only snapshot into private staging outside git.
2. Inventory record formats, IDs, counts, provenance, dates, status and cross-record references.
3. Run generic secret, topology and personal-path checks plus the private literal registry.
   The registry is an extra layer; its absence must not disable generic checks.
4. Sanitize source records in the migration copy with structured parsers and deterministic rules.
   Keep raw evidence privately where authorized. Do not delete source rows to make counts pass.
5. Regenerate materialized views, search indexes and embeddings from sanitized source text.
6. Verify stable IDs, relationships, status, lineage, supersession and intended semantics, not
   only row counts. Scan both source and derived output; publish only categories and counts.
7. Repeat the process to prove idempotency; resolve baseline differences against pinned inputs.
8. Import through the reviewed Anamnesis contract once access exists. Record rollback and
   verify retrieval. Do not fall back to Core or turn a documentation task into a memory push.

The source runbook's proposed scanner flags are not an existing CLI contract. Implement a v2
tool with tested argument parsing and redacted reports before adding runnable commands here.
Unresolved leaks block data import; they do not block unrelated contract or documentation work.

## M7: skill and documentation procedure

Inventory every source skill and wrapper. Keep meaningful selection boundaries; historical-only
does not mean deleted. Oramasys owns shared methodology and the wrapper generator under
`src/tools/`; specialists own domain workflows. Generate supported names/descriptions and
harness-specific pointers, not permission grants. Test deterministic generation and drift.
Loading a skill must not fetch, pull, install, import memory or rewrite its checkout.

Author new Alexandria documents from reconciled current behavior and accepted decisions.
Each document records pinned v1 source lineage where relevant. Preserve historical numbering as
provenance, not as an invented file path. Authority transfers by an explicit coverage/acceptance
record, not by copying the old archive. Keep build commands and non-obvious conventions close
to the code; keep historical incidents and long procedures behind relevant links.

## Approval, continuation and completion

Continue authorized read-only work, scoped implementation and relevant local diagnosis until
the requested deliverable is complete. Reuse existing authorization for the same target/effects.
Do not halt on an expected regression test failure or a routine resolvable error. Stop for user
input only when a material choice cannot be inferred, necessary access is unavailable, or the
next consequential action needs authorization not already supplied.

External messages, deployment, production data migration, destructive deletion, history rewrite,
credential rotation and permission expansion each require authorization for their actual effects.
Prepare a concrete artifact first. A requested draft PR may notify subscribers; distinguish that
authorized publication from unrelated messages. Never bypass an enforced rejection.

For release, include commits, dependency versions, artifact digests, target environment, exact
validation, migration/backup/recovery steps, expected effects and rollout/rollback triggers.
Rollback uses a known-good v2 release; the existing v1 system remains independently available.
Complete the program only when the ledger is closed, selected workflows work without v1,
required safety gates operate in the real harness, and acceptance evidence is recorded.

## Execution ledger at this publication

| Item | Status | Next evidence required |
| --- | --- | --- |
| All five Claude inputs read and preserved | Complete | Original-entry hashes are in the provenance manifest |
| Source/target main snapshots rechecked | Complete for listed repositories | Refresh before each implementation batch |
| Audit and combined planning package | Prepared for publication | Remote commit/PR verification is reported in the handoff |
| Exhaustive capability ledger | Pending | Every source capability classified; current file inventory is insufficient |
| Runtime migration and instruction fixes | Not executed in this documentation batch | Target PRs and applicable test evidence |
| Anamnesis access | Blocked: lookup returned 404 | Confirm access or provision through an authorized owner |
| Parser/dialer shared owner | Open design decision | ADR defining ownership and avoiding a policy/transport cycle |
| Private design skill and raw memory scan | Not independently inspected | Private, redacted evidence at a pinned revision |
| Classic branch protection | Inaccessible to integration | Owner-provided evidence; empty rulesets do not prove no protections |
| Existing legacy PRs | Observed, unchanged | Separate decisions; do not make them migration dependencies |

No completion percentage is assigned until the capability denominator exists. Estimates in the
preserved source reports are historical estimates, not a release claim.
