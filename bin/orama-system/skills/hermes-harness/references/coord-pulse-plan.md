# Coord pulse — 15-minute idle job dispatcher (PLAN)

**AFRP:** Type C | Practitioner | Mode 2  
**Scope:** Schedule Mac/Linux OpenClaw to pull one inbox job when idle, without new Gateway RPC.  
**v1 anchor:** `docs/plans/2026-05-29-03-v1.1-definitive.md` §2 tiers 0–2; `graceful-degradation.md` Ladders C, E, F.

---

## Recommendation (most frugal — reuse existing)

**Do not** add Gateway job RPC or cloud cron. Reuse:

| Layer | Existing artifact | Role in pulse |
|-------|-------------------|---------------|
| Schedule | `install_network_watch.sh` + launchd plist pattern | `com.orama.coord-pulse` every **900s** |
| Health | `probe_lan_peer.py` | Ladder F gate before fan-out |
| Inbox | `lan_peer_assign.py` list / read | Job bucket (Mac + Win drops) |
| Win serial | `win_job_queue.py` | Win side only (already shipped) |
| Monitor | `coord_monitor.ps1` (Win) | Mirror as `coord_pulse.sh` (Mac) |
| Agent | `.cursor/agents/mac-orchestrator-queue.md` + `cursor-agent --print` | One local job when idle |
| Learn | PT `learn.py` + `auto_dream.py` | After each completed job |
| Discovery | `com.orama.network-watch` | Unrelated; keep 30s IP refresh |

**OpenClaw Gateway (`:18789`)** stays a **model/control plane**, not the scheduler. Pulse is **launchd → shell → optional cursor-agent** (Tier 0 → Tier 1).

---

## Pulse algorithm (Mac/Linux)

```text
every 15 min (launchd StartInterval=900):
  1. Tier 0 — if mac_pulse.lock exists and pid alive → EXIT (job running)
  2. Tier 0 — probe_lan_peer.py --json → log; abort fan-out if hard FAIL (optional continue local)
  3. Tier 0 — git fetch both repos (no pull unless post-job hook)
  4. Tier 0 — lan_peer_assign.py list + list --peer
       → diff against ~/.openclaw/state/lan_peer/last_pulse_seen.json
  5. IF no new actionable card AND mac_job_queue idle → EXIT (frugal idle)
  6. Tier 1 — cursor-agent --print --model <local/fast> \
       "Follow .cursor/agents/mac-orchestrator-queue.md: one job, learn, push, drop"
  7. Post-job — pull --rebase, push, update last_pulse_seen.json, remove lock
```

**Actionable Mac jobs:** new `win-*` drop needing Mac ack; `V1_DEFERRED_BACKLOG` row; local `mac-*` assignment card.

**Not actionable:** ops acks, already-processed filenames in `last_pulse_seen.json`.

---

## Mac job queue (thin mirror of Win)

Add `mac_job_queue.py` (optional P1 spike follow-on):

- State: `~/.openclaw/state/lan_peer/mac_job_queue.json`
- Roles: `orchestrator`, `researcher` (single active each)
- `enqueue` scans inbox for `mac-*` + unacked `win-*` deliverables
- Pulse calls `enqueue` + `status`; cursor-agent runs `next orchestrator` only

Win keeps `win_job_queue.py`; Mac does **not** SSH to Win.

---

## Scheduling install (copy network-watch)

```bash
# New: scripts/install_coord_pulse.sh
# Plist: config/com.orama.coord-pulse.plist
#   StartInterval: 900
#   Program: coord_pulse.sh
# Log: ~/.openclaw/state/lan_peer/coord-pulse.log
```

Win operator: `coord_pulse.ps1` one-shot per tick; `install_coord_pulse.ps1` registers Task Scheduler **OramaCoordPulse** every **900s**. Manual window: `coord_monitor.ps1 -Minutes 15` (multi-tick listen, no agent).

---

## Hermes Gateway pulse (bidirectional — Win + Mac + Linux)

**Name:** Hermes coord pulse (not OpenClaw Gateway `:18789` — that stays model/control plane).

```text
┌─────────────────────────────────────────────────────────────┐
│  every 900s (launchd Mac | Task Scheduler Win)              │
│    Tier 0: lock file → skip if job running                  │
│    Tier 0: probe_lan_peer.py (listen Win/Mac/Linux peer)    │
│    Tier 0: git fetch + win_job_queue enqueue / inbox list   │
│    Tier 0: skip if no actionable work OR blocked prereq     │
│    Tier 1: cursor-agent --print ONE job (queue agent card)  │
│    Post:   learn.py + auto_dream + push + peer drop         │
└─────────────────────────────────────────────────────────────┘
```

| Host | Scheduler | Script | Agent card |
|------|-----------|--------|------------|
| Mac/Linux | `com.orama.coord-pulse` | `coord_pulse.sh` | `mac-orchestrator-queue.md` |
| Windows | `OramaCoordPulse` | `coord_pulse.ps1` | `win-coder-queue.md` / `win-autoresearcher-queue.md` |
| Manual (any) | operator | `coord_monitor.ps1 -Minutes 15` | listen-only, no spawn |

**Frugal rules:** one job per pulse; no new broker; blocked cards (e.g. L1 until P5) stay in queue but pulse skips them; peer timeout → local backlog only.

**Cycle the operator described:**

1. Finish one queue job → push/sync → learn ALL  
2. Wait 15 min (scheduler fires OR `coord_monitor.ps1`)  
3. Probe Mac/Win/Linux peer → enqueue → if idle, cursor-agent claims next job  
4. Repeat


## cursor-agent invocation (frugal)

```bash
cursor-agent --print --model composer-2.5 \
  "Read orama-system/.cursor/agents/mac-orchestrator-queue.md. \
   Execute exactly ONE job from lan_peer inbox or V1_DEFERRED_BACKLOG. \
   learn.py + auto_dream.py on PT. push main. Drop deliverable to Win if needed."
```

- **One shot per pulse** — no daemon cursor-agent
- **No cloud** unless local Ollama/cursor-agent fails twice (Ladder B2)
- Subagent fan-out only when assignment card says Mode 3

---

## Degradation (bidirectional)

| Failure | Fallback |
|---------|----------|
| cursor-agent missing | Log + skip; manual operator |
| peer timeout | Process local backlog only; retry drop next pulse |
| git conflict | Stash drift; learn lesson; do not spawn second agent |
| Win idle, Mac busy | Win `coord_monitor.ps1` continues local queue |

---

## Implementation phases

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **P0** | `coord_pulse.sh` + `mac-orchestrator-queue.md` agent card | Manual `./coord_pulse.sh` runs one cycle |
| **P1** | `install_coord_pulse.sh` + launchd plist | `launchctl list \| grep coord-pulse` |
| **P2** | `mac_job_queue.py` + portal `/co-orchestration/macos` pulse status | Unit tests |
| **P3** | Win `coord_pulse.ps1` + `install_coord_pulse.ps1` (Task Scheduler) | `Get-ScheduledTask OramaCoordPulse` |

**Out of scope:** Gateway WebSocket job bus, remote Hermes RPC, new paid APIs.

---

## Verification

```bash
./bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh --dry-run
./bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
launchctl list | grep com.orama.coord-pulse
tail -f ~/.openclaw/state/lan_peer/coord-pulse.log
```

---

## Relation to current manual cycle

Manual loop today = pulse + cursor-agent session. This plan **automates the wait/listen/sync** half; operator still approves PR merges (#183, #199).
