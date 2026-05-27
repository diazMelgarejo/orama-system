# 13. AlphaClaw fork — integration + contrib branches

**TL;DR:** [`origin/main`](https://github.com/diazMelgarejo/AlphaClaw/tree/main) is the **upstream mirror only**. Fork work lives on **`feature/MacOS-post-install`** (integration). Agent commits (e.g. attribution guards) go on **`cursor/sync-attribution-guards-6421`** and PR **into integration**, not into `main`.

Both **`feature/MacOS-post-install`** and **`cursor/sync-attribution-guards-6421`** must share the same nearest common ancestor with upstream: **`origin/main`** (merge-base equals `origin/main` tip).

---

## Branch roles

| Branch | Role |
|--------|------|
| `main` | Upstream mirror — sync from upstream; **no fork feature commits** |
| `feature/MacOS-post-install` | Long-lived **integration** branch (macOS port + fork work) |
| `cursor/sync-attribution-guards-6421` | Short-lived **contrib** branch → PR targets **integration** |

## Environment variables

```bash
export ALPHACLAW_UPSTREAM_BRANCH=main
export ALPHACLAW_INTEGRATION_BRANCH=feature/MacOS-post-install
export ALPHACLAW_CONTRIB_BRANCH=cursor/sync-attribution-guards-6421
```

Set in `.cursor/environment.json` for cloud VMs.

## Align before commit or push

```bash
bash scripts/git/alphaclaw-align-all.sh
```

This:

1. Merges `origin/main` into `feature/MacOS-post-install` if needed.
2. Rebuilds `cursor/sync-attribution-guards-6421` on the integration tip (cherry-picks fork-only commits).
3. Verifies **merge-base**(`branch`, `origin/main`) = `origin/main` for integration and contrib.

## Push + PR order (when you have credentials)

```bash
bash scripts/cursor/push-openclaw-stack.sh
```

1. Push **`feature/MacOS-post-install`** (includes upstream merge commit).
2. Push **`cursor/sync-attribution-guards-6421`**.
3. Open PR: **`cursor/sync-attribution-guards-6421` → `feature/MacOS-post-install`** (not → `main`).
4. Open or update PR: **`feature/MacOS-post-install` → `main`** when integration is ready for upstream sync review.

## Prevent shallow-clone orphan roots

Never build contrib branches from `git clone --depth 1` on a stale SHA. Always run **`alphaclaw-align-all.sh`** after clone so history is anchored on current `origin/main` via the integration branch.

---

## Related

- [12. Cursor Cloud — commit attribution guards](12-cursor-cloud-commit-attribution.md)
- [08. Git hygiene and branching](08-git-hygiene-and-branching.md)
