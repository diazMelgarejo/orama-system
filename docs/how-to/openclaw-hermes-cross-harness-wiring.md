# OpenClaw ↔ Hermes Cross-Harness Wiring

> **What this is:** How Mac OpenClaw (Ollama primary) talks to Hermes Harness on Windows.  
> **Audience:** OpenClaw on Mac, cursor-agent on Mac or Win, Claude Code in this repo.  
> **Canonical sources:** [`hermes-harness/SKILL.md`](../../bin/orama-system/skills/hermes-harness/SKILL.md) · [`mac-co-orchestrator-playbook.md`](../../bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md) · [`lan-endpoint-contract.md`](../../bin/orama-system/skills/hermes-harness/references/lan-endpoint-contract.md)

---

## 1. System Topology

```
Mac (this machine)                          Windows (192.168.254.100)
─────────────────────                       ──────────────────────────
OpenClaw gateway :18789                     OpenClaw gateway :18789
  primary: ollama/qwen3.5:9b-nvfp4          primary: lmstudio/qwen3.5-27B
  (localhost:11434)                         (localhost:1234)
                                            Hermes Agent (venv launcher)
orama-system portal :8002   ←──LAN──→      orama-system portal :8002
  /co-orchestration/macos                     /co-orchestration/windows
  /api/peer-file  (file inbox server)         /api/peer-file

Mac inference role: Ollama researcher       Win inference role: LM Studio 27B coder
Mac coder: cursor-agent / Codex CLI         Win coder: Hermes + Codex CLI
```

**INVARIANT:** Win IP is DHCP-dynamic. Always read from `~/.openclaw/state/last_discovery.json → endpoints.win.ip`. Never hardcode.

---

## 2. Verify the LAN Peer (run before dispatching anything)

```bash
cd "$ORAMA_SYSTEM_PATH"    # orama-system root

python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

**Pass criteria:**

| Check | Expected | Meaning |
|-------|----------|---------|
| `portal-health` | PASS | Win orama portal `:8002` is up |
| `peer-lmstudio` | PASS | Win LM Studio `:1234` is serving models |
| `portal-status` | PASS or SKIP | SKIP = gateway-auth-token not in Keychain yet (non-blocking for file-inbox mode) |
| `ws-peer` | PASS or SKIP | Same as above |

**Current state (2026-06-28):** `portal-health` ✅ · `peer-lmstudio` ✅ · status/ws SKIP (add `openclaw.gateway-auth-token` to Keychain to upgrade to PASS).

Quick manual check:

```bash
WIN_IP=$(python3 -c "import json; d=json.load(open('$HOME/.openclaw/state/last_discovery.json')); print(d['endpoints']['win']['ip'])")
curl -s --max-time 5 "http://${WIN_IP}:1234/v1/models" | python3 -c "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])"
```

---

## 3. How OpenClaw Dispatches Work to Win (file-inbox transport)

OpenClaw uses a **file-inbox** system — no direct RPC. Mac posts JSON/Markdown files to Win's inbox via the peer portal; Win picks them up, runs the task, drops the result back.

### 3a. Fan-out (Mac → Win)

```bash
# Create a fan-out manifest (see autoresearch-fanout-example.json for format)
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/autoresearch-fanout-example.json

# Mac keeps mac-* files locally; win-* files POST to http://${WIN_IP}:8002/api/peer-file
```

### 3b. Drop a single file to Win inbox

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop --peer \
  --file /tmp/my-task.md \
  --assignee win \
  --topic autoresearch/gpu-run \
  --fanout-id 2026-06-29-001
```

### 3c. Read Win's reply

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --peer \
  --name gpu-results-h6.md
```

### 3d. Portal inbox UI (both hosts)

| Host | URL |
|------|-----|
| Mac | `http://localhost:8002/co-orchestration/macos` |
| Win | `http://localhost:8002/co-orchestration/windows` |
| Either | `http://localhost:8002/co-orchestration` (auto-skin) |

---

## 4. How Hermes on Win Receives and Executes

On Windows, Hermes is the operator shell. When a file arrives in Win's inbox:

