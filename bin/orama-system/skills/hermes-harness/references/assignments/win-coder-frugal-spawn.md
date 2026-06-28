# Win coder — merge bridge + frugal spawn policy

**Assignee:** win (coder)  
**Topic:** code-review/bridge-merge  
**Fan-out:** 2026-06-28-coord-004  
**Priority:** 2 — after autoresearcher LM Studio pass

## Task

1. Open PR: `subagent/win-coder/bridge-http-local` → `main` (do not force-push).
2. Verify `preflight()` reports `http-local` on Win GPU host.
3. Document spawn policy: Hermes/cursor-agent uses LM Studio before Codex/online.
4. Drop `win-frugal-spawn-policy.md` to Mac peer.

## Reference

`graceful-degradation.md` ladder B4 + E.
