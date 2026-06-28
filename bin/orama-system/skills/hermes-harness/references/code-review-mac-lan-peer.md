# Mac code review assignment

**Assignee:** mac  
**Topic:** code-review/lan-peer-stack  
**Fan-out:** 2026-06-28-code-sections-001

## Files (orama-system)

| Path | Focus |
|------|-------|
| `src/orama_system/lan_peer_files.py` | Inbox sanitization, meta sidecars |
| `src/orama_system/lan_peer_channel.py` | WS/SSE transport, heartbeat only |
| `bin/.../scripts/lan_peer_assign.py` | CLI fan-out, peer HTTP drops |
| `bin/.../scripts/probe_lan_peer.py` | Probe matrix, auth candidates |

## Deliverable

`mac-code-review.md` — bugs, test gaps, LESSONS candidates. Drop to Win peer inbox when done.
