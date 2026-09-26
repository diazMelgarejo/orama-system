# Module: Redis Coordination

> Status: stub — **superseded in principle** by
> [`43-gossipbus-mesh-transport.md`](../43-gossipbus-mesh-transport.md) (frugal GossipBus mesh).
> Keep this stub only if a future operator explicitly requires Redis/Valkey.

## What it does

~~ReplacesSQLite-based`GossipBus`withRedispub/sub~~**Preferredv2path:**keepper-particleSQLite
`GossipBus`;addoptional`GossipMesh`tail/ingestbetweenparticles(orama+PT)withoutacentralbroker.

Redis pub/sub remains a **last-resort** escape hatch if mesh tail proves insufficient at scale.

Neither GossipMesh nor a future Redis backend is a claim authority. Atomic
remote claims, leases, and recovery remain the deferred v2.1
[`Orchestrator Controller`](../68-orchestrator-controller-satellite.md)
protocol; changing event transport must not create a second job-state writer.

## Decision gate

Do**not**implementRedisbeforev2.1`GossipMesh`LANtailistried.v1co-orchestrationalreadycoordinatesvia
fileinbox+portalprobeswithoutRedis.

## Design sketch

- `RedisBus` implements the same `emit()` / `subscribe()` interface as `GossipBus`
- Swappable via config: `GOSSIP_BACKEND=redis` vs `GOSSIP_BACKEND=sqlite`
- Redis channel naming: `perpetua:events:{session_id}`

## Dependencies

- `redis-py` async client (`redis[asyncio]`)
- Running Redis instance (or Valkey) on LAN
