# Local Runtime Overlay — Git Reference Card

> **Use when:** `git status` shows `M config/devices.yml` and/or `M config/models.yml` on
> Perpetua-Tools; before pull/rebase/integrity checks; when an agent is tempted to
> `git checkout` those paths to "clean up".
> **Goal:** Treat discovery-written LAN state as **intentional local cache**, not dirty
> noise — preserve it in the working tree, never commit it.
> **Canonical policy:** [`config/LOCAL-RUNTIME-OVERLAY.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/LOCAL-RUNTIME-OVERLAY.md)
> **Enforcement:** [`scripts/git/check_local_runtime_overlay.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/scripts/git/check_local_runtime_overlay.py)

Applies to **Perpetua-Tools** only (`config/devices.yml`, `config/models.yml`).

---

## Two layers (do not conflate)

| Layer | What | Git rule |
|-------|------|----------|
| **Committed schema** (`HEAD` / `origin/main`) | Device/model structure; empty `lan_ip`; loopback or env-var host defaults | Must stay LAN-free — CI `--mode tree` |
| **Working-tree overlay** | Last discovery/dispatch probe wrote operator DHCP addresses | **Keep locally** — never commit; never `git checkout` to discard |

`git status` showing `M config/devices.yml` on an active machine is **normal**, not a hygiene failure.

---

## Operator / agent rules

| Do | Don't |
|----|-------|
| Leave overlay values in the working tree | `git checkout` / `git restore` those paths to "clean up" |
| Stash before pull/rebase if merge would overwrite | Commit RFC1918 / operator LAN values |
| Compare **committed** trees for integrity (`git archive origin/main`, or overlay checker `--mode tree` on a fresh clone) | Treat overlay drift as merge corruption |
| Use hooks-safe stash pop after pull, or let discovery refresh | `git add -A` blindly on PT without reviewing overlay files |

---

## Before pull / rebase (overlay preservation)

```bash
# Perpetua-Tools repo root only
git stash push -m "runtime overlay" -- config/devices.yml config/models.yml
git pull --ff-only origin main   # or rebase — your normal sync
git -c core.hooksPath=/dev/null stash pop
bash scripts/git/install-local-hooks.sh
# If conflicts in overlay files: keep working-tree values or re-run discovery; do not commit LAN IPs
```

See [`stash-hooks-safeguard-reference-card.md`](../../git-history-surgery/references/stash-hooks-safeguard-reference-card.md) — **always** hooks-off → pop → hooks-on.

When syncing **both** repos, run the overlay stash in PT **inside** the broader
[safe-cross-host-sync](safe-cross-host-sync-reference-card.md) stash → pull → pop flow
(stash overlay paths explicitly if the broad stash message is not enough for agents to remember).

---

## Optional per-clone hardening

Prevents accidental `git add -A` of overlay values on **this machine only** (not committed):

```bash
git update-index --skip-worktree config/devices.yml config/models.yml
# Undo:
git update-index --no-skip-worktree config/devices.yml config/models.yml
```

---

## Integrity checks (fresh `origin/main` vs local)

When verifying post-merge regression or silent merge failure:

1. **Ignore** working-tree overlay diffs when judging local checkout health.
2. Compare **committed** content: `git diff origin/main -- config/devices.yml` should be empty in the index/HEAD sense; working tree may differ.
3. On a **fresh clone** of `origin/main`, run:
   `python3 scripts/git/check_local_runtime_overlay.py . --mode tree` — must pass.
4. For full-tree integrity, use [fresh-main integrity diff (CLAYGO)](fresh-main-integrity-diff-claygo.md) and **exclude** overlay interpretation errors (see that card § Overlay exclusions).

---

## Related

- [`stash-hooks-safeguard-reference-card.md`](../../git-history-surgery/references/stash-hooks-safeguard-reference-card.md) — mandatory hooks-off before stash pop/apply
- [`safe-cross-host-sync-reference-card.md`](../../git-history-surgery/references/safe-cross-host-sync-reference-card.md) — Mac ↔ Win `main` sync
- [`../SKILL.md`](../SKILL.md) — worktree lifecycle
- [`fresh-main-integrity-diff-claygo.md`](fresh-main-integrity-diff-claygo.md) — true unique branch contribution vs `origin/main`
- [`config/LOCAL-RUNTIME-OVERLAY.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/LOCAL-RUNTIME-OVERLAY.md) — package policy source
