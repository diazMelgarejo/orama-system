# orama-system — Agent Resume Guide

**Repo:** diazMelgarejo/orama-system
**Branch:** `main`
**Renamed:** ultrathink-system → orama-system (2026-04-20)
**Last updated:** 2026-04-20

## What this repo is
ὅραμα (vision/revelation) — complete agent methodology for solving impossible problems. Hosts: API server (port 8001), multi-agent MCP servers, 5-stage methodology.

## Mandatory on every session
1. Read `.claude/lessons/LESSONS.md` at session start
2. Write discoveries back to `.claude/lessons/LESSONS.md` before Stop
3. Use the 5-stage methodology (`/agent-methodology`) for non-trivial tasks
4. Run `/ecc-sync` after any ECC Tools PR merges

## LM Studio (auto-discovered)
Managed by `~/.openclaw/scripts/discover.py`. Discovery runs at SessionStart.
Fallback: `~/.openclaw/scripts/discover.py --restore profile:mac-only` if Win is down.

## Claude Code automation
- SessionStart: discovers endpoints + syncs instincts
- PostToolUse(*.py): ruff lint
- Stop: checks LESSONS.md was updated this session
- Skills: `/ecc-sync`, `agent-methodology` (Claude-only)
- Subagent: `crystallizer` (stage 1 of methodology)

## Start the API server
```bash
source .env && source .env.lmstudio 2>/dev/null || true
python api_server.py  # port 8001
```

## 5-stage methodology
Crystallize → Architect → Execute → Refine → Verify
Use `/crystallizer` subagent for complex problem crystallization.
