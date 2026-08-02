# Guard sync divergence — reference card

## Problem this solves

2026-08-01 guard epic: Perpetua-Tools hardened `audit_engine.py` on PR #319 while
orama canonical still carried the old copy. Running `sync-attribution-guard-scripts.sh`
orama → PT would **clobber** PT improvements. Parity checks reported DRIFTED but
did not distinguish *safe lag* from *sibling ahead*.

## Algorithm (per manifest path)

```text
canon_hash = hash(canonical HEAD file)
sib_hash   = hash(sibling HEAD file)

if canon_hash == sib_hash: SAFE
if sib_hash in canonical git history for path: SAFE (sibling lags — upgrade OK)
if canon_hash in sibling history only: BLOCK (canonical behind — promote sibling)
else: BLOCK (forked / sibling innovations absent from canonical)
```

## Execution surfaces

| Surface | When |
| ------- | ---- |
| `sync-attribution-guard-scripts.sh` | Runs checker `--workspace` before sync (unless `GUARD_SYNC_SKIP_DIVERGENCE_CHECK=1`) |
| `.githooks/pre-push` | When outgoing commits touch `scripts/git/` manifest paths |
| Agent manual | Before any harmonization wave |

## One-PR-per-repo consolidation

| Repo | Open PR | Role |
| ---- | ------- | ---- |
| Perpetua-Tools | #319 | Canonical staging until merged |
| orama-system | #255 | Absorb + doctrine + checker |
| AlphaClaw | #26 | Downstream mirror |

Do not open PR #320, #27-sync, etc. Stack commits on these branches until merge.

## Merge order after wave

1. PT #319 → `main`
2. orama #255 → `main` (checker + promoted guards)
3. AlphaClaw #26 → `feature/MacOS-post-install`

## Emergency bypass

```bash
GUARD_SYNC_SKIP_DIVERGENCE_CHECK=1 bash scripts/git/sync-attribution-guard-scripts.sh <target>
```

Requires explicit operator acknowledgment — never default for agents.
