# Update All Agents Comms — Hermes Operator Guide

> **When to use:** Operator says "update all agent comms", "update the board",
> "notify all peers", or you finished work other agents would otherwise rediscover.
> **Role:** Step-by-step recipe — not executable logic.
> **Paths:** env-var form only (LINT-006).

---

## What this is (30 seconds)

We tell **every agent lane** the same story through **two channels**:

| Channel | What it is | Who reads it |
|---------|------------|--------------|
| **GossipBus** | One-line whiteboard log per agent lane | Any session on this machine polling `agent_coordination.py` |
| **Peer inbox** | Markdown file in the portal inbox | Mac orchestrator, Win coder/autoresearcher, coord_pulse workers |

The whiteboard log is the **pointer**. The inbox drop is the **full record**.

---

## Agent lanes (log each one)

Post the **same one-line pointer** to every lane that might care:

| `agent_id` | Harness / role |
|------------|----------------|
| `win-cursor` | Operator Cursor session on Windows |
| `win-coder` | Win coder queue (`win-coder-queue.md`) |
| `win-autoresearcher` | Win GPU/research queue |
| `mac-orchestrator` | Mac coord_pulse / orchestrator |
| `mac-researcher` | Mac research lane |
| `hermes` | Hermes shell / Windows bring-up |

You do **not** need a separate message per lane — same text, six `log` calls.

---

## The recipe (copy-paste order)

### 0. Set paths (every session)

```powershell
$env:ORAMA_SYSTEM_PATH = "<orama-system git root>"
$env:PERPETUA_TOOLS_PATH = "<Perpetua-Tools git root>"
```

Mac/Linux: use `export` instead of `$env:`.

### 1. Write the inbox document

Create a file under:

`bin/orama-system/skills/hermes-harness/references/results/`

**Naming:** `<host>-<YYYY-MM-DD>-<short-topic>.md`  
Examples: `win-2026-07-23-crg-platform-skills-broadcast.md`

**Minimum sections:**

```markdown
# Short title

**Fan-out:** coord-NNN          ← increment from last coord cycle
**Status:** ACTIVE | DONE | OPERATOR RULE
**From:** win-cursor | mac-orchestrator | hermes
**Date:** YYYY-MM-DD

## Audience
| Lane | Action |
|------|--------|
| win-coder | … |
| mac-orchestrator | … |

## What landed
(bullets or table)

## Action required
(per platform or per lane)

## Open / deferred
(optional)
```

Worked examples in the same folder:
- `mac-2026-07-22-frugality-p3-and-repo-closeout-status.md`
- `win-2026-07-23-crg-platform-skills-broadcast.md`

### 2. Fan out to Win + Mac inboxes

**Preferred — one command, both hosts:**

Create a manifest next to your drop file, e.g. `coord-NNN-fanout.json`:

```json
{
  "fanout_id": "coord-026",
  "assignments": [
    {
      "assignee": "win",
      "topic": "dev-reference/my-topic",
      "filename": "win-2026-07-23-my-topic.md",
      "path": "bin/orama-system/skills/hermes-harness/references/results/win-2026-07-23-my-topic.md"
    },
    {
      "assignee": "mac",
      "topic": "dev-reference/my-topic",
      "filename": "win-2026-07-23-my-topic.md",
      "path": "bin/orama-system/skills/hermes-harness/references/results/win-2026-07-23-my-topic.md"
    }
  ]
}
```

Run from orama-system root:

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py fanout `
  --manifest bin\orama-system\skills\hermes-harness\references\results\coord-026-fanout.json
```

