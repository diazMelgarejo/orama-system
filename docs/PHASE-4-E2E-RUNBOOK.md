# Phase 4 End-to-End Integration Runbook

**Date:** 2026-07-11  
**Status:** Prep for manual E2E validation (automated tests in `tests/test_coord_pulse_integration.py`)  
**Scope:** Live LAN topology transitions across Mac + Windows peers  
**Duration:** ~30 minutes (5 scenarios × ~6 min each)

---

## Prerequisites

### Hardware Setup
- Mac: Ollama at `localhost:11434` with `qwen3.5:9b-nvfp4` loaded
- Win (RTX3080): LM Studio at `$LM_STUDIO_WIN_ENDPOINTS` (e.g., `192.168.1.101:8002`)
- Win (RTX5080): LM Studio at `192.168.1.102:8002` (optional, for FLEET testing)
- LAN: All machines must ping each other (verified by `discover-lm-studio.sh`)

### Software Prerequisites
```bash
# On Mac
cd $ORAMA
git pull origin main
python3 -m pytest tests/test_coord_pulse_integration.py -v  # Unit tests pass

# On Win (both machines)
cd $PERPETUA_TOOLS
python3 -m pytest tests/test_fleet_mode.py -v  # Unit tests pass
```

### Access & Tokens
```bash
# Mac: Set control plane token (for API auth)
export ORAMA_CONTROL_PLANE_TOKEN="your-token-here"

# Win: Set same token (must match for relay probe)
setx ORAMA_CONTROL_PLANE_TOKEN "your-token-here"
```

### Log Files (for observation)
```bash
# Mac
mkdir -p ~/.openclaw/state/lan_peer
tail -f ~/.openclaw/state/fleet_topology.json
tail -f ~/.openclaw/state/lan_peer/coord-pulse.log
tail -f ~/.openclaw/state/gossip_events.jsonl  # New in Phase 4

# Win (PowerShell)
$env:LOCALAPPDATA + "\orchestrator\fleet_topology.json"
$env:LOCALAPPDATA + "\orchestrator\gossip_events.jsonl"
```

---

## Scenario 1: SOLO → PAIR (Single Peer Discovery)

**Goal:** Verify Mac discovers Win, transitions from SOLO to PAIR mode.

### Setup
```bash
# Mac: Stop any Win connections (simulate SOLO)
# Confirm: ~/.openclaw/state/fleet_topology.json has fleet_mode=SOLO

# Win (RTX3080): Ensure LM Studio running
curl http://192.168.1.101:8002/v1/models
# Should return models list
```

### Execution
```bash
# Mac: Run coord_pulse manually (instead of cron)
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh --dry-run

# Then run live (without --dry-run)
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
```

### Observation
```bash
# In terminal 1 (tail log)
tail -f ~/.openclaw/state/lan_peer/coord-pulse.log

# Expected log output:
# [timestamp] pulse start dry_run=0
# [timestamp] probe_lan_peer.py: querying 192.168.1.101:8002
# [timestamp] peer responded: fleet_mode=SOLO
# [timestamp] merged topology: peers=[win-rtx3080], fleet_mode=PAIR
# [timestamp] topology transition: SOLO → PAIR
# [timestamp] gossip event emitted: fleet_topology_transition

# In terminal 2 (watch topology)
watch -n 1 "cat ~/.openclaw/state/fleet_topology.json | python3 -m json.tool"

# Expected:
# {
#   "local_node": "mac-studio",
#   "fleet_mode": "PAIR",          ← Changed from SOLO
#   "peers": ["win-rtx3080"],
#   "cross_reachable": false,
#   "timestamp": 1234567890.123
# }

# In terminal 3 (watch gossip events)
tail -f ~/.openclaw/state/gossip_events.jsonl

# Expected:
# {"event_type": "fleet_topology_transition", "old_mode": "SOLO", "new_mode": "PAIR", ...}
```

### Validation Checklist
- [ ] Coord pulse completes without errors (<15 min)
- [ ] fleet_topology.json updated with PAIR mode
- [ ] Gossip event logged in gossip_events.jsonl
- [ ] Log shows "SOLO → PAIR" transition

---

## Scenario 2: PAIR → FLEET (Second Peer Discovery + Cross-Reachability)

**Goal:** Verify Mac discovers 2nd Win peer and cross-reachability, transitions to FLEET.

### Setup
```bash
# Mac: Currently in PAIR mode from Scenario 1

# Win (RTX5080): Ensure 2nd LM Studio running on 192.168.1.102:8002
curl http://192.168.1.102:8002/v1/models
# Should return models list

# Ensure Win (3080) can reach Win (5080)
curl http://192.168.1.102:8002/api/fleet-topology
# Should show 5080 in peers list
```

### Execution
```bash
# Mac: Run coord_pulse again
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
```

