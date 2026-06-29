# Hermes coord pulse — unified comparison (Mac vs Win)

**Date:** 2026-06-29  
**Fan-out:** coord-019  
**Plan:** `coord-pulse-plan.md`  
**Implementations:** `coord_pulse.sh`, `coord_pulse.ps1`

---

## Shared core (keep on both)

| Feature | Why |
|---------|-----|
| 900s scheduler | Frugal; matches operator ritual |
| `probe_lan_peer.py` | Ladder F before fan-out |
| `*_job_queue.py` + `pulse-gate` | One JSON gate for idle/actionable/busy |
| `last_pulse_seen.json` | Inbox diff telemetry |
| `BLOCKED_PENDING` in Python | Single source; no duplicate ps1/bash lists |
| Job id + role in cursor-agent prompt | Deterministic one-shot |
| Role-specific agent cards | Coder vs autoresearcher / orchestrator vs researcher |
| `coord-pulse.log` | Operator tail |

---

## Pros and cons

### Windows (`coord_pulse.ps1`)

| Pros | Cons |
|------|------|
| **Role-specific agent cards** (`win-coder-queue`, `win-autoresearcher-queue`) | PID lock only — no `flock` on Windows |
| Strict `ORAMA_SYSTEM_PATH` — fails fast if misconfigured | `ORAMA_SYSTEM_PATH` required (no git-detect fallback) |
| `coord_monitor.ps1 -Minutes N` for listen-only multi-tick | Task Scheduler setup is more steps than launchd |
| Mature `win_job_queue` with assignment-card filters | Historically duplicated `BlockedPending` in ps1 **(fixed: pulse-gate)** |
| GPU / LM Studio single-tenant enforced by one job per role | No `job_cycle_listen.sh` reset-on-job yet on Win |

### Mac/Linux (`coord_pulse.sh`)

| Pros | Cons |
|------|------|
| **`flock` lock** — covers full cursor-agent run | No native `coord_monitor` equivalent (use `job_cycle_listen.sh`) |
| `pulse-gate` + idle exit (P2.1) | launchd only on macOS (Linux uses same script, manual cron) |
| Git-detect `ORAMA` when env unset | Was single generic agent card **(fixed: researcher card)** |
| `job_cycle_listen.sh` + `coord_mark_job_done.sh` reset timer | `composer-2.5` may hit cloud (Ladder B2 not wired in pulse) |
| Fetches **both** orama + PT repos | Portal pulse status endpoint still deferred (P2) |

---

## Merge matrix (best idea → both hosts)

| Idea | Source | Adopted |
|------|--------|---------|
| `pulse-gate` CLI | Mac | **Both** (coord-019) |
| `last_pulse_seen.json` snapshot | Mac | **Both** (coord-019 Win) |
| `BLOCKED_PENDING` in queue only | Win | **Both** (Mac already) |
| Role-specific agent card | Win | **Both** (Mac researcher → autoresearcher card) |
| `flock` during agent | Mac | Mac only (Win keeps PID+finally) |
| Dual-repo `git fetch` | Mac | **Both** (Win adds PT fetch) |
| `job_cycle_listen` reset-on-job | Mac | Mac; Win uses `coord_monitor.ps1` |
| Listen-only multi-tick | Win | Win `coord_monitor`; Mac `job_cycle_listen.sh` |
| Bold `**Priority:**` regex | Win | Both queues |

---

## When to use which host

| Work type | Host | Queue role |
|-----------|------|------------|
| PR merge / triage / Mac acks | Mac | `orchestrator` |
| GPU autoresearch / H5 | Win | `autoresearcher` |
| Bridge / portal / coder spikes | Win | `coder` |
| Win→Mac deliverables (`win-*`) | Mac | `orchestrator` or `researcher` |
| Mac→Win assignments (`win-coder-*`) | Win | `coder` |

---

## Operator verify

```bash
# Mac
./bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh --dry-run
./bin/orama-system/skills/hermes-harness/scripts/job_cycle_listen.sh --rounds 3 --tag manual
```

```powershell
# Win
.\bin\orama-system\skills\hermes-harness\scripts\coord_pulse.ps1 -DryRun
.\bin\orama-system\skills\hermes-harness\scripts\coord_monitor.ps1 -Minutes 15
```

---

## Remaining gaps (P2+)

1. Portal `/co-orchestration/{macos,windows}` pulse status JSON
2. Win port of `job_cycle_listen.sh` reset semantics (or document `coord_monitor` as equivalent)
3. Shared `blocked_pending.json` config (avoid drift between queues)
4. Ladder B2 local model fallback in pulse spawn
