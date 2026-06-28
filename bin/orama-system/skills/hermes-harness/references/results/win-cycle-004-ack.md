# Win co-orchestrator — cycle 004 ACK

**Fan-out:** `2026-06-28-coord-004`  
**Status:** ACCEPTED — sequential job queues active  
**Mesh:** assume green (pull + `probe_lan_peer.py` after restart)

## Completed (sequential)

| Role | Job | Deliverable |
|------|-----|-------------|
| autoresearcher | `win-autoresearcher-h5-cross-frugal.md` | `gpu-results-h5-cross.md` |
| coder | `win-coder-frugal-spawn.md` | `win-frugal-spawn-policy.md` |

## Queue

`win_job_queue.py` — one active job per role (`autoresearcher`, `coder`).  
State: `~/.openclaw/state/lan_peer/win_job_queue.json`

## Mac pending

- `mac-h5-comparison.md` (Ollama 9B H5 leg)
- PR review: `subagent/win-coder/bridge-http-local` (PT)

**Monitor Win:** http://192.168.254.100:8002/peer-inbox