### Observation
```bash
# Expected log output:
# [timestamp] peer responded: fleet_mode=FLEET, peers=[win-rtx5080]
# [timestamp] merged topology: peers=[win-rtx3080, win-rtx5080]
# [timestamp] cross_reachable: true (from peer's view)
# [timestamp] topology transition: PAIR → FLEET

# Expected fleet_topology.json:
# {
#   "fleet_mode": "FLEET",         ← Changed from PAIR
#   "peers": ["win-rtx3080", "win-rtx5080"],
#   "cross_reachable": true,       ← Now true
# }

# Expected gossip event:
# {"event_type": "fleet_topology_transition", "old_mode": "PAIR", "new_mode": "FLEET", ...}
```

### Validation Checklist
- [ ] Coord pulse discovers 2nd peer
- [ ] fleet_mode transitions to FLEET
- [ ] cross_reachable set to true
- [ ] Gossip event shows PAIR → FLEET

---

## Scenario 3: FLEET → PAIR (Peer Loss)

**Goal:** Verify Mac handles peer failure, transitions from FLEET to PAIR.

### Setup
```bash
# Mac: Currently in FLEET mode from Scenario 2

# Win (RTX5080): Stop LM Studio
# Simulate peer failure by killing process or stopping service
killall LMStudio  # or equivalent on Windows
```

### Execution
```bash
# Mac: Run coord_pulse
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
```

### Observation
```bash
# Expected log output:
# [timestamp] probe 192.168.1.102:8002 — timeout (unreachable)
# [timestamp] merged topology: peers=[win-rtx3080], cross_reachable=false
# [timestamp] topology transition: FLEET → PAIR

# Expected fleet_topology.json:
# {
#   "fleet_mode": "PAIR",          ← Changed from FLEET
#   "peers": ["win-rtx3080"],
#   "cross_reachable": false,
# }

# Expected gossip event:
# {"event_type": "fleet_topology_transition", "old_mode": "FLEET", "new_mode": "PAIR", ...}
```

### Validation Checklist
- [ ] Coord pulse detects unreachable peer (timeout)
- [ ] fleet_mode transitions to PAIR
- [ ] Remaining peer still in topology
- [ ] Gossip event shows FLEET → PAIR

---

## Scenario 4: PAIR → SOLO (Total Peer Loss)

**Goal:** Verify Mac handles all peers becoming unreachable, transitions to SOLO.

### Setup
```bash
# Mac: Currently in PAIR mode from Scenario 3

# Win (RTX3080): Stop LM Studio
# Simulate total peer loss
killall LMStudio  # or equivalent on Windows
```

### Execution
```bash
# Mac: Run coord_pulse
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
```

### Observation
```bash
# Expected log output:
# [timestamp] probe 192.168.1.101:8002 — timeout (unreachable)
# [timestamp] merged topology: peers=[], cross_reachable=false
# [timestamp] topology transition: PAIR → SOLO

# Expected fleet_topology.json:
# {
#   "fleet_mode": "SOLO",          ← Changed from PAIR
#   "peers": [],
#   "cross_reachable": false,
# }

# Expected gossip event:
# {"event_type": "fleet_topology_transition", "old_mode": "PAIR", "new_mode": "SOLO", ...}
```

### Validation Checklist
- [ ] Coord pulse detects all peers unreachable
- [ ] fleet_mode transitions to SOLO
- [ ] Peers list is empty
- [ ] Gossip event shows PAIR → SOLO

---

## Scenario 5: Recovery (SOLO → PAIR → FLEET)

**Goal:** Verify recovery after total loss, reverse scenarios 3-1.

### Setup
```bash
# Mac: Currently in SOLO mode from Scenario 4

# Win (RTX3080): Restart LM Studio
# Win (RTX5080): Restart LM Studio (if available)

# Verify both are reachable
curl http://192.168.1.101:8002/v1/models
curl http://192.168.1.102:8002/v1/models
```

### Execution
```bash
# Mac: Run coord_pulse iteratively

# Step 1: Discover RTX3080
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
# Should transition: SOLO → PAIR

# Step 2: Discover RTX5080 and cross-reachability
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
# Should transition: PAIR → FLEET
```

### Observation
```bash
# First pulse:
# [timestamp] topology transition: SOLO → PAIR

# Second pulse:
# [timestamp] topology transition: PAIR → FLEET

# Final fleet_topology.json:
# {
#   "fleet_mode": "FLEET",
#   "peers": ["win-rtx3080", "win-rtx5080"],
#   "cross_reachable": true,
# }

# Expected gossip events (2 total):
# {"event_type": "fleet_topology_transition", "old_mode": "SOLO", "new_mode": "PAIR", ...}
# {"event_type": "fleet_topology_transition", "old_mode": "PAIR", "new_mode": "FLEET", ...}
```

### Validation Checklist
- [ ] Recovery sequence works correctly
- [ ] Transitions logged in correct order
- [ ] Final state is FLEET
- [ ] No event duplication

---

## Scenario 6: Stable Topology (FLEET → FLEET)

**Goal:** Verify stable FLEET mode doesn't emit unnecessary events.

