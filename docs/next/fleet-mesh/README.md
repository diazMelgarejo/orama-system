# Fleet Mesh — Active Plans

Status: active / unfinished planning index.  
Owner: `orama-system` with cross-repo dependencies in `Perpetua-Tools`.

This folder is the canonical launchpad for the SOLO / PAIR / FLEET → Phase 7–10+ planning lineage. It does not supersede the original source documents; it indexes them and preserves the avalanche chain so the next implementation agent starts from the correct root.

## Mother plan

| Role | Document | Why it matters |
|---|---|---|
| Root / mother plan | [`2026-07-08-self-healing-mesh-degradation-modes.md`](2026-07-08-self-healing-mesh-degradation-modes.md) | First explicit SOLO / PAIR / FLEET self-healing mesh plan. Introduced FleetMode, topology state, gossip relay, fleet endpoints, coord pulse extension, banner/status integration, and split-brain prevention. |

The mother plan is active, not archive. Later documents should cite it as the source of the avalanche.

## Active Orama documents

| Phase / branch | Document | Status | Notes |
|---|---|---:|---|
| Timeline / handoff | [`2026-07-10-phase-integration-map.md`](2026-07-10-phase-integration-map.md) | active reference | Connects PT Phase 1.0–1.3, PT Phase 2 FleetMode, Orama Phase 3–6, and later Phase 7–10+ work. |
| Research input | [`2026-07-10-oasn-p2p-architecture-research.md`](2026-07-10-oasn-p2p-architecture-research.md) | active research | P2P/membership/gossip research input. Treat as research, not implementation spec. |
| Phase 7 / G7 | [`G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`](G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) | active plan | Portal Notification Hub / async notification MVP analysis. |
| Phase 7 / G7 next steps | [`2026-07-14-g7-async-notifications-next-steps.md`](2026-07-14-g7-async-notifications-next-steps.md) | active checklist | Open G7 implementation checklist and review notes. |
| Phase 10+ companion | [`43-gossipbus-mesh-transport.md`](../../v2/43-gossipbus-mesh-transport.md) | active future mesh design | Interest-filtered, redacted, append-only GossipBus/GossipMesh deltas. This is the likely Phase 10+ Byzantine/witness/gossip direction. |

## Cross-repo active companions

| Repo | Document | Relationship |
|---|---|---|
| Perpetua-Tools | `docs/PHASE-2-SPEC.md` | PT concrete Phase 2 implementation/spec for FleetMode and topology state management. |
| Perpetua-Tools | `orchestrator/fleet_topology.py` | PT runtime implementation of FleetMode classifier/topology state, when present on the current PT main lineage. |
| Perpetua-Tools | `docs/phase-0-specifications/PATTERN-SYNTHESIS.md` | Security and pattern synthesis feeding gossip, split-brain, and witness recovery. |
| Perpetua-Tools | `docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md` | Threat-model companion for Phase 10+ Byzantine/witness direction. |

## System Navigation Graph

This is the fleet-mesh navigation hub, not a replacement architecture. Follow
the authority order below when documents disagree. Every listed node has a
direct edge to its governing context so an agent can reach the relevant active,
historical, security, or runtime evidence in a small number of hops.

1. [`docs/v2/`](../../v2/) is authoritative over every planning document here.
2. [`43-gossipbus-mesh-transport.md`](../../v2/43-gossipbus-mesh-transport.md)
   defines the later mesh transport direction; do not treat it as G7 MVP code.
3. [`39-maestro-owasp-genai-reference.md`](../../v2/39-maestro-owasp-genai-reference.md)
   is the canonical security-verification hub; use it before changing a
   security-sensitive notification, mesh, or control-plane edge.
4. The mother plan, integration map, and OASN research in this directory explain
   the active SOLO / PAIR / FLEET lineage and its technical inputs.
5. The G7 analysis and next-steps checklist in this directory define the
   Phase-7-adjacent portal-notification problem. Their production research and
   TDD handoff are linked below.
6. [`../../archive/fleet-mesh/README.md`](../../archive/fleet-mesh/README.md)
   contains completed Phase 5-6 evidence and the historical cross-reference;
   it supplies provenance, not an implementation starting point.

| Node | Direct edge | What an agent should take from it |
|---|---|---|
| Canonical product/security authority | [`docs/v2/`](../../v2/), [`39`](../../v2/39-maestro-owasp-genai-reference.md) | Non-negotiable architecture and security constraints. |
| Future mesh contract | [`43`](../../v2/43-gossipbus-mesh-transport.md) | GossipBus/GossipMesh compatibility direction, deferred from G7 MVP. |
| Root plan | [`2026-07-08 self-healing mesh`](2026-07-08-self-healing-mesh-degradation-modes.md) | Why SOLO / PAIR / FLEET, topology state, relay, and split-brain work exist. |
| Integrated timeline | [`2026-07-10 phase integration`](2026-07-10-phase-integration-map.md) | Maps PT Phase 1.0-1.3, FleetMode, Orama Phase 3-6, and the Phase 7-10+ continuation. |
| Research input | [`2026-07-10 OASN`](2026-07-10-oasn-p2p-architecture-research.md) | P2P/membership/gossip options; research only, never an unreviewed implementation mandate. |
| G7 product analysis | [`G7 async notifications`](G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) | Portal Notification Hub scope and the initial implementation checklist. |
| G7 production evidence | [SSE production patterns](../../superpowers/references/2026-07-14-g7-sse-production-patterns.md) | Bounded Firecrawl research, browser-auth constraints, overflow, envelope, and replay decisions. |
| G7 executable handoff | [Authenticated SSE MVP plan](../../superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md) | File-by-file TDD implementation sequence; subordinate to `docs/v2/`. |
| PT runtime companion | [PT Phase 2 spec](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/PHASE-2-SPEC.md), [fleet topology](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/fleet_topology.py) | Runtime/state ownership for FleetMode and topology, when present in the current PT lineage. |
| PT security companion | [pattern synthesis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PATTERN-SYNTHESIS.md), [swarm security analysis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md) | Threat-model and pattern evidence for later mesh hardening; leave their claims intact unless separately tasked. |
| Completed evidence | [`fleet-mesh archive`](../../archive/fleet-mesh/README.md) | Phase 5-6 report and historical review ledger, preserved for provenance. |

### Shortest Useful Paths

```text
docs/v2 security and mesh authority
  -> fleet-mesh active index
  -> mother plan / integrated timeline / OASN research
  -> G7 analysis
  -> SSE production research
  -> authenticated SSE implementation plan
  -> feature-flagged portal-local implementation

completed Phase 5-6 report + historical ledger
  -> archive index
  -> active index
  -> Phase 7-10+ roadmap and current G7 work
```

The first path is intentionally directional: an MVP implementation must read
back toward `docs/v2` and the active root before it changes code. The second
path prevents a completed report from being mistaken for the current root plan.

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
