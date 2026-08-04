# Fleet: GOSSIP secret — Mac ready, Win OOB distribute

**Fan-out:** coord-034  
**Status:** ACTIVE — **secrets stay in 1Password, never in comms**  
**From:** mac-orchestrator  
**Date:** 2026-07-27

## What Mac completed

- `ensure_local_mesh_secrets.py` → `GOSSIP_SHARED_SECRET` present in orama + PT repo-local env policy files
- `.local/mesh-secrets.json` archive on Mac
- `lan_topology_archive.py` backup + apply on `main`

## Audience — action required

| Lane | Action |
|------|--------|
| `mac-orchestrator` | Secret in repo-local env policy file — copy to **1Password** if not already |
| `win-cursor` | Paste **same** `GOSSIP_SHARED_SECRET` from 1Password into 3080 + 5080 repo-local env policy files (orama + PT) |
| `win-coder` / `win-autoresearcher` | After operator paste: `ensure_local_mesh_secrets.py` + `start.ps1` on each Win box |
| `hermes` | No secret in chat; `hermes backup` before #222 |

## OOB distribute (operator — NOT GossipBus)

1. Save Mac orama-system + Perpetua-Tools repo-local env policy files in 1Password (secure note).
2. On **3080**: paste matching `GOSSIP_SHARED_SECRET` → `python scripts\mesh\ensure_local_mesh_secrets.py` → `start.ps1`
3. On **5080**: repeat step 2.
4. Verify mesh — no gossip 403 storm.

**Never:** commit, email, Slack, or `agent_coordination.py log` the secret value.

## SSoT

- [fleet-2026-07-27-pre-pr222-backup-runbook.md](fleet-2026-07-27-pre-pr222-backup-runbook.md)
- Inbox: [fleet-2026-07-27-gossip-unify-mac-first.md](fleet-2026-07-27-gossip-unify-mac-first.md) (coord-033)

## Agent lanes note

GossipBus whiteboard logs are **pointers only**. Mesh peers are **physical machines** (Mac + 3080 + 5080), not SQLite agent IDs.
