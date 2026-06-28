# Safe Cross-Host Sync — Git Reference Card

> **Use when:** Mac ↔ Win (or any two clones) must share `main` while one host has local edits.  
> **Goal:** Pull remote work, land your commit, push — **without** destructive git.  
> **Origin:** 2026-06-28 Win `start.ps1` discover fix + Mac Phase 1–2 LAN peer channel (`1932423` on `orama-system`).

This is **normal sync**, not history surgery. For rewrites/expunges, use
[`expunge-contaminated-history.md`](expunge-contaminated-history.md) instead.

---

## When to use

| Situation | Use this card |
|-----------|----------------|
| Dirty worktree + need `git pull --ff-only` before merge/push | ✅ |
| Cross-host handoff (Win pushed → Mac must pull, or reverse) | ✅ |
| Submodule-only drift (`vendor/ecc-tools` new commits) you do **not** intend to commit | ✅ stash/pop, then leave unstaged |
| Secret/token/path in committed history | ❌ use expunge flow |
| Branch rewrite / force-push recovery | ❌ use re-anchor flow |

**Repos in scope:** `orama-system` and `Perpetua-Tools` — run the protocol **per repo**.

---

## Non-negotiables (fail closed)

| Forbidden | Why |
|-----------|-----|
| `git reset --hard` | Destroys uncommitted and stashed work without review |
| `git push --force` / `--force-with-lease` on `main` | Unless user explicitly requests + lease recorded |
| `git pull` without `--ff-only` on `main` | Avoid surprise merge commits on shared trunk |
| `git stash drop` before verifying pop | Stash is the safety net |
| Commit `.env.local`, tokens, `control_plane_token` | Gitignored secrets — handoff via `print-lan-peer-token` scripts |
| Commit submodule drift by accident | Review `git status` after pop; restore if unintended |
| `git config` global/local changes by agents | User-owned identity and hooks |

**Windows PowerShell:** run [`windows-powershell-runtime-bootstrap.md`](windows-powershell-runtime-bootstrap.md) first. Use `;` not `&&` in older PS; quote `git rev-parse --abbrev-ref '@{u}'`.

---

## Protocol (bash — Mac / Git Bash)

Run from each repo root (`orama-system`, then `Perpetua-Tools`):

```bash
# 0. Preflight
git status --short --branch
git fetch origin --prune

# 1. Stash everything (including untracked)
git stash push --include-untracked -m "preserve: cross-host sync $(date +%Y-%m-%d)"

# 2. Fast-forward only — stops if diverged (safe)
git pull --ff-only origin main

# 3. Restore local work
git stash pop
# If conflicts: resolve manually, never reset --hard

# 4. Review what will ship
git status --short
git diff --stat

# 5. Commit only intentional files (example)
git add platform/windows/start.ps1   # paths vary
git commit -m "fix(windows): short summary

Why: one sentence."

# 6. Push
git push origin main
git status --short --branch
```

**Peer host** after push:

```bash
git pull --ff-only origin main
```

---

## Protocol (PowerShell — Windows)

```powershell
# 0. Preflight
git status --short --branch
git fetch origin --prune

# 1. Stash ( -u includes untracked; same as --include-untracked )
git stash push -u -m "preserve: cross-host sync $(Get-Date -Format yyyy-MM-dd)"

# 2. Fast-forward only
git pull --ff-only origin main

# 3. Restore
git stash pop

# 4. Review
git status --short
git diff --stat

# 5. Commit (use backtick-n for body paragraphs in PS)
git add platform/windows/start.ps1
git commit -m "fix(windows): short summary`n`nWhy: one sentence."
git push origin main
git status --short --branch
```

---

## Multi-repo order (Mac ↔ Win stack)

1. `orama-system` — stash → pull → pop → commit/push (or pull-only on peer)
2. `Perpetua-Tools` — same; **often** only submodule drift locally → pop and **do not** commit unless intentional

Typical clean end state:

- `orama-system`: working tree clean, `main` matches `origin/main`
- `Perpetua-Tools`: optional `vendor/ecc-tools` modified — leave unstaged unless bumping submodule pin

---

## Decision tree after `stash pop`

```text
git status clean?
  yes → done (pull-only case) or nothing to push
  no → inspect each path:
    intentional fix/docs → git add + commit + push
    submodule drift only → git restore vendor/<name> OR leave unstaged
    .env.local / .paths / tokens → never add; keep gitignored
    conflict markers → resolve files; re-run hygiene; never reset --hard
```

---

## Verification (before push)

```bash
python3 scripts/review/repo_hygiene.py .
# optional targeted tests for touched areas
git log -1 --oneline
```

Hooks (once per clone): `bash scripts/git/install-local-hooks.sh`

---

## Example session (2026-06-28)

**Win** had local `platform/windows/start.ps1` fix; **Mac** had landed `lan_peer_channel.py` on `main`.

| Step | orama-system |
|------|----------------|
| Stash | `start.ps1` discover stderr fix |
| Pull | `af804c8..85ec1df` (Mac LAN P2P) |
| Pop | clean |
| Commit | `1932423` — discover stderr no longer aborts `start.ps1` |
| Push | Win → `origin/main` |
| Mac | `git pull --ff-only origin main` → sees `1932423` |

---

## Related

- [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../docs/wiki/08-git-hygiene-and-branching.md) — stash-first discipline, identity, hygiene
- [`windows-powershell-runtime-bootstrap.md`](windows-powershell-runtime-bootstrap.md) — Git/Node PATH on Win
- [`../SKILL.md`](../SKILL.md) — history surgery (distinct from this card)
- [`../../using-git-worktrees/SKILL.md`](../../using-git-worktrees/SKILL.md) — parallel worktrees
- [`../../hermes-harness/references/lan-peer-self-talk.md`](../../hermes-harness/references/lan-peer-self-talk.md) — operator playbook (sync before LAN peer)
