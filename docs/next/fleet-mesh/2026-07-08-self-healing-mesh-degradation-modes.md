# Plan: Self-Healing Mesh with SOLO / PAIR / FLEET Degradation Modes

**Date:** 2026-07-08
**Status:** Draft — pending review
**Owner:** orama-system (Layer 3) + Perpetua-Tools (Layer 2)

> **Phase Numbering (2026-07-10 Harmonization):** This plan's 6 phases are numbered Phase 2–6 when integrated with parallel Phase 1.0–1.3 research implementation. See [2026-07-10-pr2-phase0-review-crossreference.md](../../archive/fleet-mesh/2026-07-10-pr2-phase0-review-crossreference.md) for integrated timeline.
**Related:** `startup_intelligence.py`, `gossip_bus.py`, `discover.py`, `lan_peer_channel.py`, `coord_pulse.sh/.ps1`

**Navigation:** → unified timeline (integrated): [2026-07-10-phase-integration-map.md](2026-07-10-phase-integration-map.md) · status/gap tracking: [2026-07-10-pr2-phase0-review-crossreference.md](../../archive/fleet-mesh/2026-07-10-pr2-phase0-review-crossreference.md) · research inputs (PT): [D2 Heartbeat & Failure Detector](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/DELIVERABLE-2-HEARTBEAT-LIVENESS-REGENERATED.md) (feeds § 6.2) · [PATTERN-SYNTHESIS.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PATTERN-SYNTHESIS.md) (P2/P5/P9/P19 map to gossip-relay/split-brain) · [MULTIAGENT-SWARM-SECURITY-ANALYSIS.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md) · architecture research: [2026-07-10-oasn-p2p-architecture-research.md](2026-07-10-oasn-p2p-architecture-research.md)

> **VERIFIED STATUS (2026-07-10, live code check — not a status claim, actually run):**
> Grepped for `FleetMode`, `classify_fleet_mode`, `fleet_topology`, `/api/fleet-topology`,
> `/api/peer-relay-probe`, `--fleet-status`, `probe_lan_peer.py --relay` across both repos.
> **Zero matches for all of them, confirmed twice** (once before, once after a concurrent
> merge landed — see below). None of THIS plan's 6 implementation phases have been started;
> all 10 Success Criteria in § 13 are unchecked and accurate as unchecked (marked inline
> below).
>
> **IMPORTANT — naming collision with a DIFFERENT "Phase 1":** while this session was
> reviewing PT PR #201, a separate concurrent agent working in a git worktree
> (`worktree-phase-1-impl`) merged substantial real implementation directly to PT `main`
> (`c445f6aa`, 5440 lines: `orchestrator/{membership,peer_record,witness_quorum,
> monotonic_gate}.py` + ~4000 lines of tests, 69/69 passing). That work is **PT's
> `PHASE-1-SCOPE-DRAFT.md` "Phase 1.0–1.3.1"** — implementing the D1 PeerObservation
> model, D4's witness-quorum (T4) and monotonic-apply-gate (T7) threat defenses as real
> code. **This is NOT this plan's "Phase 1" (FleetMode/fleet_topology.py)** — both docs
> independently number their next step "Phase 1," describing different scopes. Re-grepped
> for `FleetMode`/`fleet_topology` after that merge: still zero matches, so this plan's
> Phase 1 remains genuinely unstarted. But PT's Phase 1.0–1.3.1 substantially advances the
> *research* this plan's § 6.2/6.3 depend on into *tested code* — closer to ready-to-consume
> than "prerequisite research" implied below. See
> [2026-07-10-pr2-phase0-review-crossreference.md](../../archive/fleet-mesh/2026-07-10-pr2-phase0-review-crossreference.md)
> for the full ledger including this correction.

---

## 1. Problem Statement

The 3-machine LAN fleet (Mac + Win RTX 3080 + Win RTX 5080) currently has no
unified *fleet-level* topology state. Each machine probes peers independently
and has no concept of graceful degradation when peers disappear:

- **No SOLO mode**: if both Win peers are down, the Mac still tries to dispatch
  to them and logs failures instead of cleanly switching to local-only operation.
- **No PAIR mode**: if one Win peer is down, the Mac treats it as a binary
  "Win up/down" without distinguishing "1 of 2 Win nodes reachable."
