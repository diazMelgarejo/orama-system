# P0 through T2 execution plan

> Execution instructions superseded by the
> [revision-2 review proposal](P0-THROUGH-T2-EXECUTION-PLAN-REV2-2026-10-10.md).
> Retained as the first reviewed plan, including the claims corrected in revision 2.

**Status:** execution roadmap for review. **Scope:** P0 production-pin qualification,
then T1 artifact admission and T2 observation/budget work. **Authority:** this plan
implements the boundaries in [PLAN-R4-EXECUTION](PLAN-R4-EXECUTION.md) and does not
authorize T3 effects, provider transport, durable continuation, remote workers, or a
claim of exactly-once delivery.

## Invariants that apply to every slice

- Production uses immutable Core merge commit
  `4d217f6b9e94e36554a9427198b8c2c4b7febc47`; historical lanes retain their own
  immutable pins.
- Orama owns canonical registry bytes; Oramasys owns its byte-identical consumer fixture.
  A canonical checkout, selected fixture and pinned digest must agree or the lane fails.
- A required cell never passes through a skip. A candidate overlay is never proof of a
  production install.
- Each slice begins with a failing behavioral test, has one logical commit, is reviewed
  before merge, and reports implemented, verified, published, reviewed, merged and enabled
  separately.
- No history rewrite, force push, branch deletion or mutation of append-only evidence.

## P0 — promote the qualified R3 consumer baseline

### P0.1 Canonical registry

| Owner | Deliverable | Verification |
| --- | --- | --- |
| Orama | Promote `ownership-registry.json` to the schema-2 R3 production profile; retain `ownership-registry-pre-r3.json`; retain policy-r3 and core-r3 candidate profiles with their historical Core pins | JSON parses; production/profile metadata is explicit; SHA-256 values recorded; Orama/Oramasys production bytes compare equal |
| Orama | Correct [PLAN-P0-CORE-PIN-PROMOTION](PLAN-P0-CORE-PIN-PROMOTION.md) and publish this roadmap | Links resolve; wording does not claim qualification or enablement |

### P0.2 Consumer promotion

| Owner | Deliverable | Verification |
| --- | --- | --- |
| Oramasys | Explicit profile selector in `test_ownership_registry.py`: default production, policy-r3 and core-r3 only when requested; fail unknown profile | Red test: R3 Core with old automatic selection fails; green test: production selects baseline |
| Oramasys | Promote `pyproject.toml`, active graph-spec assertion and production workflows to Core merge commit; pin CI checkout to the merged Orama registry revision | Clean environment resolves exact commit; workflow inputs use full immutable SHAs |
| Oramasys | Replace baseline fixture with exact canonical bytes; retain candidate and pre-R3 fixtures; pin all profile digests | Mutation tests reject stale digest, changed canonical byte, wrong profile, wrong pin and implemented/planned drift |
| Oramasys | Matrix qualification: production Core R3 + production profile, historical pre-R3 + policy-r3, historical R3 candidate + core-r3 | Required cells run on Python 3.11 and 3.12; profile/incompatible-Core combination fails instead of skipping |
| Oramasys | Run a clean production installation from committed manifest without an editable Core overlay | `pip check`, installed Core identity and complete native/offline-oracle results recorded |

### P0.3 Evidence and closeout

1. Re-read Core, Orama and Oramasys heads immediately before each publication.
2. Merge canonical Orama registry change first; capture its exact merge SHA.
3. Update the Oramasys workflow pin to that SHA, run all P0 lanes at the exact head, and
   resolve review findings.
4. After the operator merges the Oramasys PR, add a new dated Orama P0 evidence record.
5. Add one PT append-only memory record through the native tooling, citing only observed
   merged SHAs. Do not modify T0.

**P0 exit:** production pin, production profile, canonical registry, consumer fixture,
digests, workflow revision and clean-install evidence agree; all three profile lanes are
qualified at their own immutable revisions.

## T1 — artifact admission and policy binding

### T1.1 Contract freeze

| Owner | Interface | Required outcome |
| --- | --- | --- |
| Oramasys | `ArtifactBinding` | Immutable artifact digest, declared owner, graph/policy identity, version and provenance references; callable strings are data, never imports |
| Oramasys with Phylax/Agate interfaces | `admit_artifact(binding, context) -> AdmissionDecision` | Explicit admit/refuse result with category, evidence references and revalidation trigger; no truthy Boolean |

### T1.2 Test-first implementation

1. Write focused failing tests for unsigned/unknown artifacts, owner mismatch, stale provider
   contract, graph-id mismatch, capability/budget refusal, absent enforcement service and
   callable-reference non-import.
2. Add typed records and pure validation before indexing. Preserve existing graph-policy
   binding behavior and fail closed at the boundary.
3. Add the owner/Phylax/Agate adapter only through its declared contract. Absent service
   returns a structured refusal; it never falls back silently.
4. Add route/budget revalidation tests and consumer regression tests.
5. Run native suite, offline conformance, static import/security checks and targeted mutation
   cases. Publish a T1 evidence record before PT memory.

**T1 exit:** every admitted artifact has canonical identity and owner evidence; every missing,
stale, mismatched or unavailable dependency refuses before indexing or dispatch.

## T2 — observations, cancellation and durable budgets

T2 is two coordinated but independently reviewable slices. Core owns neutral event delivery;
Oramasys owns terminal interpretation, accounting and cancellation policy.

### T2-A Core neutral observation delivery

1. Freeze a typed observation record with run/step ordering, provenance, criticality,
   detached payload and explicit delivery outcome. It must not schedule nodes.
2. Write failing Core tests for listener mutation, a slow non-critical listener, critical
   persistence failure, ordering across fan-out, backpressure and repeated subscription.
3. Implement one ordered drain: detach payloads, bound buffering, surface non-critical
   telemetry failure separately, and block progress when critical persistence fails.
4. Run Core graph/fan-out/reducer suites and mutation tests. Do not add provider, approval
   or persistence semantics beyond neutral delivery.

### T2-B Oramasys terminal policy and accounting

1. Freeze typed terminal outcomes: completed, interrupted, cancelled, refused, budget,
   unknown. Define a run-wide budget record for step, time, cost and effect limits.
2. Write failing tests for cancellation during partial streams, cancellation before next
   dispatch, retry/nested-run/restart budget persistence, disconnect behavior and a
   critical-observation refusal.
3. Implement accounting outside the Core scheduler. A stop prevents the next dispatch; it
   does not merely hide later stream events. Retries and restarts cannot reset limits.
4. Run focused tests plus production-profile graph/compatibility suites, then a combined
   Core/Oramasys qualification at immutable heads.

**T2 exit:** neutral observation order and criticality are proven; cancellation is operational;
budget and terminal state semantics survive retry, nesting and restart without giving observers
scheduling authority.

## M1 readiness and exclusions

M1 requires merged, qualified P0, T1 and T2 evidence. It does not enable T3 approval/effect
transactions, T4 provider transport or T5 durable continuation. The current `ainvoke`
behavior restarting at `START` remains an explicit non-continuation fact until T5 passes.
