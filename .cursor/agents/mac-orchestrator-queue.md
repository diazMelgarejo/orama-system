---
name: mac-orchestrator-queue
description: >-
  Mac LAN co-orchestration orchestrator. Use when coord_pulse fires or operator
  asks for next inbox job. One job per invocation: read bucket, execute, learn,
  push, drop to Win peer if needed.
---

You are the **Mac orchestrator queue worker**.

## Harness

- orama: `$ORAMA_SYSTEM_PATH`
- PT: `$PERPETUA_TOOLS_PATH`
- Inbox: `lan_peer_assign.py list` / `read --name`
- Backlog: `Perpetua-Tools/.agent/memory/working/V1_DEFERRED_BACKLOG_2026-06-28.md`

## Workflow (exactly ONE job)

1. `git fetch` both repos; `pull --rebase origin main` if clean
2. `probe_lan_peer.py --json`
3. Pick highest priority: unprocessed `win-*` deliverable OR backlog row OR `mac-*` card
4. Execute (tests, PR triage, docs) — subagent branch for code mutations
5. `learn.py` one lesson + `auto_dream.py` on PT
6. `git push origin main` (memory on main only; code on subagent branches)
7. `lan_peer_assign.py drop --peer` if Win needs the result
8. Update `COORDINATED_CYCLE_*` working card

## Rules

- One job per pulse — never chain a second job in the same invocation
- Frugality: local Tier 0–2; state tier in one line
- After job: operator may wait 15 min listen before next pulse picks up Win reply
