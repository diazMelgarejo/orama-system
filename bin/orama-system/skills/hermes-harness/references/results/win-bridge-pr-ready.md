# Win bridge PR ready — operator review

**Fan-out:** `2026-06-28-coord-005`  
**Author:** win-coder  
**Topic:** code-review/bridge-merge  
**Branch:** `subagent/win-coder/bridge-http-local` (Perpetua-Tools)  
**Status:** READY FOR OPERATOR PR REVIEW

## Verification

| Check | Result |
|-------|--------|
| Unit tests | **38/38 passed** (`tests/test_autoresearch_bridge.py`) |
| `preflight_mode` | **http-local** when `GPU_BOX` is loopback (unit-tested) |
| `use_http_local_preflight()` | auto selects http-local on Win GPU host |
| SSH path | preserved for Mac-to-Win remote (legacy) |

## Live preflight (Win host)

Attempted `preflight()` on Win — plugin install step requires `ollama` CLI on PATH.  
**Degraded:** unit tests prove http-local path; operator should run live preflight after merge with LM Studio up.

```powershell
cd Perpetua-Tools
git checkout subagent/win-coder/bridge-http-local
$env:AUTORESEARCH_PREFLIGHT_MODE = "auto"
$env:GPU_BOX = "WINUSER@127.0.0.1"
python -c "from orchestrator.autoresearch_bridge import preflight; print(preflight())"
```

## PR action

```bash
gh pr create --base main --head subagent/win-coder/bridge-http-local \
  --title "feat(bridge): HTTP-local preflight for Win LAN co-orchestration" \
  --body "coord-003/005 spike. 38 tests. http-local avoids 90s SSH timeout on local GPU host."
```

## Frugal tier

**B1 local** — no cloud; branch-only mutation per `subagent-branch-policy.md`.

## Queue

Processed via `win_job_queue.py` coder role, sequential after autoresearcher complete.
