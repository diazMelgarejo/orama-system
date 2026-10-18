# E1 C2 (part 1): integrated purpose, version and refusal contract

Status: PROPOSED specification for independent review. Not ratified, no code, no wire change, not
authorization for T3. It answers the pre-code prerequisite of E1 section 14 rule 3 and builds on
the source inventory in the [C1 record](E1-C1-SOURCE-RECOVERY-AND-TEST-MAP-2026-10-18.md).
Part 2 is the [permit wire and role reconciliation](E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md).

Pinned sources: Phylax `0c3e860749b3ff8f62e102679f1f415f8acf0a61`
(`adjustment_grant.py`, `grant_store.py`), Oramasys `b5f3821804715665b716ab600ea8419810bea920`.
Everything marked **existing** was read at those revisions; everything marked **proposed** is new.

## 1. What exists

- The closed refusal vocabulary, shared with Oramasys, is `grant.malformed`,
  `grant.schema_unsupported`, `grant.key_unknown`, `grant.signature_invalid`, `grant.expired`,
  `grant.future_dated`, `grant.revoked`, `revocation.stale` and `verifier.unavailable`.
- The recovery grant (settle or release) is schema 1. Its wire is a canonical JSON object with an
  exact 20-field set, ASCII keys, strings and safe integers only, at most 65,536 bytes. Its signed
  preimage is Ed25519ph framing under the domain `phylax-adjustment-grant-v1\x00`.
- `from_wire` rejects duplicate keys and non-canonical bytes, and **checks the exact field set
  before the version**. An extended body is therefore `grant.malformed`; only a body with the old
  field set and a different version reaches `grant.schema_unsupported`.
- The recovery grant has **no purpose field**. Its purpose is implied by the schema family and the
  domain string.

## 2. Principle: purpose is fixed by three independent mechanisms

A grant presented at a boundary of the wrong purpose must fail on each of them, so no single parser
bug or one forged field can cross purposes.

1. **Family and version.** Each purpose has its own `schema_version`.
2. **Explicit discriminator.** New-family bodies carry a `purpose` field that must agree with the
   version. Disagreement is ambiguity (section 4).
3. **Domain-separated signature.** The preimage domain is chosen from the parsed (version,
   purpose), never from a caller-supplied value, and a signature over one domain does not verify
   under another.

## 3. Proposed families

| Purpose | `schema_version` | `purpose` field | Preimage domain | Status |
| --- | --- | --- | --- | --- |
| Recovery settle or release | `1` | **absent (frozen legacy wire)** | `phylax-adjustment-grant-v1\x00` | existing, unchanged forever |
| Effect authority (one logical operation) | `2` | `"effect"` | `phylax-effect-grant-v2\x00` | proposed |

The recovery wire, parser and signed preimage are **not changed**. A schema-1 body that carries a
`purpose` field is malformed (exact field set). A schema-2 body that claims `"recovery"` is
ambiguous. Version 2 therefore never means "recovery with an extra field".

### 3.1 Proposed effect-grant fields (closed, exact set)

Same encoding rules as the recovery wire: canonical JSON, ASCII keys, strings and safe integers
only, no nulls, six-digit UTC timestamps, unpadded base64url signature, at most 65,536 bytes.

`schema_version`, `purpose`, `grant_id`, `principal`, `run_id`, `operation_id` (the logical
operation identifier), `request_digest` (exact digest of the operation request), `effect_class`,
`use_limit` (the integer `1`), `ledger_store_id`, `consumer_lease_epoch`, `second_approval_ref`
(a string, empty meaning single approval; never absent and never null, so the field set stays
exact), `issued_at`, `expires_at`, `issuer_key_id`, `issuer_ref`, `revocation_ref`,
`payload_digest`, `issuer_signature`. There is no `artifact_digest` in the grant: the issuer cannot
verify one, so the permit treats it as consumer-asserted (see part 2).

**Erratum to E1 section 13.4.** That section says an absent `second_approval_ref` means single
approval. An exact field set rejects a missing field, so on the wire "absent" is the empty string
and a missing key is `grant.malformed`. Policy language may still say "absent"; the wire does not.

An effect grant carries no `hold_id`, `units` or `kind`, so it cannot be parsed as an adjustment of
any hold, and it carries `operation_id` and `request_digest`, so it cannot be mistaken for one.

## 4. Parse and refusal order (proposed)

