# 69 — Agent Envelope Standard (identity card, kinds, tiers)

> **Status:** published v2 standard (promoted by the human operator, 2026-09-27);
> no runtime contract is changed by this document  
> **Document owner:** `orama-system` (this specification)  
> **Schema and validator owner (v2):** [`oramasys/perpetua-core`](https://github.com/oramasys/perpetua-core)
> — neutral header, tier rules, deterministic validators  
> **Standard implementers:** `Perpetua-Tools` for v1 artifacts, `oramasys/perpetua-core`
> for v2 artifacts  
> **Parents:** [`68-orchestrator-controller-satellite.md`](68-orchestrator-controller-satellite.md),
> [`43-gossipbus-mesh-transport.md`](43-gossipbus-mesh-transport.md),
> [`48-board-job-source-line-schema.md`](48-board-job-source-line-schema.md),
> [`55-oramasys-agent-observability-contract-adr.md`](55-oramasys-agent-observability-contract-adr.md),
> [`61-pt-coordination-principal-identity-design.md`](61-pt-coordination-principal-identity-design.md)  
> **Provenance:** [`references/2026-09-27-envelope-standard-provenance.md`](references/2026-09-27-envelope-standard-provenance.md)

---

## 1. Decision

An envelope is the **identity card of one unit of work**. It carries a fixed
universal header, a small kind-specific panel, and — only when the case applies —
declared conditional fields.

This standard exists because the same envelope grew independently in three
places (memory prose, handoff, and the controller request). It does not add a
fifth transport or a new plane; it states the header those three already needed.

**Roles (operator decision, 2026-09-27).** Three roles are deliberately distinct
and must not be collapsed:

| Role | Holder | Boundary |
| --- | --- | --- |
| Document owner | `orama-system` | Owns this specification text and its versioning |
| Schema and validator owner (v2) | `oramasys/perpetua-core` | Owns the neutral header, tier rules, and deterministic validators; imports nothing from Phylax, Telos, or the controller |
| Standard implementer | `Perpetua-Tools` (v1), `oramasys/perpetua-core` (v2) | Wires the header into its artifacts and emits conforming records |

Per-kind validators stay with their kind's owner: `HandoffPacketV1` (PT) for
delivery, the controller (§7) for claim, the standalone round record for rounds.

## 2. Scope

**In scope:** the universal header, the four envelope kinds that exist today
(`authorship`, `status`, `delivery`, `claim`) plus the round sibling, the tier
rules, projection rules, validation, and migration.

**Out of scope (explicit):**

- **Hermes dispatch envelopes (L0/L2/L3) are excluded.** They stay as they are;
  this standard neither absorbs nor renames them.
- No new transport, no new plane, no new repository.
- No v1 field is renamed, and no legacy row becomes non-conformant.

## 3. The identity card

| Card panel | Envelope element | Why it is there |
| --- | --- | --- |
| Holder (presenting now) | `actor{agent_id, instance_id, identity_verified}` | the only identity that can be verified |
| Author (originated the work) | `author{agent_id, model, availability}` | credit stays with the author |
| Chain of custody | `lineage{on_behalf_of, prior_agent, prior_agent_status, takeover, superseded_ref}` | stamped **only** when the two faces differ |
| Issuing authority | claim `principal` plus verified capability | a self-printed card is not a credential (doc 61) |
| Validity window | `created_at`, plus conditional `expires_at` | expiry is required for claims and rounds |
| Entitlements | the kind-specific `authority` literal and operation | what this card permits, nothing more |
| Endorsements | `evidence_anchors[]`, `tests[]`, `human_authorized` | the stamps that justify the record |
| Tamper evidence | `digest`, `redaction.allowlist_digest`, frozen values, `extra="forbid"` | detect alteration instead of trusting the bearer |
| Card number | `envelope_id` | unique, correlatable, dedupable |

### 3.1 Tiers

**Tier U — universal (no default).** `envelope_id`, `envelope_schema_version`,
`envelope_kind`, `created_at` (tz-aware), `privacy_tier`,
`author{agent_id, model, availability}`,
`actor{agent_id, instance_id, identity_verified}`, `redaction.applied`. A missing
Tier U field is a validation error, never a silent default.

**Tier K — kind-required.** Only what that kind means (§5–§8). A kind's required
panel is normative for that kind and irrelevant to others.

**Tier C — conditional (declared, not omitted).** Present only when the case
applies, otherwise declared as `None`/empty under `extra="forbid"`, so absence is
a recorded decision: `correlation{trace_id, span_id, run_id, task_id, round_ref}`,
`content_class`, `redaction.policy_version`, `redaction.fields_dropped`,
`redaction.allowlist_digest`, `expires_at` outside claim/round,
`actor.principal_id` (claim only), `round_ref` on delivery, `supersedes_round_ref`,
`out_of_scope_refs`, `stop_condition_detail_refs`, `pr_url`, `monitorability`,
`lineage`, `takeover`, `superseded_ref`.

### 3.2 Planes and kinds are orthogonal

The four planes classify *where* a record operates (execution, transport,
orchestration, observability); `envelope_kind` classifies *what it means*. A
`delivery` record may be projected from the execution plane to the observability
plane without becoming a new kind or a new transport contract. `TaskEnvelope`,
`WorkerResult`, and `MonitorabilityEnvelopeV1` keep their existing names and
shapes (§14).

## 4. Authorship kind

Required: `date`, `evidence_anchors[]`, `rationale_digest`, plus the common
`author`/`actor` panels — author and model are the card's back face, not new
fields.

`availability` is an **observation** by the actor at write time (`active`,
`inactive`, `unknown`). Writing it never updates a heartbeat store, never affects
a claim, and never confers authority. An inactive or unknown author stays that
way; verification applies to `actor.identity_verified` only.

### 4.1 `rationale_digest` rule (operator decision, 2026-09-27)

1. **`session_id` is required** on every envelope that carries a
   `authorship.rationale_digest`. Sessions are always named.
2. **Salt:** session-salted **HMAC-SHA256**, the doc 55 destination-hash scheme,
   so the digest is verifiable in the record and in the hash chain once
   implemented.
3. **Never salt-less:** a plain hash is non-conformant.
4. **Last-resort fallback:** if a `session_id` is genuinely missing or lost, use a
   per-record random salt, **record it in the hash chain as well as alongside the
   digest**, and flag the record as a non-normal condition.

## 5. Status kind

Required: `authority = "read_only"`, `liveness_effect = "none"`, `observed_at`,
plus the Tier U header.

A status record reports what one actor observed. It is **not** a liveness write
and cannot change any claim, lease, heartbeat, or queue-write right. Envelope
authorship of `availability` (§4) and the status kind are the same discipline:
observation is never state mutation. The first shipping implementation is the
PT `status` helper (I2), which must carry the header and publish no identity,
paths, or secrets.

## 6. Delivery kind

Required: `session_id`, `job_id`, `task_id`, `assigned_agent_id`, role, intent,
branch, `worktree_ref`, `starting_head`, `current_head`, `commit_sha` (exactly
40-hex), `files_changed`, tests, `human_authorized`, and the two literals
`merge_authorized=false`, `deployment_authorized=false`.

`round_ref` is the **only** round linkage: optional, pointing at a standalone
round record. A delivery envelope never carries an inline round block.
`task_id` and the assignee belong to `HandoffPacketV1` (§9).

`expected_base_sha` (doc 48) accepts 7–40 hex while `commit_sha` requires exactly
40; the two are asserted separately and never collapsed.

## 7. Claim kind maps to doc 68

A claim envelope's kind panel **is** the
[`doc 68 §4.2`](68-orchestrator-controller-satellite.md) request: `operation`,
`task_id`, `principal`, `idempotency_key`, `expected_task_version`, `source_ref`,
`expected_base_sha`, `capability_proof`.

This standard adds the **header only**. It does not restate, soften, or
supersede the claim contract: doc 68 remains normative for claim mechanics,
leases, idempotency scopes, recovery, and the response receipts. `principal`
lives only on a claim wrapper and is never authentication by itself; Phylax
verifies the capability proof.

## 8. Round sibling

A standalone `CoordinationRoundEnvelopeV1` owns `round_id`, plus `session_id`,
`controller_id`, `objective_ref`, `stop_condition_codes`, `ordered_handoff_refs`,
`authorization_ref`, `authority = "coordination_only"`,
`liveness_effect = "none"`, `created_at`, and `expires_at`.

Rounds stay a **sibling** of this standard's kinds: delivery points at a round
through `round_ref`, and no inline round payload exists anywhere.

## 9. Projections

A record may project a task, principal, or round value **only** when its
canonical owner, allowed location, and failure behaviour are explicit.

| Projection | Canonical owner | Rule |
| --- | --- | --- |
| `correlation.task_id` | `HandoffPacketV1` for delivery; [`doc 68 §4.2`](68-orchestrator-controller-satellite.md) for claims | If both appear in one wrapper, exact equality is required after native validation; a mismatch rejects |
| `correlation.round_ref` | standalone round record owns raw `round_id` | Must equal `delivery.round_ref` when both appear and resolve to exactly one round record |
| `actor.principal_id` | doc 68 §4.2 claim `principal` | Allowed only on a claim wrapper, exact equality required, never authentication |

A mismatch is rejected **before** state or capability lookup, and no projection
ever grants authority.

## 10. Retention and privacy

- **Retention boundary (operator decision, 2026-09-27):** envelope-derived
  persistence defaults to **90 days maximum**, overridable by configuration
  variable.
- The controller and the telemetry/observability path redact **under their own
  respective policies**; this standard does not change any other existing policy.
- `privacy_tier` uses doc 55's vocabulary (`internal_only`, `redacted`).
  `content_class` is a separate, optional, orthogonal classification that may
  carry v1-style values; it is never conflated with privacy tier, and the
  remote-export prohibition stays tied to privacy tier.

## 11. Existing mappings

| Existing contract | Relationship to this standard |
| --- | --- |
| `HandoffPacketV1` | Keeps its own validator and `schema_version`; may carry the common header. It remains the canonical owner of delivery `task_id` and the assignee |
| `TaskEnvelope` / `WorkerResult` (doc 12 plane 1) | Names and shapes kept. May carry a `delivery` profile; `depth ALWAYS 0` is an invariant-as-a-field |
| `MonitorabilityEnvelopeV1` (docs 55/60) | Kept as a payload. This standard wraps it and never supersedes it |
| Standalone `CoordinationRoundEnvelopeV1` | Owns `round_id`; referenced by `round_ref` only |
| Doc 48 source line | Optional and provisional in v1; becomes mandatory for new jobs under doc 68's v2.1 protocol |
| PT memory prose (`agent-envelope:`) | Historical `agent=` token is the **author**; `actor=` is the presenting identity. The nine stored envelopes need no rewrite |
| Hermes dispatch (L0/L2/L3) | **Excluded** from this standard |

## 12. Validation and migration

- Validators are **deterministic**: `oramasys/perpetua-core` owns the neutral
  header and tier rules, while per-kind validators stay with their kind's owner
  (§1).
- Unknown fields are forbidden (`extra="forbid"`), tier U fields have no default,
  and tier C fields are declared explicitly as `None`/empty when not applicable.
- **Migration is a disposition, not a rewrite.** v1 artifacts stay valid as v1;
  `envelope_schema_version` applies only to an opted-in wrapper, and a v1 row is
  never treated as an incomplete v2 row. Legacy rows need an explicit migration
  or handoff disposition before any field becomes required.

## 13. Relationship to the increments

- **I2 (`status` + header) is first:** purely additive, no new authority. Its
  current tip already publishes no paths, identity, or secrets and hard-enforces
  `queue_write_authority=false`.
- **I3** (worker restart) reports rather than writes.
- **I4** (publish bridge `source_ref`) stays evidence.
- **I5** (real relay) is a doc 68 claim flow and remains gated on the controller
  existing; without `claim` there is no replay-safe idempotent claim.
- **Implementers:** `Perpetua-Tools` lands the v1 wrapper and the status/header
  conformance tests; `oramasys/perpetua-core` lands the v2 neutral schema and
  validators.

## 14. Non-supersession list

This standard may supersede: the common header, `envelope_id` dedup semantics,
the redaction receipt, correlation naming, and kind/profile mapping.

It **must not** supersede, rename, or absorb:

- the LAN transport envelope and the budget envelope;
- `MonitorabilityEnvelopeV1`, `TaskEnvelope`, and `WorkerResult`;
- Hermes dispatch envelopes (L0/L2/L3);
- [`doc 68 §4.2`](68-orchestrator-controller-satellite.md) claim mechanics,
  which stay the normative claim contract.

## References

- [`68-orchestrator-controller-satellite.md`](68-orchestrator-controller-satellite.md)
  — claim contract, controller invariants `IC-1`…`IC-29`, home decision.
- [`55-oramasys-agent-observability-contract-adr.md`](55-oramasys-agent-observability-contract-adr.md)
  — privacy tiers and the session-salted HMAC-SHA256 scheme.
- [`48-board-job-source-line-schema.md`](48-board-job-source-line-schema.md)
  — `source_ref` / `expected_base_sha`.
- [`47-portable-memory-local-topology-invariant.md`](47-portable-memory-local-topology-invariant.md)
  — no topology, paths, or identity in artifacts.
- [`references/2026-09-27-envelope-standard-provenance.md`](references/2026-09-27-envelope-standard-provenance.md)
  — trimmed history of how this standard was assembled.
