# 13. AlphaClaw fork — contribution branches

**TL;DR:** In `diazMelgarejo/AlphaClaw`, **`main` tracks upstream only**. Never open PRs from `main` for orama-stack work. Commit on a **contrib branch** (e.g. `cursor/sync-attribution-guards-6421` or `feature/MacOS-post-install`) and PR into that line, not into upstream `main` directly.

---

## Branch roles

| Branch | Role |
|--------|------|
| `main` | Upstream sync / fork tracking — merge or rebase from upstream; **no feature commits** |
| `feature/*`, `cursor/*` | All diazMelgarejo fork contributions (agents, cloud VMs, local work) |

## Environment variables (cloud + local)

Set in `.cursor/environment.json` or shell:

```bash
export ALPHACLAW_UPSTREAM_BRANCH=main
export ALPHACLAW_CONTRIB_BRANCH=cursor/sync-attribution-guards-6421   # current attribution guards work
# or: feature/MacOS-post-install for general macOS integration work
```

## Checkout contrib branch

After clone or on existing tree:

```bash
bash scripts/git/alphaclaw-contrib-checkout.sh
```

Cloud install (`scripts/cursor/cloud-install.sh`) clones `main` then runs this automatically.

## PR targets

- **Open PRs:** `contrib-branch` → `contrib-branch` (or → long-lived `feature/MacOS-post-install` if that is your integration branch).
- **Do not:** push feature commits to `main` or open `main` ← feature PRs for fork-specific work.

## Attribution guards (2026-05-27)

Git guard scripts for AlphaClaw belong on **`cursor/sync-attribution-guards-6421`** until merged into your integration branch — not on upstream-tracking `main`.

---

## Related

- [12. Cursor Cloud — commit attribution guards](12-cursor-cloud-commit-attribution.md)
- [08. Git hygiene and branching](08-git-hygiene-and-branching.md)
