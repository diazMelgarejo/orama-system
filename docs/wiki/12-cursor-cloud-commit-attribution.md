# 12. Cursor Cloud — commit attribution guards

**TL;DR:** Cloud agents can inject `Co-authored-by` trailers via managed git hooks. Run `scripts/git/apply-attribution-guard-all-repos.sh` on VM boot; use `commit-clean.sh` when hooks cannot be avoided.

---

## What happens

| Mechanism | Effect |
|-----------|--------|
| `CURSOR_AGENT=1` | Marks agent VM; **not** a user toggle |
| `core.hookspath` → `~/.cursor/agent-hooks/<b64-path>/` | Cursor runs `commit-msg.cursor.co-author` |
| Desktop **Agents → Attribution** | IDE/CLI `Made-with:` trailer; **does not** reliably disable cloud co-author hooks |

There is **no** supported `CURSOR_AGENT=0` or cloud dashboard switch to disable co-author injection today.

---

## Guards (apply all)

From **orama-system** (canonical scripts):

```bash
bash scripts/git/apply-attribution-guard-all-repos.sh
```

Per repo:

```bash
bash scripts/git/disable-cursor-commit-attribution.sh /path/to/repo
```

This:

1. Disables `commit-msg.cursor.co-author` in the Cursor agent-hooks directory for that repo path.
2. Sets `core.hookspath` to `.git/hooks` and installs `commit-msg.strip-coauthor`.
3. Sets local `user.name` / `user.email` to cyre if unset.

### Hook-free commit (history-sensitive work)

**Mandatory three-step sequence** — never skip or reorder:

```bash
# 1. Stage (REQUIRED — commit-clean never runs git add)
git add <paths>   # or git add -A when the whole tree is intentional

# 2. Verify (REQUIRED — blocks empty commits)
bash scripts/git/verify-staged-for-commit.sh

# 3. Commit (hook-free)
bash scripts/git/commit-clean.sh -m "type(scope): summary"
```

Amend tip (message-only amend skips step 2 when nothing is staged):

```bash
bash scripts/git/commit-clean.sh -m "type(scope): summary" --amend
```

`commit-clean.sh` writes only the **staged** index. It does **not** run
`git reset --hard` and therefore does not discard unstaged edits.

**Failure mode (2026-07-29):** If step 1 is skipped while unstaged edits exist,
the old script still created a commit (same tree as HEAD, new message only).
CI then ran against code that never landed. `verify-staged-for-commit.sh` and
the hardened `commit-clean.sh` now **fail closed** in that case.

Before pushing, confirm file delta:

```bash
git show --stat --oneline HEAD
```

When committing logical batches in parallel, stage one batch fully, verify,
commit, then stage the next — or use separate worktrees so unrelated edits
never share a working tree.

Regression test: `bash scripts/git/commit_clean_test.sh`

---

## PR body updates (append-only)

Cloud agents and `ManagePullRequest update_pr` **replace the entire PR body** when
`body=` is set. Never pass only the latest follow-up paragraph.

**Mandatory workflow:**

1. `gh pr view <N> --json body` — read current body
2. `mkdir -p .git/pr-body-backups` — then save backup under `.git/pr-body-backups/`
3. Keep original `## Summary` at top; append `## Follow-up:` blocks chronologically
4. Preserve CodeRabbit auto-generated sections and Cursor metadata below unchanged
5. Write full merged body: `bash scripts/cursor/append-pr-body.sh <owner/repo> <N> --title "…" --file …`

See `scripts/cursor/append-pr-body.sh`, `bin/orama-system/skills/cursor-pr-body/SKILL.md`, `.cursor/rules/append-only-pr-body.mdc`, `bin/orama-system/cidf/references/integrative-editing-examples.md` §1, Perpetua-Tools `lesson_3b13ab0a45d4`.

---

## Cloud VM install

`.cursor/environment.json` `install` runs `scripts/cursor/cloud-install.sh`, which:

- Installs `python3.12-venv` when `ensurepip` is missing (Debian cloud images often lack it)
- Recreates a broken `.venv` (partial venvs lack `bin/activate`)
- Clones Perpetua-Tools and AlphaClaw under `$HOME/openclaw-v1` (guards against empty `OPENCLAW_HOME` cloning to `/Perpetua-Tools`)
- Runs `apply-attribution-guard-all-repos.sh` after sibling repos are present

---

## Multi-repo sync

Sibling repos receive the same `scripts/git/*` files via `sync-attribution-guard-scripts.sh` (called from `apply-attribution-guard-all-repos.sh`).

**AlphaClaw:** commit and PR on a contrib branch (`cursor/sync-attribution-guards-6421`), not on upstream-tracking `main` — see [13. AlphaClaw fork — contribution branches](13-alphaclaw-fork-contrib-branches.md).

---

## Related

- [08. Git hygiene and branching](08-git-hygiene-and-branching.md)
- `scripts/git/check_identity.sh`
- `bin/orama-system/skills/git-history-surgery/SKILL.md`
