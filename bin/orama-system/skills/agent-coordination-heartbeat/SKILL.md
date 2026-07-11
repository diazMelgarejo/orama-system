---
name: agent-coordination-heartbeat
description: >-
  Operate the agent-coordination heartbeat monitor for multi-agent liveness detection.
  Activates for: heartbeat monitoring, agent liveness, dead agent detection,
  cleanup stale claims, heartbeat register/list/check/dashboard/pulse/kill/timeline,
  agent_coordination.py heartbeat, gossip_bus heartbeat events.
version: 1.0.0.0
license: Apache 2.0
compatibility: python>=3.9, orama-system, perpetua-tools
allowed-tools: bash, file-operations
parent_skill: orama-system
triggers:
  - heartbeat monitor
  - agent liveness
  - dead agent cleanup
  - heartbeat dashboard
  - agent coordination heartbeat
  - cleanup stale claims
  - heartbeat pulse
  - heartbeat kill
author: Kimi Agent <kimi-agent@kimi.ai>
co_author: Cloud Kimi Agent <cloud-kimi-agent@kimi.ai>
---

# Agent Coordination Heartbeat Monitor

## Purpose

Track liveness of distributed agents via heartbeat events and automatically release stale claims from dead agents.

## When to Use

- An agent has not checked in and may be hung or dead.
- You need to list, check, pulse, or kill an agent through `scripts/agent_coordination.py heartbeat ...`.
- You need to auto-release claims held by agents that have been dead for 30+ minutes.

## Core Concepts

Liveness states are defined in `orchestrator/heartbeat_monitor.py`:

| State | Time since last activity | Meaning |
|-------|--------------------------|---------|
| **ACTIVE** | < 60 s | Agent is actively working |
| **IDLE** | 60-300 s | Registered but idle |
| **STALLED** | 300-1800 s | Likely hung; review needed |
| **DEAD** | > 1800 s | Presumed dead; auto-cleanup triggers |

## Instructions

1. **Register an agent**
   ```bash
   python3 scripts/agent_coordination.py register <agent_id> <type> <model> <notes>
   ```

2. **Emit periodic heartbeats**
   ```bash
   python3 scripts/agent_coordination.py heartbeat pulse <agent_id>
   ```

3. **Inspect health**
   ```bash
   python3 scripts/agent_coordination.py heartbeat list
   python3 scripts/agent_coordination.py heartbeat check <agent_id>
   python3 scripts/agent_coordination.py heartbeat dashboard
   ```

4. **Recover or terminate**
   ```bash
   python3 scripts/agent_coordination.py heartbeat pulse <agent_id>      # mark alive
   python3 scripts/agent_coordination.py heartbeat kill <agent_id> --reason "..."
   ```

5. **Auto-cleanup**
   Call `cleanup_stale_claims(bus)` or rely on the dashboard path to release claims from DEAD agents.

## Boundaries

### Always Do
- Verify liveness before treating an agent as dead.
- Emit release events when auto-cleaning claims.
- Log the reason when force-killing an agent.

### Ask First
- Lowering the 30-minute DEAD threshold in production.
- Killing an agent that still has in-progress work you cannot verify.

### Never Do
- Delete heartbeat events from the GossipBus to hide dead agents.
- Pulse a heartbeat for an agent you do not control.
- Hardcode agent credentials or secrets in heartbeat payloads.

## Examples

Check all agents:
```bash
python3 scripts/agent_coordination.py heartbeat dashboard
```

Programmatic cleanup:
```python
from orchestrator.heartbeat_monitor import cleanup_stale_claims
from orchestrator.gossip_bus import GossipBus

bus = GossipBus()
released = await cleanup_stale_claims(bus)
print("Released:", released)
```

## References

- Implementation: `orchestrator/heartbeat_monitor.py`
- User guide: `docs/heartbeat-monitoring.md`
- Tests: `tests/test_agent_coordination_heartbeat.py`