### Setup
```bash
# Mac: Currently in FLEET mode from Scenario 5

# Both Win peers remain running
```

### Execution
```bash
# Mac: Run coord_pulse multiple times (stable mode)
for i in {1..3}; do
  bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
  sleep 60
done
```

### Observation
```bash
# Expected log output (3 pulses):
# [timestamp] Pulse 1: topology stable, fleet_mode=FLEET
# [timestamp] Pulse 2: topology stable, fleet_mode=FLEET
# [timestamp] Pulse 3: topology stable, fleet_mode=FLEET
# (No transition message)

# Expected fleet_topology.json:
# {
#   "fleet_mode": "FLEET",
#   "peers": ["win-rtx3080", "win-rtx5080"],
#   "cross_reachable": true,
# }

# Expected gossip events:
# (No new events emitted during stable runs)
```

### Validation Checklist
- [ ] No mode transition (stays FLEET)
- [ ] No new gossip events emitted
- [ ] Topology remains consistent
- [ ] Coord pulse completes quickly (no hang)

---

## Performance Validation (All Scenarios)

### Metrics to Track

**Coord Pulse Cycle Time:**
```bash
# Time the entire pulse
time bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh

# Should complete in < 15 minutes
```

**Peer Query Latency:**
```bash
# Time individual peer queries (in coord_pulse logs)
grep "probe.*[0-9]\..*ms" ~/.openclaw/state/lan_peer/coord-pulse.log

# Each peer query should be < 2 seconds
```

**Memory Usage (no leak):**
```bash
# Run 10 consecutive pulses, monitor memory
ps aux | grep coord_pulse
# Memory should not grow unbounded
```

**File Size (no bloat):**
```bash
# Check gossip_events.jsonl size after all scenarios
wc -l ~/.openclaw/state/gossip_events.jsonl
# Should have exactly 6 events (one per transition)

du -h ~/.openclaw/state/fleet_topology.json
# Should remain < 10KB
```

---

## Troubleshooting

### Coord Pulse Hangs
```bash
# Check for stale lock
ls -la ~/.openclaw/state/lan_peer/mac_pulse.lockdir/

# If stale, remove and retry
rm -rf ~/.openclaw/state/lan_peer/mac_pulse.lockdir
bash $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh
```

### Peer Unreachable
```bash
# Verify peer IP (may have changed on DHCP)
cat ~/.openclaw/state/last_discovery.json

# Manually probe peer
curl http://<peer_ip>:8002/v1/models

# Check firewall (Mac may block outbound)
sudo lsof -i :8002
```

### Gossip Events Not Emitted
```bash
# Check event emission code in coord_pulse.sh
grep -A 5 "fleet_topology_transition" $ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh

# Verify ORAMA_CONTROL_PLANE_TOKEN is set
echo $ORAMA_CONTROL_PLANE_TOKEN

# Check API endpoint
curl -H "Authorization: Bearer $ORAMA_CONTROL_PLANE_TOKEN" \
  http://localhost:8001/api/fleet-topology
```

### Test Failures
```bash
# Re-run unit tests
python3 -m pytest tests/test_coord_pulse_integration.py::TestTopologyMergeAndClassification -v

# Check FleetMode import
python3 -c "from orchestrator.startup_intelligence import FleetMode; print(FleetMode.SOLO)"
```

---

## Post-Runbook

### Data Collection
```bash
# Archive logs for analysis
tar czf coord_pulse_e2e_$(date +%Y%m%d-%H%M%S).tar.gz \
  ~/.openclaw/state/fleet_topology.json \
  ~/.openclaw/state/gossip_events.jsonl \
  ~/.openclaw/state/lan_peer/coord-pulse.log
```

### Validation Report
Create a summary:
```markdown
## Phase 4 E2E Validation Report (2026-07-11)

### Results
- [ ] Scenario 1 (SOLO → PAIR): PASS / FAIL
- [ ] Scenario 2 (PAIR → FLEET): PASS / FAIL
- [ ] Scenario 3 (FLEET → PAIR): PASS / FAIL
- [ ] Scenario 4 (PAIR → SOLO): PASS / FAIL
- [ ] Scenario 5 (SOLO → PAIR → FLEET): PASS / FAIL
- [ ] Scenario 6 (FLEET stable): PASS / FAIL

### Performance
- Avg. cycle time: _____ seconds
- Max peer query time: _____ seconds
- Memory growth: _____ MB over 10 cycles
- Gossip event count: _____ events

### Issues
- None / See separate issue tracker
```

---

## Next Steps (Phase 5)

After Phase 4 validation:
1. Merge `feature/fleet-modes` to both repos
2. Begin Phase 5: Banner integration (SOLO/PAIR/FLEET display + `--fleet-status`)
3. Update CI/CD pipeline to include integration tests
4. Document LAN setup for new installations

---

**Document Owner:** orama-system/Phase 4 Integration Task Force  
**Last Updated:** 2026-07-11  
**Next Review:** After manual E2E validation complete
