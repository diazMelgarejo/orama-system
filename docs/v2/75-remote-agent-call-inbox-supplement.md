# 75 — Remote agent call: an inbox supplement, not a third transport

> **Repository standard:** additive. See
> [`46-repository-standard.md`](46-repository-standard.md).
> **Status:** DESIGN NOTE. NOT IMPLEMENTED. NOT RATIFIED.
> **Date:** 2026-11-15
> **Scope:** the call a peer makes when it wants another peer to do one unit
> of work. Design only. No code in this note.
> **v1 relationship:** the file inbox remains the audit trail and the whole
> call when the mesh is off. This note does not wrap a v1 CLI and does not
> replace `lan_peer_assign.py`.

## Parents

Orama `docs/v2`:

- [`43-gossipbus-mesh-transport.md`](43-gossipbus-mesh-transport.md).
  Delta sync, interest filters, redaction before egress. Gossip observes.
  It does not execute.
- [Doc 45](45-single-operator-lan-threat-model-descope.md).
  This LAN is one operator's machines. Do not add a stranger-quorum.
- [Doc 47](47-portable-memory-local-topology-invariant.md).
  Envelopes carry opaque ids. No host address, path, or secret.
- [`49-peer-mesh-auth-tls-v2-plan.md`](49-peer-mesh-auth-tls-v2-plan.md).
  Bearer only on pinned TLS. The plain portal stays on loopback.
- [`50-mesh-security-migration-ladder.md`](50-mesh-security-migration-ladder.md).
  Phase D is the v2 cutover. A new peer is acknowledged, not silently stored
  as reachable.
- [Doc 61](61-pt-coordination-principal-identity-design.md).
  Author, actor, and capability stay distinct.
- [`68-orchestrator-controller-satellite.md`](68-orchestrator-controller-satellite.md).
  The controller commits the claim. Gossip cannot.
- [`69-agent-envelope-standard.md`](69-agent-envelope-standard.md).
  One envelope. No fifth transport.

Perpetua-Tools `docs`:

- Coordination consolidation, 2026-07-17. The v2 controller is a separate
  protocol, not an in-place replacement of the v1 coordination CLI.
  `docs/next/2026-07-17-coordination-module-consolidation-plan.md`
- Phase 0F CLI contract. The v1 CLI stays frozen. This call adds no command.
  `docs/wiki/13-coordination-phase-0f-cli-contract.md`
- Consolidation part 3, 2026-08-23. Automatic expiry belongs to v2.
  v1 cleanup stays manual.
  `docs/next/2026-08-23-coordination-consolidation-part3-plan.md`
- Mesh security pointer, 2026-07-27. The mesh secret is harmonized out of
  band and is never pasted into a call.
  `docs/next/2026-07-27-mesh-security-pr222-orama-pointer.md`
- LAN gossip progress, 2026-07-13. The shipped bridge replicates events.
  It does not grant a lease.
  `docs/plans/2026-07-13-pr211-lan-gossip-progress.md`

## Files checked for numbering

The highest numbered `docs/v2` file on this branch was
`74-lost-run-takeover-entrypoint-design.md`. Dated names under
`docs/v2/plans` and `docs/v2/references` are not sequence numbers. This note
is 75.

## Decision

A remote agent call is one envelope submitted to the controller. The body is
a content digest, an inbox filename, an assignee role, and a topic. The
markdown stays in the file inbox. The call does not carry the essay, a host
address, or a credential.

If the mesh is off, or the saved peer does not answer, the inbox drop is the
whole call. Discovery then keeps that address and marks it stale. A later
run tries it again before any scan replaces it.

## Who owns which step

| Step | Owner | This call |
| --- | --- | --- |
| Envelope header and local emit | `oramasys/perpetua-core` | Validates the header. Imports no mesh code. |
| Claim, lease, idempotency, redacted outbox | `oramasys/oramasys` controller | One transaction, as in doc 68. |
| Pinned TLS dial | `oramasys/telos` | The saved peer, TLS front end only. |
| Caller admission | `oramasys/phylax` | Refuses an unverified or expired capability. |
| Hardware placement | `oramasys/agate` | May name a machine. Cannot authorize. |
| Event fan-out | GossipMesh, doc 43 | Replicates the redacted event after commit. |

A gossip event cannot claim, renew, complete, release, or recover the work.
The v1 intra-host board and the LAN file inbox remain two boards. A note on
one is not a note on the other. A harness mailbox is not either board.

## Call shape

1. The caller writes the artifact with the existing file drop, or already
   holds it. The drop's own result is the delivery record: `ok` true,
   `received_at`, and a byte count equal to the file. A matching receiver
   digest is required before the bytes are called content-verified. Portal
   acceptance is not that record. An outbox state word is not that record.
2. The caller submits one controller request. The body is the digest, the
   filename, the assignee role, and the topic.
3. Phylax admits the caller. Telos dials the saved endpoint on the pinned
   TLS front end. The plain portal stays on loopback. A bearer does not
   travel on plain HTTP.
4. The peer controller, when the effect is a claim, commits its own lease
   and then emits a redacted outbox event. The caller's gossip log does not
   create that lease.
5. GossipMesh replicates the event. Interest filters apply. A replay with
   the same event id is a no-op.
6. If the dial fails, the saved endpoint is marked stale and the inbox file
   remains the assignment.

## What this note refuses

- A new socket, broker, or third transport beside the inbox, the channel,
  and GossipMesh.
- A network wrapper around `agent_coordination.py` or `lan_peer_assign.py`.
- Hardcoded peer addresses, or a scan that promotes a new peer to reachable
  before acknowledgement.
- Witness quorum, reputation decay, or equivocation detection on this LAN.
  Doc 45 already descoped those for a single operator.
- Treating ports 8000, 8001, and 8002 as proof that the TLS front end is up.
  The model server and the portal are separate listeners.
- Adopting uncommitted working-tree edits. Idempotency and expiry follow
  doc 68 as reviewed. A later store change needs its own review.

## Acceptance for a later implementation

- Mesh disabled: the same assignment is still delivered by the file drop.
- Ingest without a bearer returns 401. A redacted-class violation is dropped
  and audited.
- A claim without a controller receipt does not change task state.
- Repeating the same idempotency key returns the recorded receipt and does
  not open a second lease.
- The envelope and the outbox event contain no address, path, or secret.
- A failed try of a saved peer sets that record stale and leaves the inbox
  file in place.

## Open point

Doc 68 already says a partial controller exists in `oramasys` and is not
reviewed, not deployed, and not on a serving path. This note does not
activate it. The operator decides when a reviewed slice may implement the
call.
