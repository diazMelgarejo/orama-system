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

```bash
git add …
bash scripts/git/commit-clean.sh -m "type(scope): summary"
# amend tip:
bash scripts/git/commit-clean.sh -m "type(scope): summary" --amend
```

---

## Cloud VM install

`.cursor/environment.json` `install` runs `apply-attribution-guard-all-repos.sh` after sibling repos are cloned.

---

## Multi-repo sync

Sibling repos receive the same `scripts/git/*` files via `sync-attribution-guard-scripts.sh` (called from `apply-attribution-guard-all-repos.sh`).

---

## Related

- [08. Git hygiene and branching](08-git-hygiene-and-branching.md)
- `scripts/git/check_identity.sh`
- `bin/orama-system/skills/expunge-git/SKILL.md`
