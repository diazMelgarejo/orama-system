# Win frugal spawn policy — Hermes / cursor-agent / Codex

**Fan-out:** `2026-06-28-coord-004`  
**Author:** win-coder (Hermes)  
**Topic:** code-review/bridge-merge  
**Branch:** `subagent/win-coder/bridge-http-local` (Perpetua-Tools) — PR to `main` pending operator review

## Spawn ladder (Win host)

```text
1. LM Studio 27B @ localhost:1234     — primary coder / autoresearcher / Hermes local
2. Win Ollama @ localhost:11434       — critic / fallback (if configured)
3. lan_peer_assign drop --peer        — ask Mac Ollama for latency-sensitive leg
4. Codex / cursor-agent cloud         — only when local GPU busy or task needs cloud
5. Perplexity / paid tiers            — budget guard; never when BUDGET_GUARD exceeded
```

Aligns with `graceful-degradation.md` ladders B + E.

## autoresearch_bridge preflight (verified)

| Setting | Expected on Win GPU host |
|---------|--------------------------|
| `AUTORESEARCH_PREFLIGHT_MODE` | `auto` or `http-local` |
| `preflight_mode` in result | `http-local` |
| `gpu_local` | `true` |
| `lm_studio_ok` | `true` when LMS up |

SSH path preserved for Mac→Win remote; local Win must not block on SSH timeout.

## Hermes / cursor-agent rules

- **One GPU model at a time** — serialize via `win_job_queue.py` (autoresearcher + coder queues).
- **cursor-agent** — prefer `--model composer-2.5` or local-equivalent before cloud.
- **codex exec** — fanout profile only when LM Studio slot free; see `codex-cli-v142-dispatch.md`.

## PR action (operator)

```powershell
cd $env:PERPETUA_TOOLS_PATH
gh pr create --head subagent/win-coder/bridge-http-local --base main `
  --title "feat(autoresearch): HTTP-local preflight on Win GPU host" `
  --body "Coord-003 spike; 38 tests pass."
```

## Queue

Processed via `win_job_queue.py` — coder role, priority 2 (after autoresearcher LM Studio pass).
