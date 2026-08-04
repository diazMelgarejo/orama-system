# Hermes dispatch taxonomy (orama canonical)

> **Purpose:** Stop conflating three unrelated dispatch lanes. Every hermes-harness
> skill, `bin/agents/` staging row, and graft decision must tag its lane.
> **Evidence:** Windows fleet results (2026-06-29 through 2026-07-27), PT
> `hermes_harness.py`, NousResearch `delegate_tool.py`, coord_pulse.ps1 live
> trace (2026-08-03 gbrain refresh).

## Three lanes (never merge in prose)

| Lane | ID | What actually runs | Parent sees | orama examples |
| ---- | -- | -------------------- | ----------- | -------------- |
| **Native Hermes children** | `L-H1` | `delegate_task` tool → child `AIAgent` in-process | Delegation call + **final summary only** | Interactive Hermes session; kanban worker lanes; `SubagentLaunchRequest` plugins |
| **PT script workers** | `L-PT` | `spawn_hermes_agent()` → new top-level `AIAgent(...).chat()` | Full stdout / JSON from each stage | `hermes_harness.py`, `hermes-orama`, `hermes-delegate` (ThreadPool) |
| **Fleet cursor-agent jobs** | `L-Fleet` | `coord_pulse` → `win_job_queue` → `cursor-agent --print` | Log lines in `coord-pulse.log` | Win coder/autoresearcher queues; `subagent/win-*` **git branches** |

### L-H1 — Native Hermes (`delegate_task`)

- Source: NousResearch `tools/delegate_tool.py`
- Child gets: fresh conversation, own `task_id`, inherited toolsets minus blocklist
  (`delegate_task`, `clarify`, `memory`, `send_message`, `cronjob`)
- Orchestrator children **wait** for their workers before returning
- **NOT** used by PT `hermes_harness.py` or orama `hermes-delegate` today

### L-PT — PT pipeline script

- Source: `Perpetua-Tools/src/hermes_harness.py`
- Direct `AIAgent` per Orama stage with `ephemeral_system_prompt` (SOUL distillates)
- `hermes-delegate` runs 2–5 parallel `spawn_hermes_agent("executor", …)` — **not**
  `delegate_task`; workers are sibling processes/threads, not Hermes children
- `hermes_spawn.sh` tracks **PT harness PID** (`python* hermes_harness.py`), not
  interactive Hermes CLI

### L-Fleet — Windows/Mac fleet coordination

- Win: `coord_pulse.ps1` (Task Scheduler ~900s) → `probe_lan_peer.py` →
  `win_job_queue.py pulse-gate` → **one** `cursor-agent --print --model composer-2.5`
- Agent cards: `.cursor/agents/win-coder-queue.md`, `win-autoresearcher-queue.md`
- `subagent/<role>/<topic>` branches = **file-inbox + git coordination**, not L-H1
- Mac parity: `coord_pulse.sh` + `mac_job_queue` (cursor-agent on Mac lanes)

## Misconstrual checklist (grep before shipping docs)

| Wrong claim | Correct lane |
| ----------- | ------------ |
| "`hermes-delegate` spawns Hermes subagents" | L-PT parallel `AIAgent` threads |
| "`bin/agents/REGISTRY.yml` is the runtime subagent tree" | Staging for profiles + thin skills |
| "`coord_pulse` dispatches Hermes workers" | L-Fleet cursor-agent |
| "`subagent/win-coder/…` branch = Hermes child" | L-Fleet git coordination |
| "Each worker gets isolated context" (hermes-delegate) | L-PT loads agent context files; not delegate_tool isolation |

## Windows session command catalog (verified)

| Command / script | Lane | When |
| ------------------ | ---- | ---- |
| `platform\windows\install.ps1` | setup | Fresh / re-run bootstrap |
| `install-hermes-harness.ps1` [-RunDoctor] | setup | Profiles + thin wrappers |
| `scripts\install_coord_pulse.ps1` [-Status] | L-Fleet | Schedule 900s pulse |
| `coord_pulse.ps1 -DryRun` | L-Fleet | Operator verify without cursor-agent |
| `hermes backup`, `hermes doctor`, `hermes profile list` | setup | Brain merge / doctor |
| `hermes_spawn.sh start\|stop\|status` | L-PT | PT harness background session |
| `python …/hermes_harness.py` | L-PT | 5-stage pipeline CLI |
| `cursor-agent --print --model composer-2.5` | L-Fleet | coord_pulse enqueue pick |

**Env:** `ORAMA_SYSTEM_PATH`, `PERPETUA_TOOLS_PATH` must reach coord_pulse via
**User-level env** or explicit export — scheduled tasks do not load `.env.local`.

## Skill doc requirements

Every hermes-harness SKILL that mentions "subagent", "worker", or "delegate" must:

1. Tag lane: `(L-H1)`, `(L-PT)`, or `(L-Fleet)` in the opening paragraph
2. If L-PT, state **NOT `delegate_task`**
3. Link this file for cross-harness readers

## PT memory anchors (plan corrections from Win side)

| Topic | PT working memory / lesson |
| ----- | -------------------------- |
| PR body clobber on Hermes PR | `PR222_HERMES_STAGING_SESSION_2026-07-27.md` |
| discover.py Windows platform | AGENT_LEARNINGS `hermes-harness-review` 2026-06-25 |
| coord_pulse `-LanArgs` | `win-hermes-gateway-review-request-2026-07-08.md` |
| hermes-spawn PID status | `lesson_9581e059df66` |
| Portable brain ≠ staged SOUL | `lesson_3b2e42ac6ee2` |

## Workspace paths (not `$OPENCLAW_ROOT`)

Committed docs use `$REPO_ROOT`, `$ORAMA_SYSTEM_PATH`, `$PERPETUA_TOOLS_ROOT`,
git repo-relative crawl (mother-of-orama + `$HOME`) — never `$OPENCLAW_ROOT` or
`$OPENCLAW_HOME` for discovery defaults.
See [`openclaw-workspace-path-doctrine.md`](openclaw-workspace-path-doctrine.md).

## Graft implications

- **SKIP** grafting OpenClaw `recursive-spawn-protocol` into `hermes-delegate`
  until lane rename (`hermes-pt-parallel` or similar)
- **ADOPT** JSON envelope on shell entrypoints (all lanes)
- **NEW** optional `hermes-native-delegate` command card — documents L-H1 only;
  no PT wrapper pretending to be `delegate_task`
