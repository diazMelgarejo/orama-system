# LAN Peer Coordination — Operator Reference

> **Role:** Win↔Mac co-orchestration restore, queue gates, inbox drops, coord pulse semantics.
> **Absorbed from:** Hermes-local `hermes-harness` self-improve fork (2026-07-23).
> **SSOT probe playbook:** [`lan-peer-self-talk.md`](lan-peer-self-talk.md)

## Roles

| Host | Harness | Inference |
|------|---------|-----------|
| **Windows** | Hermes + `start.ps1` | LM Studio `localhost:1234` |
| **Mac** | OpenClaw + `start.sh` | Ollama `localhost:11434` (+ optional Mac LM Studio) |

Peer IP: `last_discovery.json` only — never hardcode DHCP addresses.

Session state: `~/.openclaw/state/lan_peer/co_orchestration_session.json`

## Health contract

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json
```

Required PASS checks (from discovery peer IP):

| Check | Meaning |
|-------|---------|
| `portal-health` | Peer portal `GET /health` on `:8002` |
| `portal-status` | Authenticated `/api/status` |
| `peer-lmstudio` | Peer `GET /v1/models` at discovery port |
| `ws-peer` | Probe ack from peer |

If all four PASS, peer LPS is green even when `lan_peer_session.py status` still shows
historical `mode: macos-only`.

## Resume co-orchestration from degraded mode

Reachability alone does not clear `macos-only`. Record success explicitly:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_session.py record-success
```

Then `status` should show `mode: co-orchestration` and `failure_count: 0`.
Use `should-retry` only to check backoff elapsed; `record-success` is the resume action.

## Inbox drop pattern

```powershell
$ts = Get-Date -Format "yyyy-MM-ddTHH-mm"
$file = "$env:TEMP\win_next_action_$ts.md"
Set-Content -Path $file -Value "# Next action`n- request ...`n"
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop `
  --peer --file $file --filename (Split-Path $file -Leaf) `
  --assignee mac --topic "ops/next-actions"
```

Filename rules (`sanitize_filename`): `A-Z a-z 0-9 _ - .` only — **no colons, no spaces**.
Use `yyyy-MM-ddTHH-mm`, not `HH:mm`.

Fan-out to both hosts: [`update-all-agents-comms.md`](update-all-agents-comms.md).

## Queue inspection

**Win:**

```powershell
python bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py pulse-gate `
  --seen-file $env:USERPROFILE\.openclaw\state\lan_peer\last_pulse_seen.json
python bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py next coder
```

**Mac:**

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py pulse-gate \
  --seen-file ~/.openclaw/state/lan_peer/last_pulse_seen.json
python3 bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py next orchestrator
```

`pulse-gate` returns `status: idle|actionable`, `pick`, `reason`, `new_files`.
Call `pulse-gate` before dispatch; `next <role>` only when actionable.

## Discover script

`scripts/discover.py` re-probes by default; `--cached` skips freshness checks.
`$MAC_IP` unreachable → falls back to cached IP with warning.
`$MAC_IP` unset → last-known-good cached Mac IP.

## Coord pulse notes

| Platform | Script | Notes |
|----------|--------|-------|
| Windows | `coord_pulse.ps1` | Honors `coord_pulse_pause.json`; schedules 5m follow-up on dispatch |
| Mac/Linux | `coord_pulse.sh` | 15m baseline; `--watch` optional |

Both: probe → `should-retry` / `record-success` / `record-failure` → flush outbox.

Full plan: [`coord-pulse-plan.md`](coord-pulse-plan.md).

## Mac inference constraints

- Mac primary inference: Ollama `localhost:11434` — not Win LM Studio port.
- Mac runs one model/service at a time for latency-sensitive work.
- **LAN mirror:** `/v1/models` on Mac/Win may return byte-identical inventories — do not
  infer physical GPU identity from model lists; use discovery `hw_identity` or process inspection.

## Control-plane authentication

- Token files: `orama-system/.state/control_plane_token` and `Perpetua-Tools/.state/control_plane_token`
- Env: `ORAMA_CONTROL_PLANE_TOKEN`, `PT_CONTROL_PLANE_TOKEN` (same secret on both hosts)
- Start: `start.ps1 --lan-peer --no-open` (Win) / `start.sh --lan-peer` (Mac)
- Local probe: bearer `GET /peer-inbox` on `localhost:8002` — expect non-401

## Mac-side idle prompt

When Mac queue is idle, drop `ops/next-actions` to Win inbox to prompt Mac originations.
Confirm `source: mac` / `assignee: win` in `lan_peer_assign.py list`.
