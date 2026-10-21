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

**Reference revision:** E1 and Parts 1–2 links below name sections in that historical ratified
commit, without changing their original status text or bytes. The status addendum is linked at
Orama review base `55ff8ef58ef6b6202f6f521c8b5b5a7452281e1c`. Section numbers are document
identifiers, not mutable file-line positions.

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
3. **Anchor Event Retention:** The event at the prune boundary (the "anchor event") is **never
   removed** from the hot store. It is retained as the new base of the active chain.

### 3.3 Consumer Anchor Floor Invariant (Consumer-Local Rule 4)

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
     `version`, recomputed `event_digest`, and immutable `anchor_version` floor, and records the
     same `(issuer_id, version, event_digest)` in `issuer_cascade_ack`.
   * On a repeated bootstrap, the persisted issuer, key, version, digest, and floor must be exactly
     identical or the consumer refuses and retains quarantine. An identical repeat is a no-op: it
     must never reset, lower, or otherwise rewrite an acknowledged high-water mark or anchor floor.
2. **Pre-Anchor Revocation Rejection (Consumer-Side Gate):** To prevent the pre-anchor revocation
   blind-spot attack (where a pre-anchor revocation is invisible to the bootstrapped consumer),
   Step 4.3 Rule 4 (acknowledgement coverage) enforces:
   $$\text{permit}["revocation\_version"] \ge \text{consumer}["anchor\_version"]$$
   Any permit presenting $R_p < \text{anchor\_version}$ fails consumer Step 4.3 acknowledgement
   coverage (the consumer has not witnessed and cannot verify events prior to its anchor floor).
   The caller must obtain a fresh permit re-issued against the current chain head. This is a
   consumer-local dispatch check; no new shared wire refusal code is added to Part 1.

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
| **Consumer Anchor Floor** | Proposed `anchor_version` in `issuer_cascade_ack`; gating $R_p \ge \text{anchor\_version}$ under Step 4.3 Rule 4 | [Part 2 Section 1, Capacity and retention / Step 4.3][wire-objects]; proposed floor in [Section 3.3](#33-consumer-anchor-floor-invariant-consumer-local-rule-4) |
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
| Bootstrap anchor ([Section 3.3](#33-consumer-anchor-floor-invariant-consumer-local-rule-4)) | Proposed | None yet. Nearest: [Oramasys `_check_event`, `SqliteAttemptStore.ingest_events`][consumer-store]; [tests `test_ingest_records_contiguous_events_and_is_idempotent`, `test_ingest_refuses_without_flagging_a_gap_bad_signature_or_bad_digest`][consumer-tests] | Existing ingestion verifies contiguous signed events through an injected verifier. No `bootstrap_anchor` exists in this source; digest recomputation, trusted issuer/key binding and repeat-bootstrap quarantine are unevidenced. |
| Atomic persisted record (Section 3.3, item 1) | Proposed | None yet. Nearest: [Phylax `_EVENT_COLUMNS`, `_append_finalization`, `_events`][issuer-store]; [tests `test_finalization_happy_path`, `test_event_chain_digests_verify`][issuer-tests] | The issuer event row has the seven fields of [Section 3.1](#31-event-as-checkpoint-equivalence), chained digests and signatures. This supports the row substrate only; no consumer-side atomic anchor record or `anchor_version` persistence exists. |
| $R_p \ge$ anchor floor ([Section 3.3](#33-consumer-anchor-floor-invariant-consumer-local-rule-4), item 2) | Proposed | None yet. No `anchor_version` appears in the inspected consumer source. | The floor check is not implemented or tested; existing Rule 4 tests cover revocation, not the anchor floor. |
| Retention and archival ([Section 3.2](#32-pruning-retention-and-archival-rule)) | Proposed | None yet. Requirement text: [Part 2 Section 1, Capacity and retention][wire-objects]; [consumer slice-2 limits][consumer-limits] | Seven-year retention is a requirement, not evidence of an archive. No archive or pruning implementation or test is identified in these inputs. |
| Revocation and cascade bodies (Sections [1](#1-minimal-revocation-event-body)-[2](#2-minimal-cascade-event-body)) | Proposed | Partial, different mechanism. [Phylax `SqliteDispatchPermitStore._check_grant`][issuer-store]; [tests `test_grant_revoked_cascade_and_expired`, `test_finalization_grant_revoked`][issuer-tests]. [Oramasys `RevocationPort`, `SqliteAttemptStore.authorize_dispatch`][consumer-store]; [tests `test_rule4_refuses_a_revoked_grant`, `test_rule4_refuses_an_issuer_wide_revocation`][consumer-tests] | The issuer checks injected grant facts and the consumer checks an injected revocation port. Neither implements or validates the proposed body fields or approval-chain cascade processing. |
| Execution witness ([Section 4](#4-status-of-cascade-witness-fields)) | Open | None yet. Specification only: [E1 Section 9.1, Test map, E1-T-25][e1-tests]; [E1 unresolved witness fields][e1-open] | `test_e1_cascade_recovery_witness` is a proposed test name, not an executable test. Fields, publication/retention and authenticated read-back remain open. |

The [consumer test `test_ingest_accepts_revocation_events_and_authorize_ignores_them_as_revocation`][consumer-tests]
explicitly separates opaque event ingestion from revocation interpretation. Do not count ingestion
coverage as proof that the proposed revocation/cascade bodies or consumer anchor floor are implemented.

[e1-schema]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#13-specifications-closing-the-open-semantics-proposed-for-independent-review
[e1-open]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#not-resolved-from-repository-sources
[e1-approval]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#134-second-approval-decision-3-the-conditions-recorded-in-section-11
[e1-retention]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#133-retention-decision-2
[e1-tests]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md#91-test-map-resolves-e1-r09
[purpose]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md
[purpose-fields]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md#31-proposed-effect-grant-fields-closed-exact-set
[wire]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md
[wire-objects]: https://github.com/diazMelgarejo/orama-system/blob/59c623fa27497183d3a1c4ed19585d87623eae22/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md#1-permit-objects-proposed
[status]: https://github.com/diazMelgarejo/orama-system/blob/55ff8ef58ef6b6202f6f521c8b5b5a7452281e1c/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/2026-10-19-e1-specification-ratification-addendum.md#3-scope-of-parts-12-ratification-and-part-3-dependency
[issuer-store]: https://github.com/oramasys/phylax/blob/2d45556493190b1ca2a58ccede5b6b19d1daa1ad/src/phylax/dispatch_permit_store.py
[issuer-tests]: https://github.com/oramasys/phylax/blob/2d45556493190b1ca2a58ccede5b6b19d1daa1ad/src/tests/test_dispatch_permit_store.py
[consumer-store]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/src/orama/graph/dispatch_attempts.py
[consumer-tests]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/src/tests/test_dispatch_attempts.py
[consumer-limits]: https://github.com/oramasys/oramasys/blob/4c67d37c624d6bea1d4953c9777962d1f8e42a3c/docs/e1-c2-consumer-slice2.md#limits-and-open-items
