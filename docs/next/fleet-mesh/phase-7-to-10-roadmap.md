# Fleet Mesh Phase 7–10+ Roadmap

Status: active roadmap extracted from the Phase 6 completed-report clue.  
Root plan: [`2026-07-08-self-healing-mesh-degradation-modes.md`](2026-07-08-self-healing-mesh-degradation-modes.md)
Index: [`README.md`](README.md)

## Source clue

`PHASE-6-IMPLEMENTATION.md` closes Phase 5–6 and leaves these next steps:

1. **Phase 7 (Quorum Consensus):** Extend split-brain resolver for 3+ nodes.
2. **Phase 8 (Recovery Orchestration):** Implement recovery notifications and thresholds.
3. **Phase 9 (Topology Learning):** Adaptive grace periods based on network jitter.
4. **Phase 10+ (Byzantine Resilience):** Signature verification and witness-based recovery.

That report is archived as a completed milestone. This roadmap is the active continuation.

## Phase 7 — Quorum Consensus / G7 notifications

Current active documents:

- [`G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`](G7-ASYNC-NOTIFICATIONS-ANALYSIS.md)
- [`2026-07-14-g7-async-notifications-next-steps.md`](2026-07-14-g7-async-notifications-next-steps.md)

Working hypothesis:

- G7 is the operator/control-plane awareness layer that becomes necessary once split-brain/stale/recovered events exist.
- The MVP should be portal-local, feature-flagged, auth-gated, and event-envelope compatible with future GossipBus/GossipMesh v2.1.

Acceptance sketch:

- `PORTAL_NOTIFICATIONS=1` enables `/api/notifications/stream`.
- Unauthenticated clients are rejected.
- A topology/agent/job event reaches an SSE client within 2 seconds.
- Notification payloads reuse existing redaction helpers.
- The route remains disabled by default.

## Phase 8 — Recovery Orchestration

Working hypothesis:

- Once notifications exist, recovery should become policy-driven rather than ad hoc.
- Recovery thresholds should distinguish transient stale peer, repeated relay failure, confirmed split brain, and operator-forced isolation.

Inputs:

- Mother plan sections on self-healing and queue fallback.
- G7 notification event taxonomy.
- Perpetua-Tools heartbeat/liveness work.

Deliverables to design:

- Recovery threshold table.
- Operator notification severity map.
- Coord-pulse / portal action routing.
- “Do nothing / notify / degrade / isolate / recover” state machine.

## Phase 9 — Topology Learning

Working hypothesis:

- Fixed grace periods will be noisy on unstable LAN segments.
- Peer-specific jitter/reliability observations should tune stale and recovery windows.

Inputs:

- Fleet topology state.
- Coord-pulse heartbeat history.
- OASN/P2P research.

Deliverables to design:

- Peer reliability score.
- Adaptive grace period bounds.
- Learning reset rules after topology changes.
- Anti-overfitting guardrails for short samples.

## Phase 10+ — Byzantine Resilience / GossipMesh / witness recovery

Current companion:

- [`../../v2/43-gossipbus-mesh-transport.md`](../../v2/43-gossipbus-mesh-transport.md)
- Perpetua-Tools swarm security and pattern-synthesis docs.

Working hypothesis:

- Fleet mesh cannot trust every observation equally once it spans multiple nodes and agents.
- Future transport should be redacted, append-only, signed where possible, and witness-aware.

Deliverables to design:

- Signature verification boundary.
- Witness evidence schema.
- Equivocation handling policy.
- Interest-filtered GossipBus deltas.
- Recovery from conflicting peer reports.

## Non-goals for this roadmap

- Do not reimplement PT FleetMode in Orama without checking current PT main first.
- Do not treat the OASN research report as approved spec.
- Do not archive the mother plan until Phase 7–10+ has a newer approved root.
- Do not add runtime endpoints from this roadmap without a separate implementation PR/plan.