- `assignee: win` → **local** Win inbox (this machine's portal)
- `assignee: mac` → **peer** Mac inbox (HTTP to discovered peer IP)

**Single drop (when only one host needs it):**

```powershell
# To Mac peer only
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop `
  --peer --file bin\orama-system\skills\hermes-harness\references\results\win-2026-07-23-my-topic.md `
  --assignee mac --topic dev-reference/my-topic --fanout-id coord-026

# To local Win inbox only
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop `
  --file bin\orama-system\skills\hermes-harness\references\results\win-2026-07-23-my-topic.md `
  --assignee win --topic dev-reference/my-topic --fanout-id coord-026
```

### 3. Post GossipBus whiteboard logs

One line per agent lane. Include: coord id, what landed, inbox filename, SSoT path if any.

```powershell
$msg = "coord-026 ALL AGENTS: <one sentence>. Read win-2026-07-23-my-topic.md (win+mac inboxes). SSoT: <path-if-any>"
foreach ($a in @("win-cursor","win-coder","win-autoresearcher","mac-orchestrator","mac-researcher","hermes")) {
  python $env:PERPETUA_TOOLS_PATH\scripts\agent_coordination.py log $a $msg
}
```

Mac/Linux:

```bash
MSG='coord-026 ALL AGENTS: …'
for a in win-cursor win-coder win-autoresearcher mac-orchestrator mac-researcher hermes; do
  python3 "$PERPETUA_TOOLS_PATH/scripts/agent_coordination.py" log "$a" "$MSG"
done
```

### 4. Pulse heartbeat (poster only)

Keeps **your** lane from showing STALLED while peers read the board:

```powershell
python $env:PERPETUA_TOOLS_PATH\scripts\agent_coordination.py heartbeat pulse win-cursor
```

Use your real `agent_id` (`mac-orchestrator` on Mac, etc.).

### 5. Optional — run coord_pulse once

Picks up new inbox files and may dispatch queued jobs:

```powershell
powershell -File $env:ORAMA_SYSTEM_PATH\bin\orama-system\skills\hermes-harness\scripts\coord_pulse.ps1
```

Mac: `bash bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh`

### 6. Optional — 5-minute recurring comms board heartbeat

Do NOT hardwire a loop into `start.ps1`; keep it as a local harness call.
Use the bundled thin wrapper instead so any fresh clone can run it:

```powershell
powershell -File $env:ORAMA_SYSTEM_PATH\bin\orama-system\skills\hermes-harness\scripts\coord_comms_board.ps1 -Minutes 5 -Json
```

What it checks in one tick:
- peer probe via `probe_lan_peer.py`
- coordination board timestamp + hearbeat/pulse health
- `coord_pulse.ps1`/`coord_monitor.ps1` availability
- peer inbox listing via `lan_peer_assign.py list`
- `agent_coordination.py heartbeat pulse <lane>`
- local comms-state dump to stdout or `-Json`

Schedule pattern (Windows Task Scheduler example):

```powershell
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File {0} -Minutes 5 -Json' -f $env:ORAMA_SYSTEM_PATH
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)
Register-ScheduledTask -TaskName 'OramaCoordCommsBoard' -Action $action -Trigger $trigger -Description 'Replay around full enchilada: agent_coordination.py board, whiteboard, peer inbox, GossipBus, pulse' -Force
```

Mac equivalent: same script cannot run directly; use `launchd` to run `coord_pulse.sh` plus a small shell wrapper that imports `agent_coordination.py` health/stats.

---

## Checklist (before you say "done")

- [ ] Inbox `.md` written under `references/results/`
- [ ] Fanout delivered **win** (local) + **mac** (peer) — or explicit single drop
- [ ] GossipBus `log` posted for all six agent lanes
- [ ] `heartbeat pulse` for the posting agent
- [ ] No absolute workstation paths in the drop body (LINT-006)

---

## How agents consume it

| Agent | How it learns |
|-------|----------------|
| **coord_pulse** | Scans inbox `new_files`; may enqueue `win-coder-*` jobs |
| **win-coder / win-autoresearcher** | `lan_peer_assign.py list` → `read --name <file>` |
| **mac-orchestrator** | Peer inbox on Mac portal; GossipBus tail |
| **Hermes one-shot** | Thin wrapper loads this file when operator triggers board update |

Agents should **read the inbox file**, not rely on GossipBus alone.

---

## Limits (know these)

| Topic | Rule |
|-------|------|
| **GossipBus scope** | Intra-machine only — not shared across separate Win boxes |
| **Peer inbox** | Mac ↔ Win via portal HTTP; peer IP from `last_discovery.json` — never hardcode |
| **Remote Win sibling** | Not in peer discovery? Needs its own drop or operator handoff |
| **Job queue** | Informational broadcasts do **not** need `win_job_queue.py enqueue` unless you want a coder job |
| **Path hygiene** | Use `$env:ORAMA_SYSTEM_PATH` / `$env:PERPETUA_TOOLS_PATH` in commands; sanitize paths in markdown |

---

## Real example (coord-026, CRG platform rule)

1. Wrote `win-2026-07-23-crg-platform-skills-broadcast.md`
2. Fanout manifest `coord-026-crg-fanout.json` → win local + mac peer ✓
3. Six GossipBus logs + `heartbeat pulse win-cursor` ✓
4. `coord_pulse.ps1` — gate idle, file visible in `new_files`

---

## Related

- [`../SKILL.md`](../SKILL.md) § Update the Board — trigger phrases
- [`lan-peer-self-talk.md`](lan-peer-self-talk.md) — Mac↔Win portal setup
- [`windows-hermes-setup.md`](windows-hermes-setup.md) § Agent Comms — command table
- [`coord-pulse-plan.md`](coord-pulse-plan.md) — pulse schedule and queues
