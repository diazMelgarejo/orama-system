# oramaclaw Vendor Sync — PT Mirror Mechanism

**Date:** 2026-06-21  
**Branch:** `feat/openclaw-codex-app-server` → merged into PT `main` (`4125487`)  
**Status:** Shipped

---

## Problem

`src/oramaclaw/` lives in orama-system (L3). Perpetua-Tools (L2) needs to import
it at runtime. Committing a copy into PT's git history creates merge noise, stale
divergence, and a false impression that PT owns the code.

---

## Decision: untracked on-disk mirror + orama-system post-commit hook

`vendor/oramaclaw/` exists on every PT developer machine as a live directory but
is excluded from PT's git history via `.gitignore`. It is kept in sync by a
`post-commit` hook in orama-system that fires automatically after any commit
touching `src/oramaclaw/`.

```
orama-system commit touching src/oramaclaw/
         │
         └─ .githooks/post-commit
                  │
                  └─ scripts/sync-oramaclaw-vendor.sh
                           │
                           └─ rsync src/oramaclaw/ → $PT_ROOT/vendor/oramaclaw/
                                    (untracked, .gitignored in PT)
```

---

## Files

| File | Repo | Purpose |
|------|------|---------|
| `scripts/sync-oramaclaw-vendor.sh` | orama-system | rsync driver; resolves PT root from `$PERPETUA_TOOLS_ROOT` or `$PERPETUA_TOOLS_PATH` |
| `.githooks/post-commit` | orama-system | fires after commits touching `src/oramaclaw/`; calls the sync script |
| `scripts/git/install-local-hooks.sh` | orama-system | installs `pre-commit`, `commit-msg`, **`post-commit`** into `.githooks/`; run on every `start.sh` |
| `vendor/oramaclaw/` | PT | on-disk mirror; in `.gitignore`; never committed |
| `.gitignore` | PT | `vendor/oramaclaw/` entry added `4125487` |

---

## Invariants

- **Causality:** the hook fires in orama-system (source of truth), not in PT. PT
  has no awareness of when orama changes.
- **Fail-safe:** hook exits 0 on any error (`|| true`). A sync failure never
  blocks a commit.
- **Silent no-op:** if neither `PERPETUA_TOOLS_ROOT` nor `PERPETUA_TOOLS_PATH` is
  set, the hook exits immediately. CI and machines without PT checked out are
  unaffected.
- **Manual sync:** `bash scripts/sync-oramaclaw-vendor.sh` can be run at any time
  to force a resync (e.g. after a fresh PT clone or after pulling orama-system
  without committing).

---

## Setup on a fresh machine

```bash
# 1. Clone both repos, set the env var (add to ~/.zshrc):
export PERPETUA_TOOLS_ROOT="$HOME/code/OpenClaw/perplexity-api/Perpetua-Tools"

# 2. Install orama-system hooks (includes post-commit):
bash scripts/git/install-local-hooks.sh

# 3. Prime the vendor dir on first checkout:
bash scripts/sync-oramaclaw-vendor.sh
```

After step 3, every orama-system commit that touches `src/oramaclaw/` will keep
`$PT_ROOT/vendor/oramaclaw/` current automatically.

---

## PT import path

PT processes that need oramaclaw should add the vendor dir to `sys.path` or run
under `PYTHONPATH=$PERPETUA_TOOLS_ROOT/vendor`. The canonical import surface
(`from oramaclaw.engine import ControlEngine`, etc.) is unchanged.

---

## See also

- `docs/2026-06-21-pr98-oramaclaw-v1-code-review.md` — full code review report
- `docs/superpowers/plans/2026-06-21-oramaclaw-master-tick-list.md` — implementation tick list
- `src/oramaclaw/` — canonical source