- **No FLEET mode**: when all 3 are online, there is no swarm coordination.
- **No gossip relay**: if Mac can reach 3080 but not 5080, and 3080 *can* reach
  5080, the Mac has no way to learn 5080's status through 3080.
- **No self-healing**: `discover.py` detects topology changes and re-probes, but
  the re-probe is local-only. No peer-to-peer health propagation exists.

The result: the fleet degrades *silently and incorrectly* instead of *gracefully
and visibly*.

---

## 2. Design Goals

1. **Three named fleet modes** — `SOLO`, `PAIR`, `FLEET` — that replace the
   current binary "distributed yes/no" with a graduated degradation ladder.
2. **Gossip-first relay** — when a node can't reach a peer directly, it asks
   reachable peers for that peer's status before falling back to job-queue
   instructions.
3. **Self-healing mesh** — topology changes trigger automatic re-classification
   without human intervention, using existing `discover.py` watcher + `coord_pulse`
   heartbeat infrastructure.
4. **Headless P2P conventions** — no central coordinator, no cloud dependency,
   no single point of failure. Each node maintains its own view of fleet
   topology and reconciles via gossip.
5. **Idempotent transitions** — mode switches are read-only classifications
   (same input → same output), safe to re-evaluate on every heartbeat.

---

## 3. Fleet Mode Definitions

### `SOLO` — single machine, no peers reachable

| Property | Value |
|---|---|
| **Condition** | `peers_reachable == 0` |
| **Manager backend** | local Ollama (Mac) or local LM Studio (Win) |
| **Coder backend** | local backend only |
| **Cloud fallback** | active if API key present |
| **Dispatch** | all tasks execute locally; no peer inbox/outbox traffic |
| **Banner** | `SOLO · single-node (0 peers)` |

### `PAIR` — this machine + exactly one peer

| Property | Value |
|---|---|
| **Condition** | `peers_reachable == 1` |
| **Manager backend** | local (this machine is coordinator) |
| **Coder backend** | remote peer LM Studio + local fallback |
| **Cloud fallback** | standby (activated only if peer also goes down) |
| **Dispatch** | coord_pulse to the one reachable peer; outbox flush to that peer only |
| **Banner** | `PAIR · 2-node (peer: <ip>)` |

### `FLEET` — 3+ machines mutually reachable

| Property | Value |
|---|---|
| **Condition** | `peers_reachable >= 2` AND at least one peer can also reach the other |
| **Manager backend** | Mac (coordinator); Win nodes are coder-tier |
| **Coder backend** | both Win LM Studio endpoints, round-robin or affinity-routed |
| **Cloud fallback** | disabled (local fleet is sufficient) |
| **Dispatch** | coord_pulse to all peers; outbox flush per-peer; gossip relay active |
| **Banner** | `FLEET · 3-node swarm (3080 ✓ 5080 ✓)` |

---

## 4. Architecture: Extending Existing Primitives

### 4.1 `FleetMode` enum (new, in PT `startup_intelligence.py`)

```python
class FleetMode(str, Enum):
    SOLO  = "SOLO"    # 0 peers reachable
    PAIR  = "PAIR"    # 1 peer reachable
    FLEET = "FLEET"   # 2+ peers reachable + cross-reachable
```

**Relationship to `StartupScenario`:** `StartupScenario` classifies a *single
machine's* backend availability (6 states). `FleetMode` classifies the *fleet's*
peer topology (3 states). They are orthogonal:

```
StartupScenario (local backends) × FleetMode (peer topology) = runtime posture
```

Example: `MAC_DUAL` + `FLEET` = Mac has both Ollama + LM Studio up, and both
Win nodes are reachable. `MAC_OLLAMA_ONLY` + `SOLO` = Mac has Ollama only, no
Win peers.

### 4.2 `classify_fleet_mode()` — pure function, zero I/O

```python
def classify_fleet_mode(
    peers_reachable: int,
    cross_reachable: bool,
) -> FleetMode:
    if peers_reachable == 0:
        return FleetMode.SOLO
    if peers_reachable == 1:
        return FleetMode.PAIR
    if peers_reachable >= 2 and cross_reachable:
        return FleetMode.FLEET
    return FleetMode.PAIR  # 2+ peers but fragmented (no cross-reachability)
```

### 4.3 Fleet topology state file: `~/.openclaw/state/fleet_topology.json`

