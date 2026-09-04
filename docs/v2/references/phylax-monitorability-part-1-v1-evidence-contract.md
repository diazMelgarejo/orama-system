# Phylax Monitorability — Part 1: v1 Evidence Contract MVP

**Status:** subordinate implementation guidance for the shipped v1 bridge

**Owners:** Perpetua-Tools (v1 contract and emitters), Phylax (future consumer)

**Normative authority:** [Doc 60 — Canonical Phylax Monitorability Design
Specification](../60-phylax-monitorability-design-spec.md). Doc 60 governs
ownership, evidence meaning, authority, privacy, liveness, and migration gates;
this part records only the PT v1 implementation boundary.

**Implementation modules:**
[Part 2 — derived inference](phylax-monitorability-part-2-derived-inference.md) ·
[Part 3 — migration and assurance](phylax-monitorability-part-3-migration-assurance.md)

## Purpose

v1 adds a machine-valid, privacy-redacted monitorability envelope to an existing
agent handoff before dispatch. It establishes the producer-side evidence and
adapter seam described by Doc 60; it does not implement Phylax monitor
semantics, retention, admission, or enforcement.

The shipped implementation reference is Perpetua-Tools PR #379 and its
associated redacted handoff work. Its queue-admission audit record is not a
presence action: validation, admission, logging, progress, advisory findings,
and stale cleanup do not refresh worker liveness.

## Contract

The existing `HandoffPacketV1` gains one optional strict field:

```python
monitorability: MonitorabilityEnvelopeV1 | None = None
```

Compatibility is strict and optional: a legacy v1 packet without
`monitorability` remains valid, but a packet that includes it must satisfy the
complete closed envelope. Validation must not synthesize, repair, or silently
discard an invalid supplied envelope. New standard producers emit it; only a
future versioned Phylax adapter may make normalized monitorability mandatory.

```python
class MonitorabilityEnvelopeV1(BaseModel):
    schema_version: Literal[1]
    otel: OTelGenAiContextV1 | None = None
    phylax: PhylaxMonitorabilityContextV1
    privacy: RedactedEvidencePolicyV1
    integrity: EvidenceIntegrityV1

class RedactedEvidencePolicyV1(BaseModel):
    raw_reasoning_persisted_in_packet: Literal[False]
```

`otel` records only a legitimate operation, provider, stable logical agent,
model, conversation, and W3C trace/span context. It must not invent a provider,
derive a conversation ID from content, or place hashes in standard identity
fields.

### Frozen OTel projection contract

The v1 adapter is pinned to `oramasys.phylax.otel-map.v1`, whose upstream
baseline is `open-telemetry/semantic-conventions-genai@94f432d7126f5884d30a2cdde6f4e89908ebb6fd`
(captured 2026-09-04). This is a reproducible input to the adapter, not a claim
that every developing GenAI semantic convention is stable or applicable.

| Projection class | Required or permitted fields | Rule |
| --- | --- | --- |
| W3C correlation | trace ID and span ID together | both validate as W3C IDs; neither is synthesized |
| pinned standard `gen_ai.*` | `gen_ai.operation.name` | required whenever `otel` is present |
| pinned standard `gen_ai.*` | `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model` | emit only when legitimately known; never infer from content |
| Oramasys extension | `oramasys.phylax.schema_version`, `oramasys.phylax.policy_pack.id`, `oramasys.phylax.policy_pack.version`, `oramasys.phylax.risk_tier` | redacted scalar metadata from the envelope |
| Oramasys extension | `oramasys.phylax.reported_monitor_decision`, `oramasys.phylax.severity`, `oramasys.phylax.confidence`, `oramasys.phylax.escalation_state`, `oramasys.phylax.retention_class`, `oramasys.phylax.reasoning_availability`, `oramasys.phylax.evidence_manifest_hash` | redacted scalar metadata; never a trusted Phylax decision or raw/sealed evidence |

