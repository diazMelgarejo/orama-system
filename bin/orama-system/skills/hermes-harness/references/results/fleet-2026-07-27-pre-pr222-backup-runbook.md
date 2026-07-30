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
3. `python3 scripts/mesh/ensure_local_mesh_secrets.py` (Mac only — establishes canonical `GOSSIP_SHARED_SECRET`)
4. Transfer the Mac `GOSSIP_SHARED_SECRET` to each Windows node via **air-gapped medium only** (e.g. TailsOS-hardened USB). **Never** use git, email, Slack, or agent comms for secret transport.
5. On **each** Windows node (required when fleet includes Windows peers):
   1. Write `GOSSIP_SHARED_SECRET` into the repo-local gitignored env file via offline editor (avoid command-line entry — shell history).
   2. **Archive/quarantine stale JSON mirrors before the helper** — `ensure_local_mesh_secrets.py` reads `.local/mesh-secrets.json` **before** the repo-local env file. Move any existing orama + Perpetua-Tools `mesh-secrets.json` files into `.local/archive/` (timestamped `.bak`) so the transferred env value is the source of truth.
   3. Run the helper (no `--force`): `.\.venv\Scripts\python.exe scripts\mesh\ensure_local_mesh_secrets.py`
   4. **Parity gate** — confirm the repo-local env value matches every JSON store (orama + PT sibling when present). Fail closed if any store disagrees.
6. Verify mesh (discover, gossip, LMS probes) on **every** node — Mac and all Windows GPU nodes
7. **Windows-only gate** (blocking when ≥1 Windows node in fleet): on **each** Windows GPU node, run `hermes backup` → optional `install-hermes-harness.ps1 -RunDoctor`

### Windows Step 5b–5d (detail)

`ensure_local_mesh_secrets.py` adoption order is JSON stores first, then repo-local env. A stale JSON mirror can overwrite a freshly transferred env value. **Always quarantine JSON before step 5c.**

```powershell
cd $env:ORAMA_SYSTEM_PATH
$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMddTHHmmssZ"
$archive = Join-Path $env:ORAMA_SYSTEM_PATH ".local\archive"
New-Item -ItemType Directory -Force -Path $archive | Out-Null
$archiveIndex = 0
foreach ($store in @(
  (Join-Path $env:ORAMA_SYSTEM_PATH ".local\mesh-secrets.json"),
  $(if ($env:PERPETUA_TOOLS_PATH) { Join-Path $env:PERPETUA_TOOLS_PATH ".local\mesh-secrets.json" })
)) {
  if ($store -and (Test-Path $store)) {
    $archiveIndex++
    $dest = Join-Path $archive "mesh-secrets.json.$ts.$archiveIndex.bak"
    Move-Item -Path $store -Destination $dest -ErrorAction Stop
  }
}
python scripts\mesh\ensure_local_mesh_secrets.py
```

Parity check (value not printed):

```powershell
python scripts\mesh\verify_gossip_secret_parity.py --require-stores || { echo "FAIL: env/JSON parity"; exit 1 }
```

## Merge gate (#222)

| Gate | Scope | Requirement |
|------|-------|-------------|
| **Fleet-wide** | Every node (Mac + all Windows GPU nodes) | Steps **2–6** green on **every** node |
| **Windows-only** | Each Windows GPU node (blocking when fleet includes ≥1 Windows peer) | Step **7** green on **every** Windows node — does **not** substitute for Steps 2–6 |

Merge orama #222 only when **both** gates pass.

## Canonical SSoT

- Ladder: `orama-system/docs/v2/50-mesh-security-migration-ladder.md` (Phase A–D)
- OpenClaw workspace: `$OPENCLAW_ROOT/references/2026-07-27-pre-pr222-operator-backup-runbook.md`

## Open / deferred

- Phase D strict cutover deferred to v2 launch
