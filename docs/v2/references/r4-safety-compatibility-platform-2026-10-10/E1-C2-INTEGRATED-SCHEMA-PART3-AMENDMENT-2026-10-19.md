# E1 C2 (Part 3): Integrated Schema Contract Amendment — Revocation, Cascade, and Retained-Anchor Checkpoints

**Status:** PROPOSED AMENDMENT for independent review (Codex, Cline) and operator ratification.
**Precondition Context:** Proposes answers to E1 Section 14 Rule 3 and items left pending
integrated schema review in [E1 Section 13, Specifications closing the open semantics][e1-schema]
and [Not resolved from repository sources][e1-open]. Consumer witness fields remain open
as described in [Section 4](#4-status-of-cascade-witness-fields).
**Companion Documents:**

* Part 1: [Purpose, version and refusal contract][purpose]
  (19-field grant v2, default-deny classification, closed refusal vocabulary).
* Part 2: [Permit wire and role reconciliation][wire]
  (permit wire, finalization wire, multi-role reconciliation).
* [Status addendum, Scope of Parts 1–2 Ratification and Part 3 Dependency][status].

**Authority boundary:** The addendum records the historical Parts 1–2 ratification at
`59c623fa27497183d3a1c4ed19585d87623eae22`; it explicitly excludes Part 3. This amendment
remains proposed until a separate operator decision names its exact reviewed commit. Merge,
source/test correspondence, or reviewer endorsement supplies no ratification or implementation
authority. No serving, production emission, or pin promotion is authorized; `ORAMA_GRANT_SERVING`
remains unset.

**Reference revision:** Relative links below navigate the repository's current documents.
Historical evidence is bound separately to the immutable snapshots in Section 7, without
changing their original status text or bytes. Section numbers are document identifiers,
not mutable file-line positions.

## Ratification surface

This table scopes the one operator decision this document can support. It marks existing text
and moves none of it. [Section 3.3](#33-consumer-anchor-floor-invariant-additional-consumer-local-gate)
was the first slice put to the operator (its decision is recorded in the packet, Section 8).
Sections 1 and 2 are the second slice and are proposed for ratification together as one
decision, recorded in the sibling
[Sections 1-2 acceptance matrix][matrix]; everything else remains proposed and is a release
prerequisite that is not part of either decision. The meaning of a ratification is in
[Section 8](#8-ratification-acceptance-packet).

| Section | Marking |
| :--- | :--- |
| [1. Minimal revocation event body](#1-minimal-revocation-event-body), including its [locked rules](#locked-rules-for-sections-1-and-2) | **Proposed for ratification** (second slice, decided together with Section 2) |
| [2. Minimal cascade event body](#2-minimal-cascade-event-body), including its [locked rules](#locked-rules-for-sections-1-and-2) | **Proposed for ratification** (second slice, decided together with Section 1) |
| [3.1 Event-as-checkpoint equivalence](#31-event-as-checkpoint-equivalence) | Remains proposed; release prerequisite (checkpoints beyond the anchor), not part of this decision |
| [3.2 Pruning, retention and archival](#32-pruning-retention-and-archival-rule) | Remains proposed; release prerequisite, not part of this decision |
| [3.3 Consumer anchor floor invariant](#33-consumer-anchor-floor-invariant-additional-consumer-local-gate): the bootstrap-anchor protocol, the atomic persisted identity/version/digest/floor record, and the $R_p \ge$ anchor_version floor comparison rule, with the consumer-local refusal and quarantine semantics defined inside it | **Proposed for ratification** |
| [4. Cascade witness fields](#4-status-of-cascade-witness-fields) | Remains proposed (open); release prerequisite, not part of this decision |
| [5. Field-set summary](#5-summary-of-proposed-field-sets-for-schema-review) | Index only; each row follows the marking of the section it summarizes |
| [6. Source and test crosswalk](#6-source-and-test-crosswalk-review-evidence-not-adoption) | Review evidence, not adoption |
| [7. Immutable historical evidence](#7-immutable-historical-evidence) | Evidence identifiers, not adoption |
| [8. Ratification acceptance packet](#8-ratification-acceptance-packet) | Procedure; the packet itself is a sibling document |

Nothing in this table changes the statement in the authority boundary above that the whole
amendment is proposed. Even for Section 3.3, a ratification is a contract decision only (see
Section 8).

---

## 1. Minimal Revocation Event Body

Per [Part 2 Section 1, Permit objects, Step 4.3 Rule 4][wire-objects], the consumer
refuses any acknowledged event above $R_p$ that revokes *"this grant, its approval chain or the
issuer"*. Therefore, a revocation event must identify its target entity by subject kind and
subject identifier.

The append-only log `issuer_events` already supplies the sequential `version`, causal
`previous_event_digest`, and issuer Ed25519 `signature`. The event body carries only the pure
semantic delta:

```json
{
  "subject_kind": "grant",
  "subject_id": "grant-uuid-or-urn"
}
```

### Exact Field Specification

1. `subject_kind` (`str`): Exact closed vocabulary: `"grant" | "approval" | "issuer"`.
2. `subject_id` (`str`): Non-blank canonical identifier of the revoked subject:
   * For `subject_kind == "grant"`: the `grant_id`.
   * For `subject_kind == "approval"`: the `second_approval_ref` carried on the v2 grant.
   * For `subject_kind == "issuer"`: the canonical `issuer_id`.

No extraneous operational fields (e.g. `disposition_ref`, `revocation_epoch`) are embedded in the
event body; the event's own chain version in `issuer_events` serves as the authoritative
revocation version.

---

## 2. Minimal Cascade Event Body

Per [E1 Section 13.4, Second approval, Cascade record][e1-approval]:

> "Each issuer cascade emits a durable notification identifying the affected approval and
> grants, issuer authority version and cascade event. The issuer records authority facts only;
> it does not query consumer execution state."

The proposed exact body carries:

```json
{
  "approval_id": "second-approval-ref",
  "grant_ids": [
    "grant-uuid-1",
    "grant-uuid-2"
  ],
  "issuer_authority_version": 1
}
```

### Exact Field Specification

1. `approval_id` (`str`): The revoked parent approval reference (`second_approval_ref`).
2. `grant_ids` (`list[str]`): Sorted, duplicate-free list of canonical ASCII identifiers for
   dependent grants whose **issuer-side authority** is affected by this cascade commit. It is not an
   assertion that a consumer has or has not consumed, dispatched, or executed any listed grant: the
   issuer records authority facts and does not query consumer execution state.
   *(Note: `grant_ids` supports notification delivery, recovery-witness lookup, and audit indexing.
   Consumer dispatch gating remains a consumer-local Step 4.3 decision over its own durable grant
   use, acknowledgement, and authority state; this notification neither substitutes for nor changes
   that gate.)*
3. `issuer_authority_version` (`int`): Safe positive integer identifying the issuer authority
   epoch at the time of the cascade commit.

### Locked rules for Sections 1 and 2

These rules complete the two bodies above. They bind the issuer and the consumer alike, and a
body that breaks any of them is malformed.

1. **Closed bodies.** A revocation body has exactly `subject_kind` and `subject_id`; a cascade
   body has exactly `approval_id`, `grant_ids` and `issuer_authority_version`. A missing, extra
   or null field is malformed. `subject_kind` is exactly `grant`, `approval` or `issuer`.
2. **Canonical identifier.** `subject_id`, `approval_id` and every `grant_ids` element is an
   ASCII string of 1 to 1024 bytes made only of the printable characters U+0021 to U+007E, so it
   is never blank, padded, spaced, controlled or non-ASCII. No normalization is applied; a value
   that is not already canonical is refused, not repaired.
3. **Cascade list.** `grant_ids` is a JSON array in strictly ascending code-point order. A
   duplicate or an out-of-order pair is malformed. An empty array is valid and records only the
   approval. `issuer_authority_version` is a safe integer from 1 to 2^53 - 1.
4. **Bounded size.** The complete seven-field event (`version`, `kind`, `body`,
   `previous_event_digest`, `event_digest`, `issuer_key_id`, `signature`) is serialized as
   canonical JSON: object keys sorted, separators `,` and `:` with no whitespace, non-ASCII text
   written as itself (not `\u` escapes), NaN and infinity refused, encoded as UTF-8. The cap is
   65,536 bytes of that encoding. The issuer and the consumer use this same function, so the
   issuer never appends an event the consumer must refuse. The four-field digest wrapper is
   unchanged and is a different object.
5. **Authority facts only.** The issuer records authority facts and takes no consumer
   execution state as an input. Recording an identical revocation again returns the existing
   event and appends nothing.
6. **Consumer application.** A verified revocation or cascade is persisted in the same local
   transaction as its acknowledgement, and replaying it changes nothing. At Step 4.3, inside the
   existing dispatch transaction, Rule 4 additionally refuses a grant when any acknowledged event
   revokes that grant, revokes the issuer, revokes the approval bound to the attempt, or lists the
   grant in a cascade. The approval binding is the grant's verified `second_approval_ref`,
   persisted once with the dispatch attempt as part of its identity; the authorizing caller
   neither supplies nor omits it. The empty string (single approval) matches no approval
   revocation. An attempt recorded without a binding is undeclared and is refused whenever the
   issuer has revoked any approval, so omission fails closed. A cascade can only add a refusal;
   it never satisfies or relaxes any other rule, so it neither substitutes for nor changes the
   Step 4.3 gate.
7. **Refusal leaves nothing.** A refusal under rule 6 leaves no dispatch intent, no outbox
   entry, no consumed grant use and no consumed reservation.
8. **No new wire vocabulary.** These rules add no shared wire refusal code. Refusal reasons are
   consumer-local, and the closed permit, finalization and abandon vocabularies are unchanged.

---

## 3. Retained-Anchor Chain Checkpoint Specification

Per [Part 2 Section 1, Permit objects, Capacity and retention][wire-objects]:

> "A consumer needs only an issuer-signed chain checkpoint (version and digest) at its
> acknowledged point plus the events since; events below the lowest acknowledged version across
> consumers may be pruned only after such a checkpoint is published."

### 3.1 Event-as-Checkpoint Equivalence

In `SqliteDispatchPermitStore`, each `issuer_events` row contains:
`("version", "kind", "body", "previous_event_digest", "event_digest", "issuer_key_id", "signature")`.
Because the issuer signs `event_digest` using its Ed25519 key, and `event_digest` commits to the
entire historical chain through `previous_event_digest`, the event row at version $N$
**literally is** an issuer-signed `(version, digest)` checkpoint. No secondary signing domain or
checkpoint envelope is required.

### 3.2 Pruning, Retention, and Archival Rule

1. **Pruning Ceiling:** Events may be pruned from the hot `issuer_events` store only below the
   **lowest acknowledged version across consumers**.
2. **Move to Audit Archive (No Discard):** Pruned rows MUST be migrated to the cold audit archive
   to fulfill the seven-year requirement in [E1 Section 13.3, Retention][e1-retention].
   They are never deleted or
   discarded.
3. **Bounded Current-Anchor Retention:** The event at the current prune boundary (the "anchor
   event") remains in the hot store as the base of the active chain. There is at most one such
   retained boundary event per issuer chain. When a later prune advances the boundary from $N$ to
   $M > N$, the former $N$ anchor is migrated to the cold audit archive with the other rows below
   $M$, and only the $M$ anchor remains hot. The archive preserves the former anchor and its
   digest-chain evidence; hot retention is a current-checkpoint cache, not a permanent copy of
   every historical boundary.

<a id="33-consumer-anchor-floor-invariant-consumer-local-rule-4"></a>

### 3.3 Consumer Anchor Floor Invariant (Additional Consumer-Local Gate)

The earlier fragment `#33-consumer-anchor-floor-invariant-consumer-local-rule-4` referred
to this section. Its former label conflated the proposed floor check with the existing
Step 4.3 Rule 4 revocation check; those are separate gates.

When a consumer bootstraps from a pruned anchor at $\text{anchor\_version} > 1$:

1. **Bootstrap Initialization:** The consumer executes
   `bootstrap_anchor(issuer_id, anchor_event, verifier)` as one local transaction:
   * It reconstructs the canonical event preimage from exactly `body`, `kind`,
     `previous_event_digest`, and `version`, using the canonical JSON encoding in Part 2.
     It computes the SHA-256 digest of those UTF-8 bytes and requires it to equal the supplied
     `anchor_event["event_digest"]`. Verifying a signature over a caller-supplied digest alone is
     insufficient.
   * It resolves `issuer_key_id` only through the locally trusted key material for `issuer_id`,
     requires that key to belong to the declared issuer, and verifies the detached Ed25519 signature
     over the recomputed digest. A key or issuer supplied only by the event is never trusted.
   * On first bootstrap, it atomically persists the issuer identity and key identity, anchor
     `version`, recomputed `event_digest`, and immutable `anchor_version` floor. It also persists
     a checkpoint-aware acknowledgement base `(base_version, base_digest) = (anchor_version,
     event_digest)` and initializes `acked_through = anchor_version`; the matching
     `(issuer_id, version, event_digest)` remains recorded in `issuer_cascade_ack` for audit.
     The base is not a claim that events before `anchor_version` were locally replayed. It is the
     verified signed checkpoint that makes the anchor the first acknowledged version for this
     consumer.
   * On a repeated bootstrap, the persisted issuer, key, version, digest, and floor must be exactly
     identical or the consumer refuses and retains quarantine, as defined in
     [Anchor quarantine](#anchor-quarantine-semantics) below. An identical repeat is a no-op: it
     must never reset, lower, or otherwise rewrite an acknowledged high-water mark or anchor floor.
   * `acked_through` is checkpoint-aware. Without a persisted base, it is the greatest contiguous
     verified acknowledgement sequence beginning at version 1. With base version $N$, it is the
     greatest $V \ge N$ for which the persisted, verified anchor at $N$ and every event from
     $N + 1$ through $V$ are acknowledged without a gap. Therefore bootstrap at $N > 1$ sets
     `acked_through` to $N$ immediately; an event at $N + 1$ advances it to $N + 1$ only after
     verification. Missing or conflicting events above $N$ do not advance it, and the consumer
     never fabricates acknowledgements below $N$.
   * Rules 2, 3, and 5 use this derived checkpoint-aware `acked_through` value. Their comparisons
     are unchanged: Rule 2 requires `acked_through >= R_p`, Rule 3 requires
     $R_p \ge \text{consumer_acked_through}$ from the permit, and Rule 5 requires the
     finalization coverage already specified in Part 2. The additional anchor-floor gate below is
     separate and does not replace any of those rules.
2. **Pre-Anchor Revocation Rejection (Consumer-Side Gate):** To prevent the pre-anchor revocation
   blind-spot attack (where a pre-anchor revocation is invisible to the bootstrapped consumer),
   this proposed additional consumer-local anchor-floor gate enforces:
   $$\text{permit}["revocation\_version"] \ge \text{consumer}["anchor\_version"]$$
   Any permit presenting $R_p < \text{anchor\_version}$ fails the proposed anchor-floor gate
   coverage (the consumer has not witnessed and cannot verify events prior to its anchor floor).
   The caller must obtain a fresh permit re-issued against the current chain head. This is a
   consumer-local dispatch check, separate from Rule 4's acknowledged-event revocations and
   the acknowledgement coverage in Rules 2, 3 and 5; no new shared wire refusal code is added.
   The refusal is defined in [Lower-floor refusal](#lower-floor-refusal) below.

<a id="lower-floor-refusal"></a>

**Lower-floor refusal (consumer-local).**

* **Name:** `anchor_floor.permit_below_floor`. It is a consumer-local reason. It is never
  emitted on the wire, is not part of the closed refusal vocabulary of
  [Part 1][purpose], and adds no shared wire refusal code. The phrase "fails the gate" in
  item 2 means exactly this refusal and nothing else.
* **When raised:** in the Step 4.3 consumer transaction, when the issuer has a persisted anchor
  floor and the permit's $R_p$ is below it. The comparison reads the persisted floor under the
  same transaction that would record the intent, so a floor committed concurrently still
  applies. An issuer with no persisted anchor (never bootstrapped from a pruned anchor) has
  no floor and this refusal is not raised for it.
* **State left behind:** none. The refusal happens before any authority write: no intent, no
  outbox item, no use consumed, and the reservation is not consumed, so the caller can retry
  with a fresh permit against the same reservation. The consumer may keep a sanitized,
  payload-free refusal audit entry, as for other refusals.
* **Not another gate:** it is distinct from Rule 4 (an acknowledged event revokes the grant,
  its approval chain or the issuer) and from Rules 2, 3 and 5 (acknowledgement coverage). It
  must not reuse their reason names, and a permit that is also refused by those rules reports
  the first gate in the Step 4.3 order without merging reasons.
* **Remedy:** obtain a permit re-issued against the current chain head. The floor is never
  lowered to admit an old permit.

<a id="anchor-quarantine-semantics"></a>

**Anchor quarantine semantics.** These define the term "retains quarantine" used in item 1.
They follow the existing consumer clock-quarantine pattern ([consumer slice-2 notes][consumer-clock],
`clear_clock_quarantine`), applied to one issuer.

* **What enters quarantine:** a repeated `bootstrap_anchor` for an `issuer_id` whose supplied
  issuer, key identity, version, recomputed digest or floor differs in any field from the
  persisted record. A bootstrap that fails digest recomputation, trusted-key resolution or
  signature verification on first install is a plain refusal and persists nothing, so it does
  not enter quarantine. Only a conflict with an already-persisted anchor does.
* **Where it is stored:** in the same atomic record as the identity, version, digest and floor
  (a quarantine flag on that row). Setting the flag is committed in the transaction that
  detected the conflict, so it survives restart and cannot be missed by a later dispatch.
  The conflicting evidence is kept, not applied: the persisted values are never overwritten.
* **What it blocks:** every dispatch authorization for that issuer, rechecked under the
  authorization write lock before any reservation is consumed (the same ordering the clock
  quarantine uses). Read-only inspection of the record and of acknowledged events stays
  possible. Quarantine of one issuer does not block other issuers. The blocked authorization
  reports a consumer-local reason `anchor_quarantined`, never on the wire and with no
  shared refusal code, and writes no authority state.
* **How it clears:** only an audited operator procedure, `clear_anchor_quarantine`,
  takes an injected operator authority (no default; a missing or blank reference is refused),
  non-blank trusted evidence of which anchor is correct, and an existing quarantine. It
  appends the previous record, the accepted record, the evidence, the operator reference and
  a timestamp to an append-only log, in the same transaction as the clear. Nothing deletes
  or rewrites a log row.
* **Forbidden:** automatic clearing (by timeout, by restart, by a matching later bootstrap or
  by any caller-supplied flag), and lowering a floor. If trusted evidence shows the persisted
  floor itself is wrong and a lower one is correct, that is a separate operator-ratified
  re-anchor decision outside this section, never a side effect of clearing quarantine.

---

## 4. Status of Cascade Witness Fields

Consumer-side execution recovery witness fields in [E1, Not resolved from repository sources][e1-open]
remain **open**. They are not defined or frozen by this proposed Part 3 amendment and will be
defined alongside the telemetry and
observability contract slice. That later slice must close all of these gates before it can claim a
witness contract: (1) the concrete field set, types, canonical encoding, and durable identity;
(2) the publication medium, retention owner, and durability boundary; and (3) an authenticated
read-back mechanism that verifies the published record and defines failure as unavailable rather
than empty success. Until then, a missing or unreadable witness remains a fail-closed recovery
condition, not evidence of no affected work.

---

## 5. Summary of Proposed Field Sets for Schema Review

| Contract Entity | Defined Wire Fields | Specification Basis |
| :--- | :--- | :--- |
| **`revocation` Event Body** | `subject_kind` (`"grant" \| "approval" \| "issuer"`), `subject_id` (`str`: grant_id, second_approval_ref, or issuer_id) | [Part 2 Section 1, Step 4.3 Rule 4][wire-objects]; proposed body in [Section 1](#1-minimal-revocation-event-body) |
| **`cascade` Event Body** | `approval_id` (`str`: second_approval_ref), `grant_ids` (`list[str]`), `issuer_authority_version` (`int`) | [E1 Section 13.4, Second approval][e1-approval]; proposed body in [Section 2](#2-minimal-cascade-event-body) |
| **Anchor Checkpoint** | Retained `issuer_events` row: `version`, `kind`, `body`, `previous_event_digest`, `event_digest`, `issuer_key_id`, `signature` | [Part 2 Section 1, Capacity and retention][wire-objects]; proposed equivalence in [Section 3.1](#31-event-as-checkpoint-equivalence) |
| **Consumer Anchor Floor** | Proposed `anchor_version` in `issuer_cascade_ack`; additional consumer-local gate requiring $R_p \ge \text{anchor\_version}$ | [Part 2 Section 1, Capacity and retention / Step 4.3][wire-objects]; proposed floor in [Section 3.3](#33-consumer-anchor-floor-invariant-additional-consumer-local-gate), separate from Rule 4's revocation check |
| **Grant v2 (Historical Part 1; Not Re-ratified Here)** | 19 closed fields from Part 1 Section 3.1 | [Part 1 Section 3.1, Proposed effect-grant fields (closed, exact set)][purpose-fields]; historical status per [addendum][status] |

## 6. Source and Test Crosswalk (Review Evidence, Not Adoption)

This is a source inspection at immutable review inputs: Phylax
`2d45556493190b1ca2a58ccede5b6b19d1daa1ad` and Oramasys
`4c67d37c624d6bea1d4953c9777962d1f8e42a3c`. Symbol/test names identify the evidence inside
each linked file without line-number coupling. Tests listed here were inspected, not executed
by this documentation correction; no new runtime conformance, qualification, or independent
approval is claimed. Parallel runtime corrections require their own exact-head evidence.

| Part 3 normative item | Status | Existing source or test covering it today | Supported conclusion and remaining gap |
| :--- | :--- | :--- | :--- |
| Bootstrap anchor ([Section 3.3](#33-consumer-anchor-floor-invariant-additional-consumer-local-gate)) | Proposed | None yet. Nearest: [Oramasys `_check_event`, `SqliteAttemptStore.ingest_events`][consumer-store]; [tests `test_ingest_records_contiguous_events_and_is_idempotent`, `test_ingest_refuses_without_flagging_a_gap_bad_signature_or_bad_digest`][consumer-tests] | Existing ingestion verifies contiguous signed events through an injected verifier. No `bootstrap_anchor` exists in this source; digest recomputation, trusted issuer/key binding and repeat-bootstrap quarantine are unevidenced. |
| Atomic persisted record (Section 3.3, item 1) | Proposed | None yet. Nearest: [Phylax `_EVENT_COLUMNS`, `_append_finalization`, `_events`][issuer-store]; [tests `test_finalization_happy_path`, `test_event_chain_digests_verify`][issuer-tests] | The issuer event row has the seven fields of [Section 3.1](#31-event-as-checkpoint-equivalence), chained digests and signatures. This supports the row substrate only; no consumer-side atomic anchor record or `anchor_version` persistence exists. |
| $R_p \ge$ anchor floor ([Section 3.3](#33-consumer-anchor-floor-invariant-additional-consumer-local-gate), item 2) | Proposed | None yet. No `anchor_version` appears in the inspected consumer source. | The floor check is not implemented or tested; existing Rule 4 tests cover revocation, not the anchor floor. |
| Retention and archival ([Section 3.2](#32-pruning-retention-and-archival-rule)) | Proposed | None yet. Requirement text: [Part 2 Section 1, Capacity and retention][wire-objects]; [consumer slice-2 limits][consumer-limits] | Seven-year retention is a requirement, not evidence of an archive. No archive or pruning implementation or test is identified in these inputs. |
| Revocation and cascade bodies (Sections [1](#1-minimal-revocation-event-body)-[2](#2-minimal-cascade-event-body)) | Proposed | Partial, different mechanism. [Phylax `SqliteDispatchPermitStore._check_grant`][issuer-store]; [tests `test_grant_revoked_cascade_and_expired`, `test_finalization_grant_revoked`][issuer-tests]. [Oramasys `RevocationPort`, `SqliteAttemptStore.authorize_dispatch`][consumer-store]; [tests `test_rule4_refuses_a_revoked_grant`, `test_rule4_refuses_an_issuer_wide_revocation`][consumer-tests] | The issuer checks injected grant facts and the consumer checks an injected revocation port. Neither implements or validates the proposed body fields or approval-chain cascade processing. |
| Execution witness ([Section 4](#4-status-of-cascade-witness-fields)) | Open | None yet. Specification only: [E1 Section 9.1, Test map, E1-T-25][e1-tests]; [E1 unresolved witness fields][e1-open] | `test_e1_cascade_recovery_witness` is a proposed test name, not an executable test. Fields, publication/retention and authenticated read-back remain open. |

The [consumer test `test_ingest_accepts_revocation_events_and_authorize_ignores_them_as_revocation`][consumer-tests]
explicitly separates opaque event ingestion from revocation interpretation. Do not count ingestion
coverage as proof that the proposed revocation/cascade bodies or consumer anchor floor are implemented.

## 7. Immutable Historical Evidence

The relative links above are navigation. These explicit full-commit evidence links preserve
the historical bytes used for this proposal; they do not follow later repository edits.
Their absolute URLs are intentional evidence identifiers, including for this repository.

| Source | Immutable evidence snapshot |
| :--- | :--- |
| E1 and its named sections | [E1 at the recorded Parts 1–2 revision](https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md) |
| Part 1 purpose and fields | [Part 1 at the recorded revision](https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md) |
| Part 2 permit and dispatch rules | [Part 2 at the recorded revision](https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md) |
| Ratification scope addendum | [Addendum at this proposal's review base](https://github.com/diazMelgarejo/orama-system/blob/55ff8ef58ef6b6202f6f521c8b5b5a7452281e1c/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/2026-10-19-e1-specification-ratification-addendum.md) |

## 8. Ratification Acceptance Packet

Ratifying [Section 3.3](#33-consumer-anchor-floor-invariant-additional-consumer-local-gate)
needs the packet in the sibling document
[E1-C2-PART3-RATIFICATION-ACCEPTANCE-PACKET-2026-10-22.md][packet]. The packet lives in its own
file because it records this document's canonical digest, which a document cannot contain about
itself. The packet states the current status of each of its six items and leaves the exact
commit and digest as operator-filled placeholders. As of this revision the conformance tests do
not exist; they are an explicit release prerequisite, and the packet cannot be complete until
they do.

A ratification of this surface is a contract and specification decision only. It authorizes no
implementation, no serving, no pin promotion and no activation, and it leaves
`ORAMA_GRANT_SERVING` unset. Everything outside Section 3.3 stays proposed.

[e1-schema]: E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#13-specifications-closing-the-open-semantics-proposed-for-independent-review
[e1-open]: E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#not-resolved-from-repository-sources
[e1-approval]: E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#134-second-approval-decision-3-the-conditions-recorded-in-section-11
[e1-retention]: E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#133-retention-decision-2
[e1-tests]: E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#91-test-map-resolves-e1-r09
[purpose]: E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md
[purpose-fields]: E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md#31-proposed-effect-grant-fields-closed-exact-set
[wire]: E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md
[wire-objects]: E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md#1-permit-objects-proposed
[status]: 2026-10-19-e1-specification-ratification-addendum.md#3-scope-of-parts-12-ratification-and-part-3-dependency
[issuer-store]: https://github.com/oramasys/phylax/blob/2d45556493190b1ca2a58ccede5b6b19d1daa1ad/src/phylax/dispatch_permit_store.py
[issuer-tests]: https://github.com/oramasys/phylax/blob/2d45556493190b1ca2a58ccede5b6b19d1daa1ad/src/tests/test_dispatch_permit_store.py
[consumer-store]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/src/orama/graph/dispatch_attempts.py
[consumer-tests]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/src/tests/test_dispatch_attempts.py
[consumer-limits]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/docs/e1-c2-consumer-slice2.md#limits-and-open-items
[packet]: E1-C2-PART3-RATIFICATION-ACCEPTANCE-PACKET-2026-10-22.md
[matrix]: E1-C2-PART3-S12-ACCEPTANCE-MATRIX-2026-10-24.md
[consumer-clock]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/docs/e1-c2-consumer-slice2.md
