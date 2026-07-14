# Fleet Mesh — Active Plans

Status: active / unfinished planning index.  
Owner: `orama-system` with cross-repo dependencies in `Perpetua-Tools`.

This folder is the canonical launchpad for the SOLO / PAIR / FLEET → Phase 7–10+ planning lineage. It does not supersede the original source documents; it indexes them and preserves the avalanche chain so the next implementation agent starts from the correct root.

## Mother plan

| Role | Document | Why it matters |
|---|---|---|
| Root / mother plan | [`../plans/2026-07-08-self-healing-mesh-degradation-modes.md`](../plans/2026-07-08-self-healing-mesh-degradation-modes.md) | First explicit SOLO / PAIR / FLEET self-healing mesh plan. Introduced FleetMode, topology state, gossip relay, fleet endpoints, coord pulse extension, banner/status integration, and split-brain prevention. |

The mother plan is active, not archive. Later documents should cite it as the source of the avalanche.

## Active Orama documents

| Phase / branch | Document | Status | Notes |
|---|---|---:|---|
| Timeline / handoff | [`../plans/2026-07-10-phase-integration-map.md`](../plans/2026-07-10-phase-integration-map.md) | active reference | Connects PT Phase 1.0–1.3, PT Phase 2 FleetMode, Orama Phase 3–6, and later Phase 7–10+ work. |
| Research input | [`../plans/2026-07-10-oasn-p2p-architecture-research.md`](../plans/2026-07-10-oasn-p2p-architecture-research.md) | active research | P2P/membership/gossip research input. Treat as research, not implementation spec. |
| Phase 7 / G7 | [`../G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`](../G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) | active plan | Portal Notification Hub / async notification MVP analysis. |
| Phase 7 / G7 next steps | [`../plans/2026-07-14-g7-async-notifications-next-steps.md`](../plans/2026-07-14-g7-async-notifications-next-steps.md) | active checklist | Open G7 implementation checklist and review notes. |
| Phase 10+ companion | [`../v2/43-gossipbus-mesh-transport.md`](../v2/43-gossipbus-mesh-transport.md) | active future mesh design | Interest-filtered, redacted, append-only GossipBus/GossipMesh deltas. This is the likely Phase 10+ Byzantine/witness/gossip direction. |

## Cross-repo active companions

| Repo | Document | Relationship |
|---|---|---|
| Perpetua-Tools | `docs/PHASE-2-SPEC.md` | PT concrete Phase 2 implementation/spec for FleetMode and topology state management. |
| Perpetua-Tools | `orchestrator/fleet_topology.py` | PT runtime implementation of FleetMode classifier/topology state, when present on the current PT main lineage. |
| Perpetua-Tools | `docs/phase-0-specifications/PATTERN-SYNTHESIS.md` | Security and pattern synthesis feeding gossip, split-brain, and witness recovery. |
| Perpetua-Tools | `docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md` | Threat-model companion for Phase 10+ Byzantine/witness direction. |

## Avalanche chain

```text
SOLO / PAIR / FLEET mother plan
  ↓
PT Phase 2 FleetMode + fleet_topology.py
  ↓
Orama Phase Integration Map
  ↓
Orama Phase 3/4/5/6 implementation
  ↓
PHASE-6-IMPLEMENTATION.md completed report
  ↓
Phase 7–10+ next-step clue
  ├─ Phase 7 / G7 async notifications
  ├─ Phase 8 recovery orchestration
  ├─ Phase 9 topology learning
  └─ Phase 10+ Byzantine / GossipMesh / witness recovery
```

## Phase 7–10+ roadmap skeleton

| Phase | Working title | Current home | Next action |
|---|---|---|---|
| 7 | Quorum Consensus / G7 Async Notifications | `G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` + next-steps checklist | Build feature-flagged Portal Notification Hub MVP; keep event envelope v2.1-compatible. |
| 8 | Recovery Orchestration | Mother plan + Phase 6 report next-step clue | Define notification thresholds and recovery escalation policy after G7. |
| 9 | Topology Learning | Mother plan + OASN research | Add adaptive grace periods based on observed network jitter and peer reliability. |
| 10+ | Byzantine Resilience / GossipMesh / witness recovery | `docs/v2/43-gossipbus-mesh-transport.md` + PT swarm security docs | Add signatures, witness recovery, anti-equivocation, and redacted mesh propagation. |

## Housekeeping rule

- Keep unfinished plans here under `docs/next/fleet-mesh/` by index or by `git mv` once a local checkout is available.
- Move completed reports to `docs/archive/fleet-mesh/`.
- Never archive the mother plan until Phase 7–10+ have a newer approved root plan.
- When local git access is available, run actual `git mv` for the documents listed here so GitHub rename tracking is preserved cleanly.
