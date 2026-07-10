# Phase Integration Map: 1.0–1.3 (Data Integrity) + 2–6 (Mesh Topology)

**Navigation:**  
← [Self-Healing Mesh Plan (Phases 2–6)](2026-07-08-self-healing-mesh-degradation-modes.md) · [Cross-Reference (Status Ledger)](2026-07-10-pr2-phase0-review-crossreference.md) · PT Research: [PHASE-1-SCOPE-DRAFT.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PHASE-1-SCOPE-DRAFT.md) · [D1 Spec](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/DELIVERABLE-1-PEER-OBSERVATION-MODEL.md) · [Pattern Synthesis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PATTERN-SYNTHESIS.md) · [Security Analysis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md)

**Date:** 2026-07-11  
**Status:** Living document — unified timeline for Phase 1–6 implementation  
**Scope:** Perpetua-Tools (PT, Layer 2) + orama-system (Layer 3)

---

## Quick Reference: Phase Timeline

| Phase | Layer | Component | Scope | Status | Est. Effort |
|---|---|---|---|---|---|
| 1.0 | 2 (PT) | PeerObservation Schema | D1 schema + T1–T7 threat alignment | ✅ DONE | - |
| 1.1 | 2 (PT) | Integration Loop | Wire confidence scoring into PeerRecord | ✅ DONE | - |
| 1.2 | 2 (PT) | Witness Quorum Gate | T4 Sybil defense dual-gate | ✅ DONE | - |
| 1.3.1 | 2 (PT) | Monotonic Apply Gate | T7 observation ordering + causality | ✅ DONE | - |
| 1.3.2 | 2 (PT) | Reorder Buffer | Buffering + watermark per D1 § 2.4 | 📋 PENDING | 2h |
| 2 | 2+3 (PT+orama) | FleetMode Classifier | SOLO/PAIR/FLEET enum + topology.json | 📋 PENDING | 5h |
| 3 | 3 (orama) | Fleet Topology API | `/api/fleet-topology` + `/api/peer-relay-probe` | 📋 PENDING | 7.5h |
| 4 | 3 (orama) | Coord Pulse Extension | Query peer topology, emit gossip events | 📋 PENDING | 5h |
| 5 | 3 (orama) | Banner Integration | SOLO/PAIR/FLEET display + --fleet-status | 📋 PENDING | 2h |
| 6 | 2+3 (PT+orama) | Self-Healing Mesh | Stale detection, recovery, split-brain | 📋 PENDING | 6h |

**Total Phase 1.0–1.3:** ~45 test cases, 69/69 PASSING ✅  
**Total Phase 2–6:** ~25 hours (~3-4 sessions)  
**Total: ~70 hours for complete fleet mesh**

---

## Dependency Graph

```
Phase 1.0–1.3 (COMPLETE) ✅
    ↓
    ├→ Phase 2 (FleetMode, PT)
    │     ↓
    ├→ Phase 3 (API, orama) [parallel to Phase 2]
    │     ↓
    └→ Phase 4 (Coord pulse, orama)
          ↓
          Phase 5 (Banner, both repos)
          ↓
          Phase 6 (Self-healing, both repos)
```

**Critical Path:** 1.0–1.3 ✅ → 2 || 3 → 4 → 5 → 6  
**Blockers:** Phase 2 design unblocks Phase 3; Phase 3 API unblocks Phase 4

---

## Cross-Repo Handoff Points

### PT → orama (Phase 2 completion)
- **Deliverable:** FleetMode enum definition + classify_fleet_mode() pure function spec
- **File:** Perpetua-Tools/docs/PHASE-2-SPEC.md (to be created)
- **Orama integration:** Phase 3 API takes FleetMode spec as interface contract

### orama → PT (Phase 3 completion)
- **Deliverable:** `/api/fleet-topology` + `/api/peer-relay-probe` endpoint OpenAPI schema
- **File:** orama-system/docs/FLEET-TOPOLOGY-API.md (to be created)
- **PT integration:** Phase 2 controller can now dispatch to live endpoints

### Both → integration test (Phase 4 completion)
- **Deliverable:** Merged feature/fleet-modes branches on both repos
- **Trigger:** Phase 4's coord_pulse integration passes end-to-end tests

---

## Research Foundation

