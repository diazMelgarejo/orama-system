# E1 C1 source inventory, recovery boundary and test map

Status: proposed evidence reconciliation for independent review. Specification
only; no ratification, runtime change or serving activation. This is C1 in the
task split accepted on GossipBus row 4841. C2 owns the integrated purpose,
permit and role contracts and follows this record in the review stack.

## Frozen source inventory

| Source | Reviewed revision | Relevant contract |
| --- | --- | --- |
| Orama E1 draft and durable HITL/effects contract | `1763bd93f9c9b36206728a1303a40d90233670d7` | Proposed authority, reconciliation, recovery and dispatch ordering |
| Oramasys application and M1 tests | `b5f3821804715665b716ab600ea8419810bea920` | Existing adjustment grants, durable ledger, admission and observation delivery |
| Phylax issuer and verify-only reader | `0c3e860749b3ff8f62e102679f1f415f8acf0a61` | Adjustment-grant schema 1, verification refusal vocabulary, private read-only store |
| G1 review delta | `28f33123ce49df2e0f2381ad0efcbc5a92e1ffc4` | Adds generation records and tests; does not alter those runtime contracts |

Primary sources:

- [E1 draft](E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md).
- [Durable HITL and effects](CONTRACT-DURABLE-HITL-EFFECTS.md).
- [Phylax adjustment-grant source](https://github.com/oramasys/phylax/blob/0c3e860749b3ff8f62e102679f1f415f8acf0a61/src/phylax/adjustment_grant.py).
- [Phylax authority-store source](https://github.com/oramasys/phylax/blob/0c3e860749b3ff8f62e102679f1f415f8acf0a61/src/phylax/grant_store.py).
- [Oramasys ledger](https://github.com/oramasys/oramasys/blob/b5f3821804715665b716ab600ea8419810bea920/src/orama/graph/execution_guard.py).
- [Admitted observation composition](https://github.com/oramasys/oramasys/blob/b5f3821804715665b716ab600ea8419810bea920/src/orama/graph/admission_runtime.py).

The E1 statement that its repository alone cannot establish the refusal vocabulary
has a concrete external resolution: Phylax's `GrantRefusalReason` declares
`grant.malformed` and `grant.schema_unsupported`. Its verifier maps unsupported
schema to the latter, malformed data to the former, and SQLite/I/O failures to
`verifier.unavailable`. This proves the names exist; it does not define new
effect-grant or cross-purpose semantics. C2 must map those deliberately.

Existing recovery-grant schema 1 uses a closed exact field set and rejects
extensions. Adding a purpose field to that historical wire silently would break
its parser and signed preimage. The integrated contract must define versioning
and legacy treatment before new implementation.

Parser ordering matters: `AdjustmentGrant.from_wire` checks the exact field set
before it checks `schema_version`. A version-2 body that also adds a purpose
field therefore reaches `grant.malformed` in the existing parser. A body with
the old exact field set and an unsupported version reaches
`grant.schema_unsupported`. C2 must specify and test the intended mapping for
each supported verifier version; it cannot assume legacy parsers inspect the
version first.

## Recovery witness: existing behavior versus proposed requirements

At the pinned Phylax revision, `SqliteGrantAuthorityStore` stores issuer keys,
issued grants, grant revocations and issuance audit. The verify-only reader holds
a validated read-only connection, checks database identity during reads, and
`reopen()` closes it and repeats path/descriptor/schema validation. These are
file-identity and current-store checks. They do not prove that an authorized
database snapshot is the newest one, nor retain an independent event-tip witness.

Consequently E1 section 8.2 remains a new recovery contract. Reopening a valid
old store cannot serve as its operational acceptance test. The recovery slice
must prove all of the following before an old snapshot can resume authority:

1. Dispatch is quiesced, with in-flight effects retained as uncertain.
2. Current state, events and outbox are preserved before restoring a copy into
   quarantine; preserve failures leave quarantine in force.
3. An external witness cannot be rewound by restoring either the consumer store
   or the issuer store. A directory beside a database is not by itself proof of
   that independence; define the restore boundary and witness trust explicitly.
4. Witnesses bind store identity, schema/version, batch sequence, authority and
   configuration epochs, clock high-water mark, previous witness digest, event
   tip and the issuer/provider evidence required by the integrated contract.
5. Durability and readback of the witness cover the committed batch before any
   dependent dispatch, grant acceptance or hold release. Pending, failed or
   missing publication refuses reopening.
6. A gap, truncation, rollback of either store or broken chain preserves spent
   authority conservatively. An unknown effect stays charged and unreplayed.
7. Reopening requires verified reconciliation, a recorded operator disposition,
   schema compatibility and reservation revalidation.

The integrated schema must also define recovery from an uncovered final batch
without a circular requirement: quarantine prevents business dispatch while the
recovery mechanism can publish/reconcile the missing witness under its own
explicit capability. This is a design requirement, not an existing executable API.

Proposed tests: old consumer snapshot plus newer issuer revocation; old issuer
snapshot plus newer grant consumption; witness chain gap/truncation; crash after
commit before publication; publish succeeds but readback fails; preserve failure;
schema mismatch; and a valid reconstruction that alone permits reopening.

## Existing test evidence and remaining E1 coverage

The following are actual nodes at the pinned Oramasys source. They establish
bounded M1 seams. None establishes the new E1 effect contract by itself.

| E1 requirement | Existing node or source | Evidence and missing extension |
| --- | --- | --- |
| T-01 / T-02 | `core_gate/test_admitted_observation_unknown_disposition.py::test_critical_failure_names_the_started_unsettled_attempt_durably` | Rerun passed in the 12-test delivery group; effect outbox no-attempt/corrupt-log cases remain new |
| T-03 | `test_durable_accounting.py::test_unknown_hold_is_not_released_without_an_explicit_adjustment` | Node exists; new E1 reconciliation/automatic-replay assertions still needed |
| T-04 | `test_adjustment_grant_consumer.py::test_altered_digest_or_principal_on_retry_is_refused` | Existing adjustment replay boundary; effect reconciliation actor/amount/CAS remains new |
| T-05 | `test_execution_guard.py::test_reopening_a_lease_fences_the_old_holder` | Existing ledger fence; late remote-effect receipt versus state application remains new |
| T-06 | `test_adjustment_grant_consumer.py::test_consumer_normalizes_foreign_failures_into_the_closed_set` | Existing recovery-grant failure mapping; new permit failure paths remain new |
| T-07 | `test_durable_accounting.py::test_commit_intent_is_idempotent_and_settlement_is_bound_to_its_hold` | Local idempotent intent; no claim of remote effect deduplication |
| T-08 | `test_budget_crash_recovery.py::test_sigkill_recovery_is_conservative_without_replay` | Existing accounting crash cases; every E1 effect crash boundary remains new |
| T-24 | `test_adjustment_grant_consumer.py::test_identical_request_that_lost_the_race_gets_the_recorded_receipt` | Recovery replay/concurrency seam; effect provider-key and both-side revocation ordering remain new |
| T-09 to T-23, T-25 to T-30 | E1 section 9.1 proposed test inventory | Proposed names and acceptance requirements, no executable coverage claimed here |

T-24 additionally routes to existing consumer tests for identical retry after
expiry/revocation, hold and lease epoch checks, missing revocation answers and
clock sampling under the write lock. These nodes require a focused execution at
the pinned source before a final evidence packet labels them passed.

Executed now: 12 tests across `test_admitted_observation_delivery.py`,
`test_admitted_observation_unknown_disposition.py` and `test_delivery_seam.py`
passed in the isolated main-plus-G1 checkout. G1's data/test additions do not
change the exercised runtime source. Other rows above are source inspection.

## Handoff to C2 and final checker

C2 must define the purpose discriminator/version and exact per-direction codes,
canonical message/fingerprint bytes, issuer permit and revocation/cascade
encodings, witness publication/readback and lifetime. It must reconcile the
durable-effects step-4 wording with issuer versus consumer transaction ownership.

Purpose refusal belongs at every boundary that accepts effect authority, even
in the first bounded slice. Splitting the implementation must not temporarily
admit recovery authority as effect authority. An Agy suggestion to exclude
purpose enforcement from the first effect spine is rejected on that basis.

The final checker verifies the integrated substantive commit, source links and
test matrix. The operator then supplies its ratification reference. Serving,
T3 implementation, T4/T5 and remote autonomy retain their existing gates.