Standard attributes retain their pinned semantic meaning and may not be renamed,
overwritten, or populated with hashed/content-derived substitutes. No
`oramasys.phylax.*` key may collide with a standard key; unknown,
incompatible, or non-additive changes fail closed and hold the projection until
an explicit mapping-version approval. Evidence IDs, sealed references, raw
reasoning, prompt/output/tool payloads, URLs, hosts, paths, and secrets are
never projected. The v2 adapter record carries `otel_mapping_id`,
`otel_semconv_baseline`, and the approved mapping-review identifier so Part 3
can run the same mapping regression against a fixed baseline.

The Phylax context contains policy-pack identity/version, risk tier,
capability-grant IDs, advisory decision (`allow`, `warn`, `escalate`), severity,
confidence, escalation state, retention class, reasoning availability, and
opaque evidence references. In v1 these are caller-reported context, not a
trusted Phylax decision: the shipped field is
`reported_monitor_decision: Literal["allow", "warn", "escalate"]`.
`block` is rejected by the v1 schema. Audit projection preserves that caller
status under `oramasys.phylax.reported_monitor_decision`; it must not relabel it
as a Phylax decision.

## Privacy and integrity rules

- Packets, GossipBus audit events, and normal OTel projections are redacted.
- Raw prompt/output/tool payloads, secrets, hosts, paths, URLs, CoT, and
  reasoning traces are invalid packet data.
- `reasoning_availability` is metadata only: `none`, `provider_summary`,
  `user_owned_raw`, or `sealed_reference`.
- A sealed reference is an opaque, bounded identifier. It cannot be a URI,
  path, credential, or content-bearing free-form string.
- Bounded PT identifiers match
  `^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$`. Opaque evidence, sealed, and grant
  references match `^(?:evidence|sealed|grant)_[0-9a-f]{16,64}$`; reference
  lists are non-empty and contain no duplicates. These grammar checks prevent
  identifiers from becoming content-bearing free-form fields.
- When `monitorability` is present, its required `privacy` object must include
  `raw_reasoning_persisted_in_packet: Literal[False]` with no default; omission
  and `true` are validation errors. This closed-envelope requirement does not
  make a false claim about separately governed Phylax incident storage.
- A manifest hash and ordered evidence references provide correlation; v1
  validates their syntax and internal consistency only.
- The `handoff_admitted` audit projection is allowlist-only. It projects the
  schema version, redacted policy/risk/advisory metadata, manifest hash, and
  provenance commit; it omits evidence references, sealed references, raw
  material, and high-cardinality content.

## PT MVP work sequence

1. Maintain tests for a complete envelope, closed nested models, malformed W3C
   IDs, invalid enum/authority values, the shipped opaque-reference grammar,
   recursive raw-content rejection, and non-liveness admission. The suite
   accepts an omitted `otel`, rejects an omitted or `true`
   `raw_reasoning_persisted_in_packet`, and rejects an unapproved OTel mapping
   before it emits a projection.
2. Add the Pydantic models and cross-field validators to
   `orchestrator/handoff_validation.py`; expose stable diagnostics only.
3. Keep the post-enqueue `handoff_admitted` projection explicit, redacted, and
   allowlist-only. Invalid input emits neither queue admission nor its audit
   event, and the audit record never becomes a liveness pulse.
4. Add a validating JSON fixture, Markdown template, mapping document, and
   migration note. The fixture uses `reasoning_availability: none`.
5. Run focused validation, CLI, and heartbeat tests; run the repository hygiene
   and Markdown checks before committing.

## Acceptance criteria

- Legacy v1 packets still validate unchanged.
- Envelope validation is strict, additive, and fail-closed.
- The optional `otel` field is actually optional under Pydantic 2; supplied
  monitorability still requires the `Literal[False]` raw-reasoning invariant.
- The pinned OTel mapping emits only its enumerated keys, and a changed mapping
  emits no projection before explicit approval.
- A supplied v1 advisory remains caller-reported, and `block` is invalid.
- Audit projection is allowlist-only and excludes raw/sealed/high-cardinality
  evidence data.
- PR #379's explicit successful worker presence action, not monitorability
  activity, is the liveness boundary.
- The v2 adapter boundary, not an implicit reinterpretation, governs migration.
