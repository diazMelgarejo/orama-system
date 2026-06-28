# Win doc-sync — peer-inbox portal ACK

**Branch:** `subagent/win-orchestrator/doc-sync-peer-inbox`  
**Inbox read:** `win-self-improve-runtime.md` (local)  
**Status:** DONE — stale portal references updated

## Updated files

| File | Change |
|------|--------|
| `bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md` | Win portal URL → `http://localhost:8002/peer-inbox`; code ref → `platform/windows/peer_inbox_portal.py`; note legacy `/co-orchestration/windows` 307 redirect |
| `platform/macos/README.md` | Removed deleted `co_orchestration_windows.py`; Win lane → `/peer-inbox` + `platform/windows/peer_inbox_portal.py` |

## Not touched

- `docs/LESSONS.md` (operator approve gate)

## Canonical URLs

| Host | URL |
|------|-----|
| Mac | `http://localhost:8002/co-orchestration/macos` |
| Win | `http://localhost:8002/peer-inbox` |
