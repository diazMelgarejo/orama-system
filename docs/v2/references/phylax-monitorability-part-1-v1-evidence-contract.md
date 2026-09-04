# Phylax Monitorability — Part 1: v1 Evidence Contract MVP

**Status:** implementation plan and v1 contract authority

**Owners:** Perpetua-Tools (v1 contract and emitters), Phylax (future consumer)

**Companion parts:** [Part 2](phylax-monitorability-part-2-derived-inference.md) · [Part 3](phylax-monitorability-part-3-migration-assurance.md)

## Purpose

v1 adds a machine-valid, privacy-redacted monitorability envelope to an existing
agent handoff before dispatch. It establishes evidence provenance and a stable
adapter seam. It does not observe, store, reconstruct, score, or train on raw
chain-of-thought (CoT).

The governing rule is:

> A monitorability signal may raise concern; only an independently observable
> policy violation and an authorized Phylax decision may enforce an action.

## Ownership and non-goals

| Component | v1 responsibility | Excluded responsibility |
| --- | --- | --- |
| Perpetua-Tools | strict packet validation, redaction, local audit projection, evidence references | monitor model, retention service, policy engine, remote collector |
| Phylax | names and owns future decision semantics | implementation in the PT validator |
| Telos | supplies endpoint-specific facts later | generic monitorability policy |
| Oramasys | composes application approval and routing later | duplicate event core or safety pack |

v1 must not add a monitor worker, an OTel collector, a telemetry database,
network export, raw reasoning persistence, or a liveness side effect. Queue
admission, logs, progress, and advisory findings are never heartbeats.

## Contract

The existing `HandoffPacketV1` gains one optional strict field:

```python
monitorability: MonitorabilityEnvelopeV1 | None = None
```

The field remains optional for legacy producers. New standard producers emit it;
a versioned Phylax adapter makes it mandatory only for a future v2 contract.

```python
class MonitorabilityEnvelopeV1(BaseModel):
    schema_version: Literal[1]
    otel: OTelGenAiContextV1 | None
    phylax: PhylaxMonitorabilityContextV1
    privacy: RedactedEvidencePolicyV1
    integrity: EvidenceIntegrityV1
```

`otel` records only a legitimate operation, provider, stable logical agent,
model, conversation, and W3C trace/span context. It must not invent a provider,
derive a conversation ID from content, or place hashes in standard identity
fields. Mapping is a strict superset of applicable developing `gen_ai.*`
semantics; Phylax extensions remain under `oramasys.phylax.*`.

The Phylax context contains policy-pack identity/version, risk tier,
capability-grant IDs, advisory decision (`allow`, `warn`, `escalate`), severity,
confidence, escalation state, retention class, reasoning availability, and
opaque evidence references. In v1 these are caller-reported context, not a
trusted Phylax decision. Name the source explicitly as `reported_monitor_decision`
or include an issuer/attestation state before projecting it to audit.

## Privacy and integrity rules

- Packets, GossipBus audit events, and normal OTel projections are redacted.
- Raw prompt/output/tool payloads, secrets, hosts, paths, URLs, CoT, and
  reasoning traces are invalid packet data.
- `reasoning_availability` is metadata only: `none`, `provider_summary`,
  `user_owned_raw`, or `sealed_reference`.
- A sealed reference is an opaque, bounded identifier. It cannot be a URI,
  path, credential, or content-bearing free-form string.
- Evidence IDs need a documented grammar, maximum length, and maximum count;
  a denylist on field names alone does not prevent sensitive data in values.
- The packet must say `raw_reasoning_persisted_in_packet: false`, not make a
  false claim about separately governed Phylax incident storage.
- A manifest hash and ordered evidence references provide correlation; v1
  validates their syntax and internal consistency only.

## PT MVP work sequence

1. Add failing tests for a complete envelope, closed nested models, malformed
   W3C IDs, invalid enum/authority values, opaque-reference grammar, recursive
   raw-content rejection, and non-liveness admission.
2. Add the Pydantic models and cross-field validators to
   `orchestrator/handoff_validation.py`; expose stable diagnostics only.
3. Extend queue admission after successful enqueue with an explicit allowlisted,
   redacted `handoff_admitted` projection. Invalid input emits neither queue nor
   audit event.
4. Add a validating JSON fixture, Markdown template, mapping document, and
   migration note. The fixture uses `reasoning_availability: none`.
5. Run focused validation, CLI, and heartbeat tests; run the repository hygiene
   and Markdown checks before committing.

## Acceptance criteria

- Legacy v1 packets still validate unchanged.
- Envelope validation is strict, additive, and fail-closed.
- `block` is invalid in v1; neither advisory metadata nor evidence references
  can grant merge, deployment, approval, or capability authority.
- Audit projection is allowlist-only and excludes raw/sealed/high-cardinality
  evidence data.
- Only an explicit pulse from the receiving worker changes liveness.
- The v2 adapter boundary, not an implicit reinterpretation, governs migration.
