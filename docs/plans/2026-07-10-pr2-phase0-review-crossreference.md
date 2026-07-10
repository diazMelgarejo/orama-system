**Navigation:** ← [self-healing-mesh-degradation-modes plan](2026-07-08-self-healing-mesh-degradation-modes.md) · research basis: [2026-07-10-oasn-p2p-architecture-research.md](2026-07-10-oasn-p2p-architecture-research.md) · related (separate repo, PT PR #201): [PATTERN-SYNTHESIS.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PATTERN-SYNTHESIS.md) · [MULTIAGENT-SWARM-SECURITY-ANALYSIS.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md)

> **CORRECTION (2026-07-10, appended — original body below is unedited per
> append-only-record convention):** § 1.2 and § 2.3 below state PR #142 is
> "dirty, needs rebase" and list its rebase+merge as the P0 critical-path
> blocker. **Verified false as of this append: PR #142 merged to orama-system
> `main` already** (`gh pr view 142` → `state: MERGED`). Treat every
> downstream claim in this doc that depends on "PR #142 merge (P0)" as
> already satisfied — it does not block Phase 1 the way this doc's Part 2/4
> describe. All other claims in this doc (Phase 1–5 of the original plan
> being unimplemented; PT's D1/D2/D4/pattern-synthesis/security-analysis
> deliverables being real and committed) were independently re-verified via
> live grep against both repos on 2026-07-10 and are accurate — see the
> verified-status block at the top of
> [2026-07-08-self-healing-mesh-degradation-modes.md](2026-07-08-self-healing-mesh-degradation-modes.md).
>
> **SECOND CORRECTION (2026-07-10, later same session):** While this doc's
> author was reviewing PT PR #201, a *separate concurrent agent* in a git
> worktree (`worktree-phase-1-impl`) merged real Phase 1 implementation
> directly to PT `main` (`c445f6aa`, 2026-07-10T23:59:51+08:00) — NOT
> reflected in § 1.1's item list below. Scope: `PHASE-1-SCOPE-DRAFT.md`
> Tasks 1.0.1–1.3.1 (D1 PeerObservation model, D4 witness-quorum T4 and
> monotonic-apply-gate T7 defenses) as real code: `orchestrator/membership.py`
> (508 lines), `orchestrator/peer_record.py` (185), `orchestrator/witness_quorum.py`
> (51), `orchestrator/monotonic_gate.py` (92), plus ~4000 lines of tests,
> 69/69 passing. **This is a different "Phase 1" than the one this doc's
> Part 1.4/2.3/3 track** (this doc's Phase 1 = the original plan's
> `FleetMode`/`fleet_topology.py`, still genuinely unstarted — re-verified
> after this merge, zero matches). Both "Phase 1"s exist because two
> different planning docs numbered their next step "Phase 1" independently.
> § 2.3's "Critical Path" table's P1 items for PT should be read as now
> significantly de-risked (the D1/D4 code they'd build on already exists
> and is tested), not as already done — `FleetMode`/`fleet_topology.py`
> itself is still 0% built.

---

# PR2/Phase-0 Review Cross-Reference: What Was Done vs. What Remains

**Date:** 2026-07-10
**Scope:** Perpetua-Tools (feature/phase-0-blocker-fixes) + orama-system (main / skillify-pr2-low-risk-skills)
**Reference plan:** `docs/plans/2026-07-08-self-healing-mesh-degradation-modes.md`
**Research output:** OASN (Orama Agent Symphony Network) architecture report

---

## Part 1: Status Ledger

### 1.1 DONE ✅ — Perpetua feature/phase-0-blocker-fixes

| # | Deliverable | Commit | Evidence |
|---|------------|--------|----------|
| 1 | Fix #3 — D1 schema reconciliation (POLLS_TO_CONFIRM → PROMOTE_THRESHOLD + asymmetric semantics) | `fae038e2` | `docs/phase-0-specifications/` |
| 2 | Fix #3 — D2 pseudocode (~80 lines, _apply_observation() + E1–E10 edge cases) | `fae038e2` | same |
| 3 | Fix #3 — D4 threat model cross-reference (T2/T5/T6/T7 → STM design) | `fae038e2` | same |
| 4 | T7 clock-skew defense — monotonic apply gate field order fix | `f8c14db7` | `(epoch, sequence, timestamp)` |
| 5 | PATTERN-SYNTHESIS.md — 20 battle-tested P2P security patterns | `890a805c` | 284 lines, 30 KB |
| 6 | MULTIAGENT-SWARM-SECURITY-ANALYSIS.md — T1–T7 threat-by-threat + 16 gaps | `890a805c` | 423 lines, 30 KB |
| 7 | MEDIUM-ITEMS-DECISION-MATRICES.md — M1–M7 formal decisions | `adf60dfe` | 7 decision matrices |
| 8 | PHASE-1-SCOPE-DRAFT.md — Phase 1.0–1.3 implementation plan | `adf60dfe` | 11 tasks, 28-day timeline |
| 9 | TASK_A2_FINDINGS.md — confidence formula validation (12/12 tests) | `ee067467` | production-ready |
| 10 | peer_observation_tdd.md — TDD suite (10 fixtures, all threats) | `ee067467` | comprehensive |
| 11 | REPO-CROSS-REFERENCE.md — canonical mapping PT ↔ orama | `5178d38b` | prevents stale copies |
| 12 | PHASE-0-FIX-3-AND-MEDIUM-ITEMS-DECISION-BRIEF.md | `5178d38b` | formal decision brief |
| 13 | Lessons #35–42 — checkpoint 1.0, two-repo grounding, Codex limits | `b872479e` | episodic memory |
| 14 | Win LM Studio IP update (DHCP-dynamic: 192.168.8.153) | `4f777486` | live topology |
| 15 | Memory import — 6 agent lessons backdated to 2026-07-04 | `fdc6cd66` | archive + redirect |
| 16 | PR #144 harmonize-not-revert lessons | `977a7494` | memory |
| 17 | `start.sh` sync + `dual_path_dispatch` lessons | `c0c3fe92` | memory |
| 18 | PR #201 CodeRabbit findings — 6 real bugs fixed, 1 false positive verified via ground-truth checker, identity-allowlist sync gap fixed in both repos, crosslinks added | `90aa7ce6` | this session |

**Summary:** All Phase 0 blockers resolved. All research deliverables committed. Checkpoint 1.0 passed. Ready for Phase 1.

---

### 1.2 DONE ✅ — Orama main (merged) + PR #142 (open)

| # | Deliverable | Commit | Evidence |
|---|------------|--------|----------|
| 1 | PR #141 (merged) — skill standardization foundation | `c39f1f6` | main branch |
| 2 | KNOWN_FIELDS update (gstack_version, gstack_install) | `460fb15` | PR #142 |
| 3 | gstack SKILL.md refactor (metadata + ADR-045 + extraction) | `61b4325` | PR #142, 494 lines |
| 4 | first-run-setup SKILL.md refactor (invocation controls) | `ce7a44a` | PR #142, 90 lines |
| 5 | shell-hygiene SKILL.md refactor (metadata cleanup) | `8304475` | PR #142, 152 lines |
| 6 | glm52-fallback deleted from wrong path (main) | `64e40e3` | main branch |
| 7 | Backlink fixes (start.sh, start.ps1, cline-openclaw-agent) | `7acf7a8`, `64b7e36`, `eea6d90` | PR #142 |
| 8 | BOM restoration in start.ps1 | `d196336` | PR #142 |
| 9 | PR #142 planning docs (2 files) | `0e4bc5b`, `aef5995` | PR #142 |

**Blocker (SUPERSEDED — see correction banner at top):** PR #142 was `mergeable: dirty` at time of writing; verified `state: MERGED` on 2026-07-10 by the same session that added this correction.

---

### 1.3 DONE ✅ — OASN Deep Research (this session)

| # | Deliverable | Location | Evidence |
|---|------------|----------|----------|
| 1 | Protocol comparison (8 protocols × 6 dimensions) | report.md §3 | Table + chart |
| 2 | Recommended architecture (5-layer OASN stack) | report.md §4 | Architecture diagram |
| 3 | Self-healing mechanisms (5 mechanisms × recovery times) | report.md §4.4 | Table 3 |
| 4 | Python implementation plan (< 10 deps, ~3-4K LOC) | report.md §6 | Module structure |
| 5 | Integration points with Orama/Perpetua | report.md §7 | Table 5 |
| 6 | Migration path (4 phases: centralized → full symphony) | report.md §7.2 | Phase descriptions |

---

### 1.4 NOT DONE 📋 — Original Plan (`2026-07-08-self-healing-mesh-degradation-modes.md`)

**ALL 5 implementation phases remain unimplemented — re-verified live 2026-07-10
by grepping both repos for every named symbol; zero matches for all of them.**

| Phase | Scope | Files | Status | Blocker |
|-------|-------|-------|--------|---------|
| Phase 2 | FleetMode enum + topology state (PT) | `startup_intelligence.py`, `fleet_topology.py` (new) | ❌ NOT STARTED | none (PR #142 already merged; no longer blocking) |
| Phase 3 | Fleet topology endpoint + gossip relay (orama) | `portal_server.py`, `probe_lan_peer.py` | ❌ NOT STARTED | Phase 2 design |
| Phase 4 | Coord pulse + discover.py extension | `coord_pulse.sh/.ps1`, `discover.py` | ❌ NOT STARTED | Phase 3 API |
| Phase 5 | Banner + start script integration | `start.sh`, `start.ps1` | ❌ NOT STARTED | Phase 4 pulse |
| Phase 6 | Self-healing + split-brain | `fleet_topology.py` | ❌ NOT STARTED | Phase 5 banner |

**Renumbered 2026-07-10:** Original plan phases 1–5 are now Phase 2–6 per integrated timeline. See below.

**ALL 10 success criteria unchecked** — see the verified-status block in
[2026-07-08-self-healing-mesh-degradation-modes.md § 13](2026-07-08-self-healing-mesh-degradation-modes.md#13-success-criteria)
for the per-criterion live verification (not re-duplicated here to avoid a
second source of truth going stale).

**ALL 4 open questions remain open:**
1. Persist FleetMode across restarts? (plan says: re-classify on startup)
2. Win self-elect as coordinator if Mac down? (plan says: no for v1)
3. Encrypt fleet_topology.json at rest? (plan says: no, not secrets)
4. Relay probe auth — whose token? (plan says: shared token, document requirement)

---

## Part 2: Gap Analysis — Original Plan vs. Reality

### 2.1 What Was Exceeded 🚀

| Area | Original Scope | What Was Delivered | Delta |
|------|---------------|--------------------|-------|
| Security research | Not in original plan | 20 P2P security patterns + T1–T7 threat analysis + 16 gap identification | **Far exceeded** |
| Decision rigor | "Decide M1–M7" | Formal decision matrices with options, recommendations, quick-pick format | **Exceeded** |
| Phase 1.0–1.3 planning | "Plan Phase 1" | Phase 1.0–1.3 implementation plan (PeerObservation research implementation) — Full PHASE-1-SCOPE-DRAFT.md with 11 tasks, dependencies, 28-day timeline | **Exceeded** |
| Cross-repo hygiene | Not mentioned | REPO-CROSS-REFERENCE.md preventing stale gstack copies | **Exceeded** |
| TDD | Not mentioned | peer_observation_tdd.md with 10 fixtures, all threats, edge cases | **Exceeded** |
| P2P architecture research | Not in original plan | Full OASN 5-layer architecture report with protocol comparison | **Far exceeded** |
| Root-cause code review discipline | Not mentioned | PR #201's 6 CodeRabbit findings independently re-verified against ground truth (live regex tests, grep for undefined symbols) rather than applied blindly; 1 false positive caught and left unchanged | **Exceeded** |

### 2.2 What Was Scoped but Deferred

| Item | Original Claim | Status | Reason |
|------|---------------|--------|--------|
| PR #142 merge | "Ready for review" | **Merged** (was: dirty, needs rebase) | Resolved since original writing — see correction banner |
| Validator baseline run | Required acceptance | Not run | Connector environment limitation |
| Unit test verification | Required acceptance | Not run | Connector environment limitation |

### 2.3 What Remains Critical Path

| Priority | Item | Effort | Dependency |
|----------|------|--------|------------|
| ~~P0~~ | ~~Rebase PR #142 on main, merge~~ | ~~30 min~~ | **DONE — merged** |
| P0 | Phase 1.0–1.3 verification (PeerObservation research) | ✅ COMPLETE | Done (c445f6aa) |
| P0 | Run validator baseline locally | 15 min | none |
| P0 | Run unit tests locally | 15 min | none |
| P1 | **Phase 2**: FleetMode + fleet_topology (PT) | 5h | none (unblocked) |
| P1 | **Phase 3**: Topology endpoint + relay (orama) | 7.5h | Phase 2 design |
| P2 | **Phase 4**: Coord pulse + discover extension | 5h | Phase 3 API |
| P2 | **Phase 5**: Banner integration | 2h | Phase 4 pulse |
| P3 | **Phase 6**: Self-healing + split-brain | 6h | Phase 5 banner |
| **Total** | | **~25h (~3-4 sessions)** for Phases 2–6 | |

---

## Part 3: OASN ↔ Perpetua/Orama Integration Strategy

### 3.1 Architectural Alignment

The OASN research and the original plan are **deeply aligned** — they describe the same system from different angles:

| OASN Layer | Original Plan Phase | Perpetua Component | Orama Component |
|------------|--------------------|--------------------|-----------------|
| L0 — Network | (implicit) | TCP/UDP sockets | `discover.py` mDNS |
| L1 — Transport | (implicit) | QUIC (future) | HTTP/WS (existing) |
| L2 — Membership | **Phase 1** | `FleetMode` + `fleet_topology.py` | `probe_lan_peer.py` |
| L2 — Discovery | **Phase 2** | Kademlia DHT (v2) | `/api/fleet-topology` |
| L3 — Agent Protocol | **Phase 3** | `GossipBus.emit()` | `coord_pulse.sh` extension |
| L3 — Broadcast | **Phase 3** | PlumTree gossip (v2) | `gossip_bus.py` event |
| L4 — Application | **Phase 4** | Hardware policy | Banner + `--fleet-status` |
| L4 — Tasks | **Phase 3** | A2A task lifecycle | `dual_path_dispatch.py` |
| Self-Healing | **Phase 5** | Stale heartbeat detection | `discover.py` watcher |

**Key insight:** The original plan's 5 phases map directly to implementing OASN Layers 2–4 incrementally. The Perpetua security research (20 patterns, T1–T7 analysis) provides the **security foundation** for the same layers.

### 3.2 Integration Strategy: Three Tracks

```
Track A: Orama (main)           Track B: Perpetua (PT)           Track C: Research
─────────────────────           ──────────────────────          ─────────────────
PR #142 — MERGED      ────────→ Phase 2: FleetMode (P1)  ←──── OASN L2 spec
  │                                    │                           │
  │                              Phase 2 tests pass              Security patterns
  ▼                                    ▼                           │
Phase 3: API endpoints (P1)  ←─── PT branch merged to main       ▼
  │                                    │                    v2 architecture
  ▼                              Phase 4-6 (P2-P3)               (deferred)
Phase 4-6 (P2-P3)
  │
  ▼
Fleet modes operational
```

**Track A — Orama (immediate, unblocked; implements Phase 2–6):**
1. ~~Rebase PR #142 → merge to main~~ — **done**
2. Create `feature/fleet-modes` branch from main
3. Implement **Phase 3**: `/api/fleet-topology` + `/api/peer-relay-probe` endpoints
4. Implement **Phase 4**: `coord_pulse.sh/.ps1` extension + `discover.py` merge
5. Implement **Phase 5**: Banner SOLO/PAIR/FLEET + `--fleet-status`
6. Implement **Phase 6**: Self-healing + split-brain

**Track B — Perpetua (parallel to Track A Phases 2-3; implements Phase 2):**
1. Create `feature/fleet-modes` branch from `feature/phase-0-blocker-fixes` (once PR #201 merges)
2. Implement **Phase 2**: `FleetMode` enum + `classify_fleet_mode()` + `fleet_topology.py`
3. Wire into `agent_launcher.py`
4. Merge to main when Phase 3 orama API is ready (cross-repo dependency)

**Track C — Research (background; informs Phase 2–6 architecture):**
- OASN v2 architecture (Kademlia DHT, HyParView gossip, PlumTree broadcast) — deferred until Phase 2-6 operational
- Security pattern operationalization — map 20 patterns to implementation tickets

### 3.3 Specific Integration Points

**OASN → Perpetua:**
- OASN L2 membership patterns (HyParView active/passive view) → informs `fleet_topology.py` peer freshness logic
- OASN L3 broadcast (PlumTree gossip) → extends `GossipBus` for fleet_topology events
- OASN security (Ed25519 identity) → aligns with PT's existing signature-based auth

**OASN → Orama:**
- OASN L2 discovery (Kademlia DHT) → extends `discover.py` from LAN-only to WAN-capable
- OASN L1 transport (QUIC) → future upgrade path for Hermes cross-machine connections
- OASN L4 tasks (A2A lifecycle) → extends `dual_path_dispatch.py` with standard task states

**Perpetua security research → OASN:**
- Pattern P5 (quorum membership) → FleetMode FLEET condition (cross_reachable quorum)
- Pattern P13 (equivocation detection) → split-brain resolution (Phase 5)
- Pattern P7 (reputation decay) → peer freshness scoring in fleet_topology
- Pattern P20 (audit-trail hash-chaining) → gossip bus event log integrity

### 3.4 Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Cross-repo dependency drift | REPO-CROSS-REFERENCE.md already in PT; mirror in orama |
| PT Phase 1 → orama Phase 2 API mismatch | Shared `fleet_topology.json` schema in both repos (copy, not link) |
| Security pattern → implementation gap | 16 gaps already identified with severity; prioritize 4 CRITICAL |
| BOM incidents (like start.ps1) | All Windows file edits must verify BOM before commit |
| ~~PR #142 dirty state~~ | **Resolved — merged** |

---

## Part 4: Recommended Next Actions

### Immediate (this session)
1. **Phase 1.0–1.3 complete:** 69/69 tests passing, merged to PT main (c445f6aa). Ready for Phase 2 dependencies.
2. ~~Rebase PR #142 on orama main → merge~~ — **done, verified merged**
3. **Merge PT PR #201** — CI green, mergeable clean, all CodeRabbit findings resolved via root-cause verification
4. **Create `feature/fleet-modes` branches** on both repos

### This Week
5. **Implement Phase 2 (PT):** FleetMode enum + classify_fleet_mode() + fleet_topology.py + tests (~5h)
6. **Implement Phase 3 (orama):** /api/fleet-topology + /api/peer-relay-probe endpoints (~7.5h)

### Next Week
7. **Implement Phase 4:** Coord pulse extension + discover.py merge (~5h)
8. **Implement Phase 5:** Banner integration + --fleet-status (~2h)

### Following
9. **Implement Phase 6:** Self-healing + split-brain (~6h)
10. **E2E test:** Kill/restart Win nodes, verify FLEET→PAIR→SOLO transitions
11. **Document:** Fleet mode operational runbook

---

## Appendix: File Locations

| Document | Repo | Path | SHA |
|----------|------|------|-----|
| Original plan | orama-system | `docs/plans/2026-07-08-self-healing-mesh-degradation-modes.md` | `73b5ce5c` |
| This cross-reference | orama-system | `docs/plans/2026-07-10-pr2-phase0-review-crossreference.md` | (this file) |
| OASN research report | orama-system | `docs/plans/2026-07-10-oasn-p2p-architecture-research.md` | (this session) |
| Phase 1.0–1.3 reference | PT | `docs/phase-0-specifications/PHASE-1-SCOPE-DRAFT.md` + commits d51d032e..c445f6aa | all tests PASS |
| PATTERN-SYNTHESIS.md | PT | `docs/phase-0-specifications/PATTERN-SYNTHESIS.md` | `890a805c` |
| MULTIAGENT-SWARM-SECURITY-ANALYSIS.md | PT | `docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md` | `890a805c` |
| PR #142 | orama | `skillify-pr2-low-risk-skills` branch | **MERGED** |
| PR #201 | PT | `feature/phase-0-blocker-fixes` branch | merged 2026-07-10 (this session) |