```powershell
# PATH setup (run once per session or add to PowerShell profile)
$hermesScripts = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts"
$env:PATH = "$hermesScripts;$env:PATH"

# Git Bash path (for Hermes terminal tools)
$env:HERMES_GIT_BASH_PATH = (Get-ChildItem "$env:LOCALAPPDATA\GitHubDesktop\app-*\resources\app\git\usr\bin\bash.exe" |
  Sort-Object FullName -Descending | Select-Object -First 1).FullName

# Canary check
hermes chat --query "Reply with exactly: HERMES_READY" --quiet --safe-mode `
  --provider nous --model stepfun/step-3.7-flash:free --max-turns 1
```

Hermes runs orama canonical skills via thin wrapper commands installed in `~/.hermes/skills/`:

| Wrapper | Points to |
|---------|-----------|
| `/pt-orama-council` | `bin/orama-system/skills/hermes-harness/commands/pt-orama-council.md` |
| `/pt-orama-review`  | `bin/orama-system/skills/hermes-harness/commands/pt-orama-review.md` |
| `/pt-orama-delegate`| `bin/orama-system/skills/hermes-harness/commands/pt-orama-delegate.md` |

Install/verify wrappers:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
hermes skills list --source local
```

---

## 5. Model Routing (MAC vs WIN)

**Never cross-list models.** Hardware affinity is enforced by `start.sh --hardware-policy`.

| Role | Mac | Windows |
|------|-----|---------|
| Researcher / inference | `ollama/qwen3.5:9b-nvfp4` (localhost:11434) | `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` (localhost:1234) |
| Embeddings | `bge-m3` via Ollama | `text-embedding-qwen3-embedding-8b` via LM Studio |
| Coder | `cursor-agent` or Codex CLI | Hermes + Codex CLI |
| Cross-peer dispatch | `lan_peer_assign.py drop --peer` | `lan_peer_assign.py drop --peer` |

LM Studio on any machine loads **one model at a time**. Use different machine IPs for parallel model use.

---

## 6. Benchmarking Mac Ollama vs Win 27B

Trigger via researcher queue (file-inbox pattern):

```bash
# Mac side — assign benchmark task to both
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/pulse-unified-comparison.md
```

Compare results in `gpu-results-h5-final.md` and `mac-h5-comparison.md` (canonical priors for H6).

**Benchmark criteria (H5/H6):**

| Metric | Mac 9B baseline | Win 27B target |
|--------|-----------------|----------------|
| Iterations-to-pass | baseline | < Mac 9B |
| Wall-clock | baseline | < 1.5× Mac |
| Quality | smoke rubric pass | smoke rubric pass |

---

## 7. Running H6 Real Task (unblocked 2026-06-28)

**Task card:** [`references/results/mac-hypothesis-h6-real-task.md`](../../bin/orama-system/skills/hermes-harness/references/results/mac-hypothesis-h6-real-task.md)

**Branch:** `subagent/win-autoresearcher/researcher-backlog-h6`

**Trigger (from Mac, once portal-health + peer-lmstudio are PASS):**

```bash
cd "$ORAMA_SYSTEM_PATH"

# Verify peer is up
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json

# Fan-out H6 to Win GPU autoresearcher
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop --peer \
  --file bin/orama-system/skills/hermes-harness/references/results/mac-hypothesis-h6-real-task.md \
  --assignee win \
  --topic autoresearch/gpu-run \
  --fanout-id 2026-06-29-coord-021-h6

# Win reads and executes — drops gpu-results-h6.md in Mac inbox when done
# Mac reads result:
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --peer \
  --name gpu-results-h6.md
```

**Win executes on branch** `subagent/win-autoresearcher/researcher-backlog-h6`:

1. Wait for H5-final canonical results (already in `gpu-results-h5-final.md`).
2. Run a single LM Studio 27B pass via PT `autoresearch_bridge` on the agreed real prompt class.
3. Drop `gpu-results-h6.md` with: iterations, wall-clock, rubric pass/fail, comparison to Mac 9B baseline.

---

## 8. OpenClaw Self-Knowledge (add to openclaw.json if missing)

OpenClaw's cross-harness awareness comes from `openclaw.json` agents config. To add a named Win Hermes worker:

```json
{
  "agents": {
    "win-researcher": {
      "description": "Win LM Studio 27B autoresearcher — dispatch via LAN peer file inbox",
      "model": { "primary": "lmstudio-win/qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2" },
      "transport": "lan-peer-file-inbox",
      "peer_ip_source": "~/.openclaw/state/last_discovery.json#endpoints.win.ip"
    },
    "win-coder": {
      "description": "Win Hermes + Codex CLI bounded coder",
      "model": { "primary": "lmstudio-win/gemma-4-26b-a4b-it" },
      "transport": "lan-peer-file-inbox"
    }
  }
}
```

