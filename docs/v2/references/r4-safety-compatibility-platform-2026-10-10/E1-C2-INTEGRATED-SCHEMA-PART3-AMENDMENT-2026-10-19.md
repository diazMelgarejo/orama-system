# E1 C2 (Part 3): Integrated Schema Contract Amendment — Revocation, Cascade, and Retained-Anchor Checkpoints

**Status:** PROPOSED AMENDMENT for independent review (Codex, Cline) and operator ratification.
**Precondition Context:** Answers E1 Section 14 Rule 3 and resolves items left "pending the
integrated schema review" in [E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md](E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md)
lines 485, 1023, and 1030.
**Companion Documents:**

* Part 1: [`E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md`](E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md)
  (19-field grant v2, default-deny classification, closed refusal vocabulary).
* Part 2: [`E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md`](E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md)
  (permit wire, finalization wire, multi-role reconciliation).
* Status Addendum: [`2026-10-19-e1-specification-ratification-addendum.md`](2026-10-19-e1-specification-ratification-addendum.md).

---

## 1. Minimal Revocation Event Body

Per `E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md` lines 250–251, Step 4.3 Rule 4
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

Per `E1-AUTHORITY-STATE-EFFECT-FREEZE-DRAFT-2026-10-15.md` lines 638–668:

> "Each issuer cascade emits a durable notification identifying the affected approval and
> grants, issuer authority version and cascade event. The issuer records authority facts only;
> it does not query consumer execution state."

The frozen canonical body carries:

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

Per `E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md` lines 145–147:

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
   to fulfill the seven-year retention requirement (E1 Section 13.3). They are never deleted or
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

Consumer-side execution recovery witness fields (E1 Draft lines 1022–1023) remain **open**. They
are not frozen by this Part 3 amendment and will be defined alongside the telemetry and
observability contract slice. That later slice must close all of these gates before it can claim a
witness contract: (1) the concrete field set, types, canonical encoding, and durable identity;
(2) the publication medium, retention owner, and durability boundary; and (3) an authenticated
read-back mechanism that verifies the published record and defines failure as unavailable rather
than empty success. Until then, a missing or unreadable witness remains a fail-closed recovery
condition, not evidence of no affected work.

---

## 5. Summary of Frozen Field Sets for Schema Review

| Contract Entity | Defined Wire Fields | Specification Basis |
| :--- | :--- | :--- |
| **`revocation` Event Body** | `subject_kind` (`"grant" \| "approval" \| "issuer"`), `subject_id` (`str`: grant_id, second_approval_ref, or issuer_id) | Wire 250–251 |
| **`cascade` Event Body** | `approval_id` (`str`: second_approval_ref), `grant_ids` (`list[str]`), `issuer_authority_version` (`int`) | Draft 639–668 |
| **Anchor Checkpoint** | Retained `issuer_events` row: `version`, `kind`, `body`, `previous_event_digest`, `event_digest`, `issuer_key_id`, `signature` | Wire 145–147 |
| **Consumer Anchor Floor** | `anchor_version` in `issuer_cascade_ack`; gating $R_p \ge \text{anchor\_version}$ under Step 4.3 Rule 4 | Wire 146–147; Consumer Coverage Invariant |
| **Grant v2 (Reconfirmed)** | 19 closed fields from Purpose Contract 3.1 | Purpose Contract 50–59 |
