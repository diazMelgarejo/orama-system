# Win vs Mac Hermes coord pulse — implementation comparison

> **Superseded by:** [`pulse-unified-comparison.md`](../pulse-unified-comparison.md) (coord-019 pros/cons + merge matrix)

**Date:** 2026-06-29  
**Fan-out:** coord-014  
**Plan:** `references/coord-pulse-plan.md`

## Shared core (both hosts)

| Layer | Artifact | Behavior |
|-------|----------|----------|
| Cadence | 900s | `install_coord_pulse.{ps1,sh}` |
| Log | `~/.openclaw/state/lan_peer/coord-pulse.log` | append-only |
| Lock | `*_pulse.lock` + live PID | skip tick if job running |
| Tier 0 | `probe_lan_peer.py --json` | Ladder F gate |
| Tier 1 | `cursor-agent --print --model composer-2.5` | one shot per tick |
| Post-job | learn.py + push (agent card) | PT `.agent` |

## Side-by-side

| Dimension | **Windows** (`coord_pulse.ps1`) | **Mac/Linux** (`coord_pulse.sh`) |
|-----------|--------------------------------|----------------------------------|
| Scheduler | Task Scheduler `OramaCoordPulse` | launchd `com.orama.coord-pulse` |
| Lock file | `win_pulse.lock` | `mac_pulse.lock` |
| Repo env | `ORAMA_SYSTEM_PATH` required | `ORAMA_SYSTEM_PATH` or git-detect |
| Git fetch | `git fetch origin main` each tick | not in pulse (agent card / manual) |
| Queue | `win_job_queue.py` | `mac_job_queue.py` (P2) |
| Roles | `coder`, `autoresearcher` | `orchestrator`, `researcher` |
| Enqueue filter | `win-coder-*`, `win-autoresearcher-*` | `win-*` deliverables, `mac-orchestrator-*` |
| Blocked jobs | `BlockedPending` + `BLOCKED_PENDING` in Python | no blocked list yet |
| Skip acks | via `is_actionable_assignment` | `_SKIP_FILES` (cycle acks) |
| Idle gate | **exits** if no actionable pending | was: log only; **fixed:** exit if queue not idle |
| Inbox diff | none in pulse | `last_pulse_seen.json` snapshot |
| Agent card | role-specific (`win-coder-queue.md`) | single `mac-orchestrator-queue.md` |
| Agent prompt | includes **job id** from queue | generic "ONE inbox/backlog job" |
| Dry run | `-DryRun` | `--dry-run` |
| Listen-only | `coord_monitor.ps1 -Minutes 15` | manual / operator |

## Queue semantics

**Win** pulls Mac assignments into serial queues; pulse skips blocked L1 until P5 on `main`. Pulse will not spawn `cursor-agent` unless a non-blocked pending job exists.

**Mac** pulls Win deliverables (`win-*` drops) and explicit `mac-*` cards. Orchestrator handles PR triage / merge queue; researcher handles autoresearch topics.

## Gaps to close (ordered)

1. **Mac blocked prereqs** — mirror `BLOCKED_PENDING` when Mac gets gated cards.
2. **Mac job-specific prompt** — pass `mac_job_queue` job id into cursor-agent like Win.
3. **Bold priority** — `mac_job_queue._priority` now matches Win bold-tolerant regex.
4. **P2 portal** — `/co-orchestration/macos` pulse status (deferred).

## Operator install

```powershell
# Win
$env:ORAMA_SYSTEM_PATH = '...'; $env:PERPETUA_TOOLS_PATH = '...'
.\scripts\install_coord_pulse.ps1 -Status
```

```bash
# Mac
./scripts/install_coord_pulse.sh --status
```