### Phase 1.0–1.3 backed by:
- **D1 Spec** (PeerObservation schema): Perpetua-Tools/docs/phase-0-specifications/DELIVERABLE-1-PEER-OBSERVATION-MODEL.md
- **Pattern Synthesis** (20 P2P patterns): Perpetua-Tools/docs/phase-0-specifications/PATTERN-SYNTHESIS.md
- **Threat Analysis** (T1–T7 defenses): Perpetua-Tools/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md
- **Implementer guide** (TDD specs): Perpetua-Tools/docs/phase-0-specifications/peer_observation_tdd.md

### Phase 2–6 backed by:
- **Self-Healing Mesh Plan** (architecture): orama-system/docs/plans/2026-07-08-self-healing-mesh-degradation-modes.md (§ 7–11)
- **OASN Research** (5-layer P2P stack): orama-system/docs/plans/2026-07-10-oasn-p2p-architecture-research.md
- **Cross-Reference** (integration strategy): orama-system/docs/plans/2026-07-10-pr2-phase0-review-crossreference.md (§ 3)

---

## Success Criteria (Unified)

### Phase 1.0–1.3 (COMPLETE ✅)
- [x] PeerObservation schema frozen, immutable, T1–T7 threat mitigations in code
- [x] Confidence formula multiplicative gate per D1 spec (Decimal ROUND_HALF_UP)
- [x] Witness quorum dual-gate validation (≥2 observer_id AND ≥2 provenance)
- [x] Monotonic apply gate (epoch, sequence, timestamp) with ±30s skew tolerance
- [x] All 69 tests passing across 4 checkpoints

### Phase 2 (FleetMode, PENDING)
- [ ] classify_fleet_mode() pure function, 3 modes + edge cases tested
- [ ] fleet_topology.json schema + read/write helpers
- [ ] Integration into agent_launcher.py

### Phase 3 (API, PENDING)
- [ ] GET /api/fleet-topology returns correct JSON for all 3 modes
- [ ] POST /api/peer-relay-probe returns relayed probe result
- [ ] Auth rejection (401 without token, 200 with valid)
- [ ] Gossip relay round-trip tested

### Phases 4–6 (PENDING)
- [ ] Coord pulse queries peer topology + merges local state
- [ ] Banner shows SOLO/PAIR/FLEET with peer count
- [ ] Stale heartbeat detection + auto-recovery
- [ ] Split-brain consensus: direct > relayed > stale

---

## Session Record

| Session | Date | Agent | Work | Status |
|---|---|---|---|---|
| Phase 1 Implementation | 2026-07-10 | 11 parallel agents | 1.0–1.3 complete | ✅ MERGED c445f6aa |
| Phase 1-6 Harmonization | 2026-07-11 | 3 parallel agents | Rename phases, draft integration | 📋 IN PROGRESS |
| Phase 2 FleetMode | TBD | PT implementer | ClassifyFleetMode + tests | 📋 PENDING |
| Phase 3 API | TBD | orama implementer | Endpoints + integration tests | 📋 PENDING |
| Phase 4–6 | TBD | Both repos | Coord pulse, banner, self-healing | 📋 PENDING |

---

## Open Questions (from original plan)

1. Persist FleetMode across restarts? **Recommendation:** re-classify on startup (idempotent, <1s)
2. Win self-elect as coordinator if Mac down? **Recommendation:** no for v1
3. Encrypt fleet_topology.json? **Recommendation:** no (consistent with last_discovery.json)
4. Relay probe auth — whose token? **Recommendation:** shared token, document requirement

---

## Navigation

- **Original self-healing plan:** [2026-07-08-self-healing-mesh-degradation-modes.md](2026-07-08-self-healing-mesh-degradation-modes.md) (now Phases 2–6)
- **Cross-reference:** [2026-07-10-pr2-phase0-review-crossreference.md](2026-07-10-pr2-phase0-review-crossreference.md)
- **OASN research:** [2026-07-10-oasn-p2p-architecture-research.md](2026-07-10-oasn-p2p-architecture-research.md)
- **Phase 1.0–1.3 scope:** [Perpetua-Tools/docs/phase-0-specifications/PHASE-1-SCOPE-DRAFT.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PHASE-1-SCOPE-DRAFT.md)

---

**Living Document Owner:** orama-system/Phase Integration Task Force  
**Last Updated:** 2026-07-11  
**Next Review:** After Phase 2 design completion (TBD)
