---
name: gossip-bus
description: >-
  Operate the GossipBus event bus for multi-agent coordination across both
  transports: intra-host (same-machine, SQLite FTS5 event log) and inter-host
  (LAN peer, WS/SSE + file-drop fallback). Activates for: gossip bus, emit
  event, agent coordination events, cross-machine messaging, mac win peer
  sync, lan peer channel, peer file drop, intra-host vs inter-host gossip.
version: 1.0.0.0
license: Apache 2.0
compatibility: python>=3.9, orama-system, perpetua-tools
allowed-tools: bash, file-operations
parent_skill: orama-system
triggers:
  - gossip bus
  - emit event
  - intra-host coordination
  - inter-host coordination
  - lan peer channel
  - mac win peer sync
  - peer file drop
  - cross-machine gossip
author: Claude Sonnet 5 <noreply@anthropic.com>
---

# GossipBus

## Purpose

Give agents one event-bus concept — "gossip" — that works whether the peers
sharing state are worktrees/processes on the **same machine** or separate
**Mac/Win hosts on the LAN**. The wire differs; the envelope shape and the
intent (append an event, let others discover it) do not.

## When to Use

- Two or more agents (same machine, different git worktrees, or different
  hosts) need to see each other's claims, heartbeats, or coordination events.
- You're deciding whether same-machine coordination needs new infrastructure
  — it almost never does; reuse GossipBus first (see Core Concepts).
- You need to hand data or a task assignment to the Mac or Win peer over the
  LAN and don't know whether the WS channel is currently live.

## Core Concepts

Two transports, one mental model — always pick by locality, not preference:

| Transport | Scope | Implementation | Backing store |
|---|---|---|---|
| **Intra-host** | Same machine, cross-process/cross-worktree | `orchestrator/gossip_bus.py` (`GossipBus` class) — Perpetua-Tools | `perpetua_core.db` SQLite, FTS5 keyword search + optional bge-m3 embed |
| **Inter-host (LAN)** | Mac ↔ Win, different machines | `src/orama_system/lan_peer_channel.py` (WS-primary, SSE fallback) + `lan_peer_files.py` (file-drop) — orama-system | WS/SSE live stream, or `~/.openclaw/state/lan_peer/{inbox,outbox}/` markdown/plain-text files when both wires are down |

**Intra-host is the default.** Do not build new infrastructure for
same-machine, cross-worktree, or cross-process coordination — `GossipBus` is
already local-only by design (SQLite file path resolved via
`git rev-parse --git-common-dir`, so every worktree of the same repo shares
one bus with zero new env vars). This was independently re-derived and
validated in the same session by two concurrent agents; see
`docs/LESSONS.md` (lesson `fc6e8293ab26`, Perpetua-Tools).

**Inter-host only when the peer is a different machine.** The LAN peer
channel is a state machine, not a single call:

```
WS_CONNECTING (5s timeout)
  -> WS_CONNECTED                       (heartbeat every 15s)
  -> fail x2 -> SSE_CONNECTING -> SSE_CONNECTED
  -> DISCONNECTED (30s) -> retry WS
```

Two consecutive WS failures demote to SSE before the retry cycle. If both
wires are down, `lan_peer_files.py` / `lan_peer_assign.py` still deliver via
plain file drops to the peer's inbox — no streaming required, at the cost of
latency. Never assume WS is live; the channel abstraction
(`lan_peer_channel.py`) is the only thing that should know which wire is
current.

Peer IP is **never hardcoded** — both transports that need it read
`~/.openclaw/state/last_discovery.json` (`endpoints.mac`/`endpoints.win`),
kept fresh by the `com.orama.network-watch` launchd watcher. See
`CLAUDE-instru.md` INVARIANT on Win LM Studio IP for the same rule applied
elsewhere.

## Instructions

### Intra-host: emit and query

```python
from orchestrator.gossip_bus import GossipBus

bus = GossipBus()
await bus.init_db()
await bus.emit("agent_claim", {"agent_id": "...", "task": "..."})

recent = await bus.tail(limit=20)
hits = await bus.search("heartbeat dead-agent")
```

`heartbeat_monitor.py` and `scripts/agent_coordination.py` already consume
this bus — see the `agent-coordination-heartbeat` skill before building a
parallel liveness mechanism.

### Inter-host: LAN peer

Prefer the channel abstraction over touching WS/SSE directly:

```python
from orama_system.lan_peer_channel import make_envelope, read_discovery_peer_ip
# channel.send(make_envelope("gossip", {...}))  # picks WS/SSE per current state
```

For file-drop handoff (no live wire needed):

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop \
  --file <local-file> --assignee mac|win --topic <topic>
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
```

Full operator playbook: `bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md`.

## Boundaries

### Always Do
- Pick the transport by locality (same machine vs. different host) — never
  route intra-host coordination over the LAN peer channel just because it
  exists.
- Let `lan_peer_channel.py` own WS/SSE/DISCONNECTED state; don't branch on
  transport state in calling code.
- Read peer IPs from `last_discovery.json`; never hardcode or curl-sweep.

### Ask First
- Adding a third transport or bypassing the channel abstraction.
- Lowering LAN peer retry/backoff timings in production.

### Never Do
- Build new same-machine coordination infrastructure when `GossipBus` already
  covers it.
- Delete gossip/heartbeat events to hide dead agents or failed hand-offs.
- Hardcode LAN peer IPs or credentials in payloads.

## Examples

Cross-machine task hand-off when WS is down (falls back to file-drop
automatically once WS/SSE both fail):

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop \
  --file ./hypothesis.md --assignee win --topic autoresearch/hypothesis
```

## References

- Intra-host implementation: `orchestrator/gossip_bus.py` (Perpetua-Tools)
- Inter-host implementation: `src/orama_system/lan_peer_channel.py`,
  `src/orama_system/lan_peer_files.py` (orama-system)
- LAN peer operator playbook: `bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md`
- Guide: `docs/guides/lan-peer-bidirectional-talk-2026-06-28.md`
- Related skill: [`../agent-coordination-heartbeat/SKILL.md`](../agent-coordination-heartbeat/SKILL.md) — heartbeats are emitted onto the intra-host GossipBus
- Related skill: [`../agent-methodology/SKILL.md`](../agent-methodology/SKILL.md) — Context Immersion (stage 1) should check GossipBus/LAN peer state before assuming an agent is silent because it's dead
- Tests: `tests/test_gossip_bus.py` (Perpetua-Tools), `tests/test_lan_peer_channel.py`, `tests/test_lan_peer_files.py`, `tests/test_lan_peer_assign.py` (orama-system)
