# Stash Hooks Safeguard — Git Reference Card

> **Use when:** any `git stash pop` or `git stash apply` — **always**, before the first attempt.
> **Goal:** restore stashed work without hooks blocking, hanging, or scanning the restored
> tree as if it were a commit.
> **Origin:** 2026-07-25 PT policy stash `pop` hung until hooks were bypassed; agents must
> not learn this the hard way.

Applies to **orama-system** and **Perpetua-Tools** (both use `core.hooksPath=.githooks`).

---

## Rule (agents: inviolable)

```text
NEVER bare `git stash pop` or `git stash apply`.
ALWAYS hooks-off → pop/apply → hooks-on (same shell turn).
```

`git stash push` does not need this (nothing is restored yet). The pain is on **pop/apply**.

---

## Why

- Restoring a stash can touch many tracked files at once; some environments run slow
  filters or agents mistakenly run hygiene as part of the restore path.
- A failed or hung `stash pop` leaves agents stuck mid-sync with no clear error.
- Hooks must be **back on** before the next `git commit` — never leave the clone naked.

---

## Protocol (bash — preferred)

Per-command disable — **does not persist** `core.hooksPath` (safe under “no git config” policy):

```bash
# 3. Restore local work (hooks OFF for this command only)
git -c core.hooksPath=/dev/null stash pop
# or: git -c core.hooksPath=/dev/null stash apply stash@{0}

# 3b. Re-enable hooks immediately (idempotent)
bash scripts/git/install-local-hooks.sh
```

Verify hooks are active before any commit:

```bash
git config --local --get core.hooksPath   # must print: .githooks
```

---

## Protocol (PowerShell — Windows)

```powershell
git -c core.hooksPath=/dev/null stash pop
bash scripts/git/install-local-hooks.sh
git config --local --get core.hooksPath
```

Run [`windows-powershell-runtime-bootstrap.md`](windows-powershell-runtime-bootstrap.md) first if `bash` is not on PATH.

---

## Wrapper one-liner (copy-paste)

```bash
stash_pop_safe() {
  git -c core.hooksPath=/dev/null stash pop "$@" \
    && bash scripts/git/install-local-hooks.sh
}
```

Use `stash apply` the same way (`git -c core.hooksPath=/dev/null stash apply …`).

---

## Forbidden

| Action | Why |
|--------|-----|
| `git stash pop` with default hooks | Hang / false failure on restore (this card exists to prevent that) |
| Leave hooks disabled after pop | Next commit bypasses hygiene, identity, overlay gates |
| `git stash drop` before confirming pop succeeded | Stash is the safety net |
| `git config --local --unset core.hooksPath` without immediate `install-local-hooks.sh` | Persistent naked clone |

---

## Related

- [`safe-cross-host-sync-reference-card.md`](safe-cross-host-sync-reference-card.md) — uses stash pop in step 3
- [`../../using-git-worktrees/references/local-runtime-overlay-reference-card.md`](../../using-git-worktrees/references/local-runtime-overlay-reference-card.md) — overlay stash + pop
- [`../SKILL.md`](../SKILL.md) — absorb/preserve protocol (`stash pop` on synced base)
