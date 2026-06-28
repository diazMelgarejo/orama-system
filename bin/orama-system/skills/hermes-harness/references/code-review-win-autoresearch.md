# Win code review assignment

**Assignee:** win  
**Topic:** code-review/autoresearch-bridge  
**Fan-out:** 2026-06-28-code-sections-001

## Files (Perpetua-Tools)

| Path | Focus |
|------|-------|
| `orchestrator/autoresearch_bridge.py` | GPU preflight, swarm state, sync |
| `orchestrator/control_plane.py` | autoresearch preflight routes |
| `config/routing.yml` | autoresearch agent routes, affinity |
| `tests/test_autoresearch_bridge.py` | Coverage gaps for LAN peer handoff |

## Deliverable

`win-code-review.md` — GPU runtime issues, routing bugs, PT memory landmark (no secrets). Drop to Mac peer inbox.

## Cross-read

After Mac drops `hypothesis-summary.md`, read it before benchmarking:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py read --peer --name hypothesis-summary.md
```