**Cross-harness dispatch envelope (L2):**

```json
{
  "skill_id": "pt-orama-council",
  "args": { "task": "run H6 autoresearch benchmark" },
  "agent_id": "openclaw",
  "executor_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "transport": { "partner": "hermes", "profile": "bounded" }
}
```

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `portal-health` FAIL | Win orama portal not running — run `start.sh` on Win or `start.ps1` |
| `peer-lmstudio` FAIL | LM Studio not loaded on Win — open LM Studio, load a model |
| `portal-status` SKIP | `openclaw.gateway-auth-token` not in Keychain — store it with `store_keychain_secret.sh` |
| Hermes `command not found` | Run PATH setup block in §4 |
| LM Studio "Operation canceled" | Only one model loads at a time — unload current model first |
| `ws-peer` SKIP | Same as portal-status — gateway-auth-token missing |

---

## 11. Persistent Pulse Cadence (Mac Orchestrator)

The Mac OpenClaw orchestrator runs as a persistent `openclaw cron` job, not a
manual loop. It survives gateway restarts (the job lives in `openclaw.json`'s
`.cron.jobs`, which is durable config, not ephemeral state).

**Base heartbeat — every 15 minutes:**

```bash
openclaw cron add --name "mac-orchestrator-pulse" --agent orchestrator \
  --every "15m" --session isolated --light-context --timeout-seconds 600 \
  --message "<pulse logic: probe peer, check queue, dispatch if idle+queued>"
```

**Fast loop while busy — self-reschedules to +5 minutes:**

After a successful dispatch, the pulse schedules a one-shot follow-up instead
of waiting for the next 15m tick:

```bash
openclaw cron add --name "mac-orchestrator-pulse-followup" --agent orchestrator \
  --at "+5m" --session isolated --light-context --message "<same pulse logic>"
```

If the follow-up also dispatches, it re-arms its own `+5m` follow-up — the
chain continues as long as work keeps flowing. The first idle check (nothing
queued) lets the chain end naturally; the base 15m heartbeat picks the slack
back up. This gives fast iteration under load without polling every 15m when
there's nothing to do.

**Editing the job:**

```bash
openclaw cron list                                    # see current schedule/status
openclaw cron edit <job-id> --message "<new prompt>"   # patch the pulse logic
openclaw cron get <job-id> --json                      # inspect full job JSON
```

**Do not hand-edit `openclaw.json`'s `.cron.jobs` via `jq`.** The real schema
(`schedule.kind`/`everyMs`, `payload.kind: agentTurn`, etc.) differs from what
a naive `{id, agentId, schedule:{type,value}, prompt}` shape might suggest —
an invalid shape passes `jq` cleanly but fails `openclaw config validate` and
takes the live gateway down silently (launchd shows `running` while the
process has actually exited). Always use the `openclaw cron` CLI.

**Failure handling:** retry a failing dispatch up to 10x with exponential
backoff (~5min cap total), then log a FAILURE summary (timestamp, error,
retry count, log path) to `Perpetua-Tools/.agent/memory/working/REVIEW_QUEUE.md`
and stop — never schedule a follow-up on failure, never let an error crash
the pulse job or the gateway itself.

**Verifying it's alive:**

```bash
openclaw status | grep -i gateway     # confirm gateway reachable + LaunchAgent running
openclaw cron list                    # confirm job enabled, check "Next" countdown
```

## 12. Key File Locations

| File | Purpose |
|------|---------|
| `~/.openclaw/state/last_discovery.json` | Win IP source of truth |
| `~/.openclaw/state/last_lan_peer_probe.json` | Last probe result |
| `~/.openclaw/state/lan_peer/inbox/` | Mac inbox (Win-sent files land here) |
| `bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py` | LAN peer verifier |
| `bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py` | Fan-out / drop / read |
| `bin/orama-system/skills/hermes-harness/scripts/verify_partner_canaries.py` | Win canary check |
| `platform/windows/ensure-partner-cli-paths.ps1` | Win PATH setup for Codex + Hermes |
| `docs/wiki/15-hermes-windows-harness.md` | Win Hermes install + PATH root cause |
