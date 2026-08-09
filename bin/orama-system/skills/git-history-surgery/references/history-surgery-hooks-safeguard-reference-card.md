# History Surgery Hooks Safeguard — Git Reference Card

> **Use when:** any active history rewrite, metadata scrub, blob expunge, `filter-repo`,
> `filter-branch`, post-rewrite force-push, or multi-branch republish after contamination.
> **Goal:** hooks prevent bad commits in normal work; they must be **off during active
> resolution** and **back on** before the next ordinary commit.
> **Origin:** 2026-08-08 attribution expunge — pre-push ran full guard-sync + attribution
> audit per branch (~40×), blocked `main` under Phase 0, and made expunge look hung forever.

Applies to **orama-system**, **Perpetua-Tools**, **AlphaClaw**, and any repo using
`core.hooksPath=.githooks`.

---

## Rule (agents: inviolable)

```text
NEVER run filter-repo, filter-branch, or post-rewrite force-push with default hooks.
ALWAYS hooks-off for the surgery window → rewrite/push → verify → hooks-on.
```

Hooks are **preventive**, not **diagnostic during surgery**. They audit *new* work; a
rewrite intentionally changes every commit — running hooks mid-flight produces false
blocks, multi-minute stalls, and the illusion that expunge "never started."

---

## Surgery window (what counts as "active")

| In scope (hooks OFF) | Out of scope (hooks ON) |
| -------------------- | ----------------------- |
| `git filter-repo` / `filter-branch` | Normal `git commit` on a feature branch |
| `bash scripts/git/expunge-*.sh` | `commit-clean.sh` after staging |
| Post-expunge `git push --force-with-lease` (all branches) | Routine `publish-clean-branch.sh` on unaudited tip |
| `git reflog expire` / `gc` / `repack` during scrub | `git stash pop` (see stash card — separate one-shot disable) |
| Recording lease SHAs + `--force-with-lease` pushes | Opening/reviewing PRs after surgery is complete |

---

## Protocol (bash — preferred)

Per-command disable — **does not persist** `core.hooksPath` (safe under “no git config” policy):

```bash
# 1. Optional: record that surgery is active (scripts may set this)
export HISTORY_SURGERY_ACTIVE=1

# 2. Rewrite / expunge (hooks OFF for every git invocation in this block)
git -c core.hooksPath=/dev/null filter-repo --force ...
# or: bash scripts/git/history-surgery-git.sh push --force-with-lease="refs/heads/main:${OLD_SHA}" origin main:main

# 3. Post-rewrite verification (hooks still OFF — scans are explicit, not hook-driven)
python3 scripts/review/repo_hygiene.py .   # when applicable
# local-only all-ref blob scan — labels/counts only

# 4. Force-publish rewritten refs (hooks OFF; use lease when possible)
OLD_SHA="$(git rev-parse origin/main)"
git -c core.hooksPath=/dev/null push --force-with-lease="refs/heads/main:${OLD_SHA}" origin main:main

# 5. Clear surgery flag and re-enable hooks immediately (same shell turn)
unset HISTORY_SURGERY_ACTIVE
bash scripts/git/install-local-hooks.sh
git config --local --get core.hooksPath   # must print: .githooks
```

Wrapper helper (repo root):

```bash
bash scripts/git/history-surgery-git.sh <git-args...>
# equivalent to: git -c core.hooksPath=/dev/null "$@"
```

For `main` on repos with Phase 0 direct-push guard, also set `ALLOW_MAIN_PUSH=1` on the
**single** intentional post-expunge push — still with hooks off:

```bash
OLD_SHA="$(git rev-parse origin/main)"
ALLOW_MAIN_PUSH=1 git -c core.hooksPath=/dev/null push --force-with-lease="refs/heads/main:${OLD_SHA}" origin main:main
```

GitHub **branch protection** is separate: temporarily disable or use admin bypass; hooks
off does not override `GH006`.

---

## Protocol (PowerShell — Windows)

```powershell
$env:HISTORY_SURGERY_ACTIVE = "1"
git -c core.hooksPath=/dev/null filter-repo --force ...
git -c core.hooksPath=/dev/null push --force-with-lease origin main
Remove-Item Env:HISTORY_SURGERY_ACTIVE -ErrorAction SilentlyContinue
bash scripts/git/install-local-hooks.sh
```

Run [`windows-powershell-runtime-bootstrap.md`](windows-powershell-runtime-bootstrap.md) first if `bash` is not on PATH.

---

## Relationship to other guards

| Guard | During surgery | After surgery |
| ----- | -------------- | ------------- |
| `pre-push` / `check_no_pending_merge.sh` | **Bypass** (hooks off) | **Active** — finalize any merge before push |
| `publish-clean-branch.sh` audits | Run **before** hooks-off push, or use `HISTORY_SURGERY_PUSH=1` | Default path for non-rewrite publishes |
| `commit-clean.sh` | Do not use for rewrite commits; rewrite tools own metadata | Use for new forward commits |
| Stash pop safeguard | Still use `git -c core.hooksPath=/dev/null stash pop` inside surgery | See stash card |

**Pending-operation push guard** ([`pending-operation-push-guard-reference-card.md`](pending-operation-push-guard-reference-card.md))
applies to *uncommitted merge state*, not to post-expunge force-push. During surgery,
hooks are off so pre-push cannot block; after surgery, never push with `MERGE_HEAD` set.

---

## Forbidden

| Action | Why |
| ------ | --- |
| Bare `git push --force` after `filter-repo` | Pre-push re-audits every commit per branch; appears hung |
| Leave hooks disabled after surgery completes | Next commit bypasses hygiene, identity, overlay gates |
| `git push --no-verify` as routine bypass | Disables all hooks opaquely; prefer explicit `-c core.hooksPath=/dev/null` + restore |
| Assume hook failure means expunge failed | Often false positive on rewritten SHAs / Phase 0 main guard |

---

## Related

- [`stash-hooks-safeguard-reference-card.md`](stash-hooks-safeguard-reference-card.md) — hooks off for stash pop only
- [`expunge-contaminated-history.md`](expunge-contaminated-history.md) — full scrub sequence
- [`pending-operation-push-guard-reference-card.md`](pending-operation-push-guard-reference-card.md) — post-surgery normal pushes
- [`../SKILL.md`](../SKILL.md) — decision item 12
- `scripts/git/history-surgery-git.sh` — wrapper
- `scripts/git/expunge-all-workspace-repos.sh` — workspace expunge (uses hooks-off push)
