# Fleet: pre–PR #222 backup runbook (3-node LAN)

**Fan-out:** coord-032  
**Status:** ACTIVE — operator action required before orama #222 merge  
**From:** mac-orchestrator (OpenClaw references sync)  
**Date:** 2026-07-27

## Audience

| Lane | Action |
|------|--------|
| `mac-orchestrator` | Run Phase A backup + mesh verify on Mac; unify gossip secret; fan out to Win |
| `win-cursor` | Read runbook; ensure both Windows GPU nodes backed up before #222 |
| `win-coder` / `win-autoresearcher` | No code job — informational |
| `hermes` | `hermes backup` on Win before #222; `-RunDoctor` smoke |

## What landed

- Combined operator runbook (PT mesh memory + ladder SSoT + conflict resolutions)
- Saved: `$OPENCLAW_ROOT/references/2026-07-27-pre-pr222-operator-backup-runbook.md`

## Action required (all 3 machines from `main`)

Sync `main` on each repo — **clean tree required**. Full protocol: [`safe-cross-host-sync-reference-card.md`](../../../git-history-surgery/references/safe-cross-host-sync-reference-card.md) § Quick sync (clean worktree).

```bash
git fetch origin --prune
test -z "$(git status --porcelain --untracked-files=all)" || { echo "error: dirty worktree"; exit 1; }
git switch main
git pull --ff-only origin main
```

1. Run the sync block above (orama-system, then Perpetua-Tools on Mac)
2. `python3 scripts/mesh/lan_topology_archive.py --backup --ref origin/main`  
   Windows: `.\.venv\Scripts\python.exe scripts\mesh\lan_topology_archive.py --backup --ref origin/main`
3. `python3 scripts/mesh/ensure_local_mesh_secrets.py`  
   Windows: `.\.venv\Scripts\python.exe scripts\mesh\ensure_local_mesh_secrets.py`
4. **One shared** `GOSSIP_SHARED_SECRET` on Mac + both Windows GPU nodes — distribute via dedicated air-gapped transfer (e.g. TailsOS-hardened USB or operator-approved secure channel). **Never** use git, email, Slack, or agent comms for secret transport. `ensure_local_mesh_secrets.py` writes repo-local gitignored env files without printing the value — agents must not echo secrets in PRs or logs
5. Verify mesh (discover, gossip, LMS probes) **before** merging #222
6. Win: `hermes backup` → optional `install-hermes-harness.ps1 -RunDoctor`

## Canonical SSoT

- Ladder: `orama-system/docs/v2/50-mesh-security-migration-ladder.md` (Phase A–D)
- OpenClaw workspace: `$OPENCLAW_ROOT/references/2026-07-27-pre-pr222-operator-backup-runbook.md`

## Open / deferred

- Merge orama #222 only after Steps 2–5 green on **every** node
- Phase D strict cutover deferred to v2 launch
