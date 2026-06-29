# Module: Redis Coordination

> Status: stub — **superseded in principle** by [`43-gossipbus-mesh-transport.md`](../43-gossipbus-mesh-transport.md) (frugal GossipBus mesh). Keep this stub only if a future operator explicitly requires Redis/Valkey.

## What it does

~~Replaces SQLite-based `GossipBus` with Redis pub/sub~~ **Preferred v2 path:** keep per-particle SQLite `GossipBus`; add optional `GossipMesh` tail/ingest between particles (orama + PT) without a central broker.

Redis pub/sub remains a **last-resort** escape hatch if mesh tail proves insufficient at scale.

## Decision gate

Do **not** implement Redis before v2.1 `GossipMesh` LAN tail is tried. v1 co-orchestration already coordinates via file inbox + portal probes without Redis.

## Design sketch

- `RedisBus` implements the same `emit()` / `subscribe()` interface as `GossipBus`
- Swappable via config: `GOSSIP_BACKEND=redis` vs `GOSSIP_BACKEND=sqlite`
- Redis channel naming: `perpetua:events:{session_id}`

## Dependencies

- `redis-py` async client (`redis[asyncio]`)
- Running Redis instance (or Valkey) on LAN