```json
{
  "schema": 1,
  "timestamp": "2026-07-08T10:42:29Z",
  "local_node": "mac-studio",
  "fleet_mode": "FLEET",
  "peers": [
    {
      "id": "win-rtx3080",
      "ip": "192.168.9.240",
      "port": 1234,
      "reachable": true,
      "last_seen": "2026-07-08T10:42:00Z",
      "models": ["qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2"],
      "can_reach": ["win-rtx5080"]
    },
    {
      "id": "win-rtx5080",
      "ip": "192.168.8.153",
      "port": 1234,
      "reachable": true,
      "last_seen": "2026-07-08T10:42:00Z",
      "models": ["gemma-4-26b-a4b-it-nvfp4"],
      "can_reach": ["win-rtx3080"]
    }
  ],
  "cross_reachable": true,
  "watcher_heartbeat": "2026-07-08T10:42:30Z"
}
```

Idempotent: re-writing with unchanged topology is a no-op (hash-gated, same
pattern as `discover.py`'s `last_discovery.json`).

### 4.4 Gossip relay protocol — `GossipBus` extension

The existing `GossipBus` (`orchestrator/gossip_bus.py`) already has SQLite FTS5
event log, `emit()` / `search()` API, and LanceDB embedding (optional).

**New event type:** `fleet_topology`

```python
bus.emit(
    event_type="fleet_topology",
    payload={
        "source": "mac-studio",
        "fleet_mode": "FLEET",
        "peers": [{"id": "win-rtx3080", "ip": "192.168.9.240", "reachable": true}],
        "cross_reachable": true,
        "ts": time.time(),
    },
)
```

**Gossip relay flow** (when a node can't reach a peer directly):

```
Node A (Mac) ──probe──✗── Node C (5080)
     │
     ├──probe──✓── Node B (3080)
     │
     └──gossip relay──→ Node B: "Can you reach 5080?"
                          │
                          ├──probe──✓── Node C (5080)
                          │
                          └──reply──→ Node A: "5080 is up at 192.168.8.153"
                                       │
                                       └── Node A updates fleet_topology.json
```

Implementation: extend `probe_lan_peer.py` with `--relay` flag. Single HTTP
round-trip, not a persistent connection.

### 4.5 New endpoint: `GET /api/fleet-topology`

Each node's portal exposes a read-only fleet topology endpoint:

```http
GET /api/fleet-topology
Authorization: Bearer <token>

→ 200 OK
{
  "local_node": "mac-studio",
  "fleet_mode": "FLEET",
  "peers": [...],
  "cross_reachable": true,
  "relay_capable": true
}
```

### 4.6 New endpoint: `POST /api/peer-relay-probe`

```http
POST /api/peer-relay-probe
Authorization: Bearer <token>
Content-Type: application/json

{"target_ip": "192.168.8.153", "target_port": 1234}

→ 200 OK
{"reachable": true, "ip": "192.168.8.153", "models": [...], "relay_path": ["B→C"]}
```

### 4.7 Coord pulse extension

The existing 15-minute coord pulse currently drops inbox cards, flushes outbox,
and records pulse seen. Extended pulse (additive):

1. Query each peer's `/api/fleet-topology`
2. Merge peer-reported reachability into local `fleet_topology.json`
3. If a peer is unreachable directly, try gossip relay via a reachable peer
4. Re-classify `FleetMode` from merged topology
5. Emit `fleet_topology` gossip event
6. If mode changed, log the transition

---

## 5. Gossip-First, Queue-Fallback Protocol

When 2 devices communicate but one cannot reach the 3rd:

```
┌─────────────────────────────────────────────────────────────────────┐
│  GOSSIP FIRST (real-time, seconds)                                  │
│                                                                     │
│  1. Node A probes Node C directly → FAIL (timeout/401/unreachable)  │
│  2. Node A queries Node B: "Can you reach C?"                       │
│     → POST /api/peer-relay-probe {"target_ip": "192.168.8.153"}    │
│  3. Node B probes Node C → SUCCESS                                  │
│  4. Node B returns: {"reachable": true, "ip": "...", "relay_path": ["B→C"]} │
│  5. Node A updates local fleet_topology.json with relayed info      │
│  6. Node A emits gossip event: "fleet_topology_relay"               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  QUEUE FALLBACK (asynchronous, minutes)                             │
│                                                                     │
│  7. If gossip relay also fails (B can't reach C either):            │
│     → Node A writes a "peer-unreachable" card to B's inbox          │
│     → Card includes: target IP, last-known models, retry window     │
│     → B's coord_pulse picks it up on next 15-min cycle              │
│     → B attempts to reach C and drops a reply card in A's inbox     │
│  8. If all relay attempts fail for >3 pulses (45 min):              │
│     → FleetMode degrades: FLEET → PAIR (if 1 peer still up)         │
│     → Or: PAIR → SOLO (if 0 peers up)                               │
│     → Transition logged in gossip bus + coord-pulse.log              │
└─────────────────────────────────────────────────────────────────────┘
```

**Why gossip first:** gossip is a single HTTP round-trip (~100ms over LAN).
Queue fallback is a 15-minute coord pulse cycle. If the peer is just slow to
respond (LM Studio loading a model), gossip catches it in seconds; queue
fallback is the safety net for truly unreachable nodes.

---

## 6. Self-Healing Mesh Protocol

### 6.1 Topology watcher (extend `discover.py`)

The existing `_current_liveness()` watcher detects topology changes via
`scutil` on macOS and 30s polling on all platforms. Extension on topology change:

1. Re-probe all peers (existing behavior)
2. Query each reachable peer's `/api/fleet-topology` (new)
3. Merge peer-reported topology into local `fleet_topology.json`
4. Re-classify `FleetMode`
5. If mode changed, emit gossip event + log transition

### 6.2 Heartbeat-based liveness (extend `coord_pulse`)

Each node's coord pulse runs every 15 minutes. Extend to:

1. **Emit heartbeat:** write `{"node": "mac-studio", "ts": ..., "mode": "FLEET"}`
   to local gossip bus
2. **Check peer heartbeats:** query each peer's `/api/fleet-topology` and
   verify `timestamp` is fresh (< 20 min = 1 pulse + 5 min grace)
3. **Mark stale peers:** if heartbeat is stale, mark peer as `reachable: false`
4. **Attempt recovery:** if a previously-stale peer becomes fresh again,
   auto-recover: mark `reachable: true`, re-classify mode, emit
   `"fleet_topology_recovered"` gossip event

### 6.3 Split-brain prevention

When two nodes disagree about a third's reachability:

| Mac says | 3080 says | Resolution |
|---|---|---|
| 5080 UP | 5080 UP | Consensus: 5080 UP |
| 5080 UP | 5080 DOWN | Mac probes 5080 directly; if UP, 3080's view is stale |
| 5080 DOWN | 5080 UP | Mac tries gossip relay via 3080; if relay succeeds, update |
| 5080 DOWN | 5080 DOWN | Consensus: 5080 DOWN → degrade fleet mode |

**Rule:** direct observation beats relayed; relayed beats no observation; stale
observations (< 20 min) are discarded.

---

## 7. Implementation Tasks

### Phase 2: FleetMode classifier + topology state (PT)

| Task | File | Effort |
|---|---|---|
| Add `FleetMode` enum + `classify_fleet_mode()` | `orchestrator/startup_intelligence.py` | 1h |
| Add `fleet_topology.json` schema + read/write helpers | `orchestrator/fleet_topology.py` (new) | 2h |
| Unit tests: 3 modes + cross-reachable edge cases | `tests/test_fleet_mode.py` (new) | 1h |
| Wire `classify_fleet_mode()` into `agent_launcher.py` | `src/perpetua_tools/agent_launcher.py` | 1h |

### Phase 3: Fleet topology endpoint + gossip relay (orama)

| Task | File | Effort |
|---|---|---|
| `GET /api/fleet-topology` endpoint | `src/orama_system/portal_server.py` | 2h |
| `POST /api/peer-relay-probe` endpoint | `src/orama_system/portal_server.py` | 2h |
| `probe_lan_peer.py --relay` flag | `bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py` | 1h |
| Auth-gate both endpoints (existing control_plane_auth) | same | 0.5h |
| Integration tests: relay round-trip, auth rejection | `tests/test_fleet_topology_api.py` (new) | 2h |

### Phase 4: Coord pulse + discover.py extension

| Task | File | Effort |
|---|---|---|
| `coord_pulse.sh`: query peer `/api/fleet-topology` after outbox flush | `bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh` | 1h |
| `coord_pulse.ps1`: same for Windows | `bin/orama-system/skills/hermes-harness/scripts/coord_pulse.ps1` | 1h |
| `discover.py`: merge peer topology + re-classify on topology change | `~/.openclaw/scripts/discover.py` | 2h |
| Gossip event emission on mode transition | `orchestrator/gossip_bus.py` (extend emit) | 0.5h |
| Tests: topology change triggers re-classification | `tests/test_topology_watch.py` | 1h |

### Phase 5: Banner + start script integration

| Task | File | Effort |
|---|---|---|
| `start.sh` banner: show `SOLO` / `PAIR` / `FLEET` mode | `start.sh` | 0.5h |
| `start.ps1` banner: same | `platform/windows/start.ps1` | 0.5h |
| Mode transition logging | `start.sh` + `start.ps1` | 0.5h |
| `--fleet-status` CLI flag (show topology + mode, exit) | `start.sh` + `start.ps1` | 1h |

### Phase 6: Self-healing + split-brain

| Task | File | Effort |
|---|---|---|
| Stale heartbeat detection (< 20 min grace) | `orchestrator/fleet_topology.py` | 1h |
| Auto-recovery on fresh heartbeat | `orchestrator/fleet_topology.py` | 1h |
| Split-brain resolution logic | `orchestrator/fleet_topology.py` | 2h |
| Tests: stale → recover, split-brain consensus | `tests/test_fleet_self_heal.py` | 2h |

**Total estimated effort:** ~25 hours (CC: ~3-4 sessions)

---

## 8. Headless P2P Conventions Applied

| Convention | How this plan follows it |
|---|---|
| **No central coordinator** | Each node maintains its own `fleet_topology.json`; Mac is coordinator by hardware policy, not by mesh protocol |
| **No cloud dependency** | All communication is LAN HTTP + file-based inbox/outbox; cloud fallback is a separate concern |
| **Eventual consistency** | Topology converges within 1-2 coord pulses (15-30 min); gossip relay accelerates to seconds |
| **Gossip propagation** | `GossipBus.emit()` is fire-and-forget; peers read via `/api/fleet-topology` on next pulse |
| **Idempotent state** | `fleet_topology.json` is hash-gated; `classify_fleet_mode()` is a pure function |
| **Graceful degradation** | `FLEET → PAIR → SOLO` is a one-way degradation ladder; recovery is automatic |
| **CRDT-like merge** | Topology merge: `max(timestamp)` wins per peer; direct observation beats relayed |
| **Split-brain tolerance** | Direct > relayed > stale; stale observations are discarded, not propagated |
| **Heartbeat-based liveness** | 15-min coord pulse = heartbeat; 20-min freshness window = grace period |
| **Zero-conf discovery** | `discover.py` already auto-detects LAN peers; no manual peer list needed |

---

## 9. Backward Compatibility

- `StartupScenario` (6 states) remains unchanged. `FleetMode` is additive.
- `classify_scenario()` is not modified. `classify_fleet_mode()` is a new
  function called *after* scenario classification.
- `start.sh` / `start.ps1` existing `WIN_IP` / `WIN_NODES` env vars are
  preserved. `FleetMode` is derived from them, not replacing them.
- `coord_pulse` existing behavior (outbox flush, inbox poll) is unchanged.
  Fleet topology query is appended after the existing steps.
- `GossipBus` existing event types are unchanged. `fleet_topology` is a new
  `event_type` value, not a schema change.
- `probe_lan_peer.py` existing flags are preserved. `--relay` is additive.

---

## 10. Testing Strategy

### Unit tests (offline, no network)

- `classify_fleet_mode()`: all 3 modes + edge cases (2 peers but not
  cross-reachable → PAIR, not FLEET)
- `fleet_topology.json` merge: stale vs fresh, direct vs relayed, hash-gating
- Split-brain resolution: all 4 combinations of Mac/3080 disagreement about 5080

### Integration tests (mocked HTTP)

- `GET /api/fleet-topology` returns correct JSON for each mode
- `POST /api/peer-relay-probe` returns relayed probe result
- Auth rejection: 401 without token, 200 with valid token
- Gossip relay round-trip: A → B → C → B → A

### E2E tests (live LAN, manual)

- Kill 5080's portal → Mac degrades FLEET → PAIR within 1 coord pulse
- Restart 5080 → Mac auto-recovers PAIR → FLEET within 1 pulse
- Block Mac→5080 but allow 3080→5080 → gossip relay succeeds, Mac sees 5080 UP
- Block all peer traffic → Mac degrades to SOLO, cloud fallback activates

---

## 11. Decision Audit Trail

| # | Decision | Rationale | Rejected alternative |
|---|---|---|---|
| 1 | 3 modes (SOLO/PAIR/FLEET) not 6 | User's spec names exactly 3; 6 startup scenarios remain orthogonal | Merge with StartupScenario (rejected: conflates local backends with peer topology) |
| 2 | `fleet_topology.json` not in `last_discovery.json` | Discovery is local-backend-focused; fleet is peer-topology-focused | Extend `last_discovery.json` (rejected: schema bloat, coupling) |
| 3 | Gossip relay via HTTP, not WebSocket | Single round-trip; existing WS channel is for streaming, not request-response | Use WS for relay (rejected: wrong transport for request-response) |
| 4 | 15-min heartbeat, not 5s | Existing coord_pulse is 15 min; changing it would break Windows Task Scheduler | Sub-second heartbeat (rejected: excessive traffic, battery drain) |
| 5 | `classify_fleet_mode()` is pure function | Idempotent, testable, zero I/O | Classify inside coord_pulse (rejected: untestable, side-effecting) |
| 6 | Direct > relayed > stale | Direct observation is ground truth | Timestamp priority only (rejected: fresh relayed is less reliable than direct) |

---

## 12. Open Questions

1. **Persist `FleetMode` across restarts?** Recommendation: re-classify on every
   startup (idempotent, < 1s). Stale persisted state is dangerous.
2. **Should a Win node self-elect as coordinator if Mac is down?** Recommendation:
   no for v1. Mac is coordinator per D14 hardware policy. Win self-election is v2.
3. **Encrypt `fleet_topology.json` at rest?** Recommendation: no. Contains LAN
   IPs and model names, not secrets. Consistent with `last_discovery.json`.
4. **Relay probe auth — whose token?** 3080 uses its own
   `ORAMA_CONTROL_PLANE_TOKEN` to probe 5080. Requires shared token (current
   design) or joint-account lanes. Document the shared-token requirement in
   onboarding; joint-account is v1.1.

---

## 13. Success Criteria

Verified live 2026-07-10 by grepping both repos for every named symbol/endpoint/flag
below — not a status re-assertion. All still unchecked; none are close (Phase 1
hasn't started, so criteria depending on later phases are also blocked).

- [ ] `classify_fleet_mode()` unit tests pass (3 modes + edge cases) — **NOT STARTED**, symbol doesn't exist in either repo
- [ ] `GET /api/fleet-topology` returns correct JSON for all 3 modes — **NOT STARTED**, route doesn't exist in `portal_server.py`
- [ ] `POST /api/peer-relay-probe` returns relayed probe result — **NOT STARTED**, route doesn't exist
- [ ] Killing a Win node's portal triggers FLEET → PAIR within 1 coord pulse — **BLOCKED**, depends on unstarted Phase 2–4
- [ ] Restarting the node triggers PAIR → FLEET within 1 coord pulse — **BLOCKED**, same
- [ ] Gossip relay succeeds when direct probe fails but a peer can reach the target — **NOT STARTED**, `probe_lan_peer.py --relay` doesn't exist
- [ ] `start.sh --fleet-status` shows current mode + topology (read-only, exit) — **NOT STARTED**, flag doesn't exist
- [ ] Banner shows `SOLO` / `PAIR` / `FLEET` with peer count — **NOT STARTED**
- [ ] No breaking changes to existing `StartupScenario`, `WIN_IP`, or `coord_pulse` — **N/A yet**, nothing has touched them
- [ ] All new endpoints auth-gated (401 without token) — **N/A yet**, no endpoints exist to gate

**What exceeded original scope (not requested by this plan, landed anyway):**
PT's `feature/phase-0-blocker-fixes` branch (PR #201) shipped substantially more
security rigor than this plan called for — a full P2P threat model (T1–T7),
20 battle-tested pattern catalog, 16 identified gaps with a Phase 1b roadmap,
and TDD test specs — none of which this plan's Phase 1–5 tasks required, but
all of which directly harden §§ 4.4/6.2/6.3 (gossip relay, heartbeat liveness,
split-brain) once Phase 1–5 implementation begins. See
[2026-07-10-pr2-phase0-review-crossreference.md](../../archive/fleet-mesh/2026-07-10-pr2-phase0-review-crossreference.md)
for the full ledger.
