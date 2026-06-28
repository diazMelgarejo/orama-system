# Mac code review — LAN peer stack

**Fan-out:** 2026-06-28-code-sections-001  
**Reviewer:** mac-researcher

## Findings

### Fixed this session (9f89051)

| Issue | Fix |
|-------|-----|
| `parents[5]` repo root | `parents[4]` — local inbox import worked |
| `--peer` after subcommand | `peer_p` parent parser on subcommands |
| Fan-out abort on peer 404 | Partial success + exit 1 |

### Open gaps

1. **`ws-peer` SKIP on Win** — file inbox works; WS heartbeat path still needs Win `git pull` + `--lan-peer` restart.
2. **No probe check for `/api/peer-file`** — add optional `peer-file` check to `probe_lan_peer.py` (404 vs 401 vs 200).
3. **Manifest paths relative to cwd** — document "run from `$ORAMA_SYSTEM_PATH`" in fan-out manifests.
4. **Tests** — `lan_peer_assign.py` has no unit tests; `test_lan_peer_files.py` covers inbox only.

## LESSONS candidates (pending user approval)

- File inbox = primary coordination wire for autoresearch fan-out
- Co-orchestration = split topics + markdown handoff; agents stay local per host