1. Size and UTF-8 limits, strict JSON, duplicate keys, object root, and **canonical bytes**
   (re-serialize the parsed object under the canonical rules and compare with the wire): failure is
   `grant.malformed`. A non-canonical body is therefore malformed whatever its family.
2. Read `schema_version` as an integer. An unknown value is `grant.schema_unsupported`.
3. Read the discriminator rules for that version: version 1 requires no `purpose`; version 2
   requires `purpose == "effect"`. A missing, unknown or disagreeing discriminator is
   `grant.malformed` (ambiguity).
4. Compare the grant's purpose with the **boundary's expected purpose**. A mismatch is
   `grant.schema_unsupported` and happens before any key lookup, signature work or store read.
5. Exact field set for that version, then the existing key, signature, expiry, skew and
   revocation checks. A canonical body of the wrong family is never field-set checked against the
   other family, so it reaches step 4 and is `grant.schema_unsupported`.

Step 2 before the field set is a **change to the parser order** and needs a Phylax change for the
new verifier. The pinned legacy parser runs the field set first, so the table below separates the
two behaviours and a test must pin whichever applies at the revision under test. Both refusals
are fail closed and precede any mutation.

| Presented grant | Boundary | Verifier | Result |
| --- | --- | --- | --- |
| Effect (v2) | Recovery | Legacy (pinned `0c3e860`) | `grant.malformed`: the 19-field effect set differs from the 20-field recovery set |
| Effect (v2) | Recovery | Updated, version first | `grant.schema_unsupported`: version 2 is not a recovery schema |
| Recovery (v1) | Effect | New effect verifier | `grant.schema_unsupported` at step 4 |
| Unknown version, old field set | Recovery | Legacy | `grant.schema_unsupported` (existing behaviour) |
| Unknown version, any other field set | Recovery | Legacy | `grant.malformed` (the field set is checked first) |
| Unknown version | Either | Updated, version first | `grant.schema_unsupported` |
| v2 without `purpose` | Effect | New | `grant.malformed` |
| v2 with `purpose: "recovery"` | Either | New | `grant.malformed` (ambiguous) |
| Duplicate key or non-canonical bytes, any family | Either | Either | `grant.malformed` (step 1 precedes the purpose comparison) |

`grant.signature_invalid` is never the answer to a cross-purpose presentation, because the
signature is not examined before step 4. `verifier.unavailable` means only that the verifier could
not answer.

## 5. No mutation on refusal

On every refusal in section 4, **before** the refusal is returned: no hold, ledger, outbox, receipt,
reservation, grant-use or permit row is created or changed, and no business-state digest moves.
Allowed: one sanitized audit record carrying the closed reason code, the boundary identifier, a
timestamp and the wire length. It carries no payload, credential, signature, principal or raw
error text. A test compares a full digest of the consumer and issuer stores before and after.

## 6. Correction to E1 section 13.4

Section 13.4 says an older verifier that does not know a new schema version refuses with the
existing `grant.schema_unsupported`. Against the pinned parser that holds only when the old field
set is kept. A new body that adds `second_approval_ref` or `purpose` is refused as
`grant.malformed`. The behaviour is still fail closed and nothing is silently ignored. The text
should say "refuses before mutation with a closed-set code, `grant.malformed` at the legacy parser
order, `grant.schema_unsupported` once the version is read first", and test both.

## 7. Proposed tests for E1-T-23 (expected outcomes; no executable claim)

Owner: new T3 tests. Rows 1 to 4 must be written against the legacy parser first and fail first.

1. Effect grant at the recovery verifier: expect the legacy code, store digests unchanged.
2. Recovery grant at the effect verifier: `grant.schema_unsupported`, store digests unchanged.
3. Version 2 without `purpose`, with `"recovery"`, with an extra field and with a missing field.
4. Duplicate key, non-canonical bytes, oversize body.
5. Domain separation: a valid effect signature moved into a recovery body, and the reverse, never
   verifies; the domain is chosen from the parsed family, not from input.
6. Canonical serialization vectors shared by issuance and consumer verification (byte-identical).
7. Sanitized refusal audit contains no payload, credential, signature or raw error text.
8. Purpose is enforced at **every** boundary that accepts effect authority, including the first
   bounded slice, so recovery authority is never temporarily accepted as effect authority.

## 8. Not decided here

A new refusal code for purpose mismatch was considered and rejected: the vocabulary is shared by
two repositories and a change there needs its own contract. Which Phylax release carries the
version-first parser order, and the `effect_class` registry, are left to the integrated schema
review.
