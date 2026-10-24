# E1 C2 (Part 3, Sections 1-2): ratification acceptance matrix

**Status:** PREPARED FOR OPERATOR DECISION. Nothing below is a ratification, an implementation
authority, a serving authority or a pin promotion. `ORAMA_GRANT_SERVING` stays unset. A merge, a
green check or an agent endorsement is not a ratification; only the operator record in Section 5
is, and it is blank until the operator fills it.
**Amendment:** [Part 3 amendment][amend], Sections 1 and 2 and their
[locked rules](E1-C2-INTEGRATED-SCHEMA-PART3-AMENDMENT-2026-10-19.md#locked-rules-for-sections-1-and-2).
**Predecessor:** Section 3.3 is a separate, already recorded decision in the
[first packet][packet]. This slice does not touch it.

## 1. Why one decision

A cascade is the authority-side notification that follows an approval revocation, so the two
bodies share one identifier grammar, one validation path and one consumer gate (Step 4.3 Rule 4).
Ratifying one without the other would leave the shared rules undefined.

## 2. Acceptance matrix

Each row is satisfied only by executed output at an exact head. "P" is the Phylax issuer PR,
"O" the Oramasys consumer PR, "X" the byte-identical cross-repository probe
`c2_part3_events_probe.py`, run by each repository against the other's pinned commit.

| # | Locked rule (amendment locked rule) | P test | O test | X scenario |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Revocation body is exactly `subject_kind`, `subject_id`; kind is `grant`, `approval` or `issuer` (1) | `test_revocation_body_is_closed`, `test_revocation_subject_kind_vocabulary_is_closed` | `test_ingest_refuses_malformed_bodies[revocation-*]` | X2 |
| 2 | Identifiers are canonical: ASCII U+0021-U+007E, 1-1024 bytes, refused not repaired (2) | `test_identifier_must_be_canonical` | `test_ingest_refuses_malformed_bodies[revocation blank id / whitespace id / padded id / inner space id / non-ascii id / control id / overlong id / numeric id]` | X2 |
| 3 | Cascade body is exactly `approval_id`, `grant_ids`, `issuer_authority_version` (1) | `test_cascade_body_is_closed` | `test_ingest_refuses_malformed_bodies[cascade-*]` | X2 |
| 4 | `grant_ids` strictly ascending; duplicate or unsorted refused; empty valid (3) | `test_cascade_grant_ids_must_be_strictly_ascending`, `test_cascade_grant_ids_accept_empty_and_single` | `test_ingest_refuses_malformed_bodies[cascade unsorted / duplicate / duplicate tail / case order]` | X2, X3 |
| 5 | `issuer_authority_version` is a safe integer of at least 1 (3) | `test_cascade_authority_version_is_a_positive_safe_integer`, `test_cascade_authority_version_bounds_are_accepted` | `test_ingest_refuses_malformed_bodies[cascade version zero / negative / boolean / unsafe / string / float]` | X2 |
| 6 | Complete event at most 65,536 canonical bytes, the consumer's existing wire limit (4) | `test_event_wire_size_is_bounded`, `test_event_wire_size_boundary_is_exact` | `test_event_wire_rejects_an_oversize_object` (`test_dispatch_consumer_wire.py`) | n/a (unit-level on both sides) |
| 7 | Valid events append, chain, sign and verify; digests equal the independent oracle (Section 3) | `test_append_signs_chains_and_persists_each_kind`, `test_canonical_event_vectors_match_the_independent_oracle` | `test_vendored_vectors_match_the_oracle` | X1 |
| 8 | A refused body consumes no version and writes no row (5) | `test_refused_body_consumes_no_version` | `test_malformed_batch_persists_nothing` | X2 |
| 9 | Issuer takes no consumer state; identical revocation is idempotent (5) | `test_append_api_takes_no_consumer_state`, `test_identical_revocation_is_idempotent` | n/a | n/a |
| 10 | Facts persist with the acknowledgement; replay and fork change nothing (6) | n/a | `test_ingest_persists_facts_with_the_ack`, `test_replayed_batch_is_idempotent`, `test_fork_does_not_overwrite_recorded_facts` | X7 |
| 11 | Rule 4 refuses a grant, approval or issuer revocation; the approval is the one bound to the attempt (6) | n/a | `test_rule4_refuses_grant_revocation`, `test_rule4_refuses_approval_revocation`, `test_rule4_refuses_issuer_revocation` | X4, X5a, X6 |
| 12 | Rule 4 refuses a cascade-listed grant whatever its binding (6) | n/a | `test_rule4_refuses_cascade_listed_grant` | X5b |
| 12a | The approval binding is persisted with the attempt, canonical or empty, part of its idempotent identity; the authorizing caller cannot supply it; an undeclared or legacy attempt fails closed on any approval revocation (6) | n/a | `test_approval_binding_must_be_empty_or_canonical`, `test_approval_binding_is_part_of_the_idempotent_attempt`, `test_authorizing_caller_cannot_supply_the_approval_binding`, `test_undeclared_binding_fails_closed_on_any_approval_revocation`, `test_cascade_listing_is_reported_before_an_undeclared_binding`, `test_legacy_attempts_table_gains_an_undeclared_binding` | X5c |
| 12b | Other issuers, approvals and grants are untouched (6) | n/a | `test_rule4_ignores_unrelated_facts` | n/a (unit-level) |
| 12c | Single approval matches no approval revocation (6) | n/a | `test_single_approval_binding_matches_no_approval_revocation` | n/a (unit-level) |
| 13 | Refusal leaves no intent, outbox, grant use or consumed reservation (7) | n/a | `test_refusal_leaves_no_intent_outbox_use_or_reservation` | X8 |
| 14 | No new shared wire refusal code (8) | `test_refusal_vocabulary_is_unchanged` | `test_no_new_authorization_rules` | X1-X8 (no new code observed) |

## 3. Canonical event vectors

Independent oracle: a standard-library script that imports neither repository. Event digest is
SHA-256 of the canonical JSON wrapper `{body, kind, previous_event_digest, version}` (sorted keys,
no whitespace). Version 1 chains from 64 zeros.

| v | kind | canonical body | event_digest |
| :--- | :--- | :--- | :--- |
| 1 | revocation | `{"subject_id":"grant-vector-0001","subject_kind":"grant"}` | `8bae016107341fde2b9d9241b1b450b66791018f913a0c62299de8e2bba1302f` |
| 2 | revocation | `{"subject_id":"approval-vector-0001","subject_kind":"approval"}` | `d6f41cebbb64a45186ccc4c0bcd1e0dd66ed37f0e0c1689cdcc7cf4856538aed` |
| 3 | cascade | `{"approval_id":"approval-vector-0001","grant_ids":["grant-vector-0002","grant-vector-0003"],"issuer_authority_version":1}` | `36469ce85187f112ed8c0953a0ec9ecae7a1ed99075b82aeed7029d6cb90e466` |
| 4 | revocation | `{"subject_id":"issuer-vector-0001","subject_kind":"issuer"}` | `c32f896b4e5c05a24ba137ccde6f2fdd923feaf516d03fd0baee8a0ea09b0858` |

Phylax publishes the signed vector file; Oramasys vendors it byte-identical with a recorded
SHA-256, as it already does for the permit vectors.

## 4. Immutable source pointers

Review bases at the time of preparation. They identify evidence and authorize nothing.

| Source | Full commit |
| :--- | :--- |
| orama-system `main` (includes Section 3.3 conformance suite, PR 434) | `fc74863c371704a2886d88a07e65507f5bbfec8a` |
| oramasys `main` (Section 3.3 consumer, PR 72) | `beb35f0a76609b2420b6bc88f3a82e6d839db439` |
| phylax `main` (abort binding and probe parity, PR 17) | `6ee39eedc8a6b0b49bfd2332c83415a93b4b6947` |
| Section 3.3 ratified commit (first packet) | `6459b30e77a6ab22297307374e64dd8872c9b796` |

Implementation heads are added to Section 5 by the operator when the matrix is satisfied.

## 5. Operator record (fill when complete)

```text
COMMIT   = <40-hex SHA of the reviewed amendment, operator fills>
SHA256   = <64-hex digest, operator fills>
HEADS    = <phylax 40-hex>, <oramasys 40-hex>
TESTS    = <links to executed output for rows 1-14>
REVIEWS  = <reviewer, head, verdict>
DECISION = <ratify | defer>, <date>, <operator>
SCOPE    = Sections 1 and 2 only
```

The digest is the SHA-256 of the amendment file bytes at the commit above, computed with the
method in the [first packet](E1-C2-PART3-RATIFICATION-ACCEPTANCE-PACKET-2026-10-22.md#3-canonical-digest-method).

## 6. Choices for the operator to confirm or strike

These are my proposals beyond the rules you listed; each is one line in the amendment.

1. **Identifier grammar** (locked rule 2). The listed rules say "canonical" without defining
   it. The proposal is printable ASCII without space, 1-1024 bytes. Strike or widen if real
   `second_approval_ref` values need spaces or non-ASCII.
2. **Empty `grant_ids` is valid** (rule 3). It records the approval and nothing else.
3. **64 KiB event cap** (rule 4). It bounds a cascade list. It applies to the whole event, not
   the body, because the consumer already refuses any larger event; a body-only cap would let the
   issuer append an event the consumer can never ingest.
4. **Rule 4 reads the approval binding persisted with the attempt** (rule 6). This replaces the
   earlier optional `approval_ref` argument, which let a caller that omitted it pass a grant
   whose approval was revoked when the cascade did not list that grant. The consumer now binds
   the grant's verified `second_approval_ref` when it creates the attempt, as part of the
   attempt's idempotent identity, and `authorize_dispatch` takes no approval argument. `""` is
   the wire's single-approval value and matches no approval revocation. Omitting the binding
   records the attempt as undeclared, refused as `approval_undeclared` (consumer-local) whenever
   the issuer has revoked any approval, so omission can only over-refuse, never bypass. Attempts
   tables created before the column migrate with every old row undeclared. The cascade list
   remains a second, independent refusal. Strike this choice only to keep the earlier gap.

Two stated limits of choice 4 (operator choice B1, recorded in the decision checklist). First, the
public `create_attempt` takes a typed `VerifiedDispatchGrant`, but that type is a plain value
object: the guarantee that its facts came from a verified v2 grant is held by the composition
adapter that builds it, which is not part of this slice, and Python's leading underscore on the
fixture and migration primitive is a convention, not enforcement. Second, an anchor is an epoch
floor: events below it are refused rather than backfilled, and any recovery would be a separate
audited protocol.

## 7. Out of scope

Issuer admission still reads grant and revocation facts through its injected `SignedGrantLookup`
interface, not from its own event log. That is an issuer-side composition boundary outside this
consumer-slice contract. The fixed lookup used by interop probes is test infrastructure, not a
production consumer-admission source; this slice introduces no second consumer authority. Also
excluded: Sections 3.1, 3.2 and 4, the execution-witness fields, serving, pin promotion and
activation.

[amend]: E1-C2-INTEGRATED-SCHEMA-PART3-AMENDMENT-2026-10-19.md
[packet]: E1-C2-PART3-RATIFICATION-ACCEPTANCE-PACKET-2026-10-22.md
