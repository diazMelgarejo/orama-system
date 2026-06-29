# 43 — GossipBus mesh transport (frugal particle gossip)

> **Status:** Planned — v2.1+ non-kernel module  
> **Date:** 2026-06-29  
> **Parent:** [`01-kernel-spec.md`](01-kernel-spec.md) §5 (local `GossipBus`), [`20-rag-and-memory-design.md`](20-rag-and-memory-design.md)  
> **v1 dogfood:** Mac↔Win file inbox + `ws-peer` + portal probes ([`lan-peer-bidirectional-talk-2026-06-28.md`](../guides/lan-peer-bidirectional-talk-2026-06-28.md))

---

## Thesis

**This is how we gossip.** Cooperating **particles** (an `orama-system` portal, a `Perpetua-Tools` supervisor, or a future `perpetua-core` runtime on the same mesh) exchange **small, append-only GossipBus deltas** — not full SQLite replicas, not a central message broker.

Gossip is the coordination primitive: who saw what, what changed, what needs human eyes. File inbox and `win_job_queue` remain the **audit trail** and operator handoff lane; mesh gossip is the **low-latency fan-out** for events operators and agents already emit locally.

---

## Particle model

| Particle | Local GossipBus | Typical events |
|----------|-----------------|----------------|
| **orama** (`portal_server`) | Optional mirror / audit hook | swarm preview, lifecycle, discovery load, L1 dispatch |
| **PT** (`orchestrator/supervisor`) | `orchestrator/gossip_bus.py` (v1 shipped) | job complete, dispatch, FTS recall hits |
| **perpetua-core** (v2 kernel) | `perpetua_core/gossip.py` | graph node start/end, affinity_check, authorization |

Each particle keeps its **own** append-only log (Rule 4). Mesh transport **replicates interest-filtered tails** between cooperating peers — never replaces local durability.

---

## Frugality rules (non-negotiable)

1. **Delta-only** — sync `since_ts` / `since_id` cursors; never ship whole `.db` files on the wire.
2. **Interest filters** — subscribe by `event_type`, `session_id`, `particle_id`, or `topic` prefix; default deny wide fan-out.
3. **Rate limits** — cap events/sec per peer; batch ≤50 events or 500ms (same hot-write cadence as kernel §7c).
4. **Idempotent ingest** — `(particle_id, event_id)` dedupe on receiver; duplicates are OK on lossy transports.
5. **No new infra by default** — no Redis/NATS requirement ([`02-modules/redis-coordination.md`](02-modules/redis-coordination.md) stays deferred; mesh gossip supersedes that sketch for LAN).
6. **Redaction before egress** — same `classify_and_redact` path as v1 PT GossipBus; mesh must not widen the secret blast radius.

---

## Transport ladder

```text
v1 (now)     LAN HTTP + file inbox + ws-peer     operator-visible, auditable, proven
v2.1         GossipMesh over LAN (HTTP/WS)       tail/subscribe between particles
v2.2+        mDNS peer discovery + optional relay  same API, less operator wiring
v3?          BLE mesh (bitchat-class)            offline, proximity-sized cells; same event envelope
```

### v2.1 — `GossipMesh` (LAN)

Minimal surface on each particle:

```text
GET  /api/gossip/tail?since=<cursor>&types=load,dispatch,error
POST /api/gossip/ingest   # bearer + capability `read` / `mutate` per direction
```

- **Transport:** reuse portal bearer auth + CSRF/origin guards (same bar as P5/P6).
- **Discovery:** `last_discovery.json` / `discover.py` endpoints — no hardcoded IPs.
- **Win↔Mac:** symmetric; either particle may initiate tail pull (coord cycles already sync git; gossip sync is orthogonal).

### v3? — Bluetooth / BLE mesh (bitchat analogy)

[bitchat](https://github.com/permissionlesstech/bitchat) and similar apps show **offline, serverless** multi-hop messaging over BLE. We do **not** commit to BLE in v2.1.

**If** we add it later:

- Same **event envelope** as LAN mesh (versioned JSON, `particle_id`, `event_id`, `event_type`, redacted `payload`).
- **Smaller payloads** — BLE MTU budgets; aggressive summarization for `dispatch` bodies.
- **Shorter TTL** — proximity mesh is ephemeral; durable truth stays on each particle's SQLite.
- **Human-in-the-loop** for cross-security-domain ingest (MAESTRO Layer 3 / P5-style tokens for mutating fan-out).

OQ29 tracks BLE vs LAN-only scope.

---

## Relationship to v1 co-orchestration

| Mechanism | Role | Mesh gossip |
|-----------|------|-------------|
| File inbox (`~/.openclaw/state/lan_peer/inbox`) | Durable operator artifacts, plans, acks | Complement — large markdown stays in inbox |
| `job_cycle_listen.sh` | Idle sync + probe | Complement — can trigger gossip tail pull |
| `win_job_queue` / `mac_job_queue` | Actionable job gate | Complement — queue = work; gossip = telemetry |
| `job_cycle_listen.log` | Mac idle-cycle telemetry (sync, probe, gate) | **Not** GossipBus transport — operator log only; no event ingest |
| Portal swarm/L1 APIs | Mutating control plane | Gossip **observes** dispatches; does not replace HITL |

Cross-host **mutations** still go through authenticated APIs (P5 tokens, PT `/v1/jobs`). Mesh gossip is for **observability and soft coordination**, not unsigned remote execution.

---

## Module placement

| Layer | Package | Notes |
|-------|---------|-------|
| Kernel | `perpetua_core/gossip.py` | Local `emit` / `subscribe` only |
| Orbit | `oramasys/mesh/gossip_mesh.py` (proposed) | LAN tail/ingest, peer registry |
| PT adapter | `orchestrator/gossip_mesh_client.py` (proposed) | Optional; off by default |
| BLE | `oramasys/mesh/transports/ble.py` (future) | Behind feature flag + OQ29 |

**Import boundary unchanged:** `perpetua-core` does not import mesh transports.

---

## Acceptance criteria (v2.1 LAN mesh)

- [ ] Two particles on LAN exchange `dispatch` events within 2s of local `emit` (happy path).
- [ ] Receiver dedupes replays; sender survives restart without corrupting peer log.
- [ ] Ingest without bearer → 401; ingest with redacted-class violation → drop + audit.
- [ ] Bandwidth: ≤10 KB/s sustained per peer at default filters (frugality budget).
- [ ] File inbox path still works when mesh is disabled (`GOSSIP_MESH=off`).

---

## Open questions

See [`06-open-questions.md`](06-open-questions.md) **OQ29** (BLE scope), **OQ30** (CRDT vs cursor tail).

---

## References

- v1 GossipBus impl: `Perpetua-Tools/orchestrator/gossip_bus.py`
- Kernel spec: [`01-kernel-spec.md`](01-kernel-spec.md) §5, §7c
- RAG plane: [`20-rag-and-memory-design.md`](20-rag-and-memory-design.md)
- L1 / swarm HITL: [`../plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](../plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md)
- Frugality doctrine: [`26-tdd-and-outsourced-review-doctrine.md`](26-tdd-and-outsourced-review-doctrine.md) §3
