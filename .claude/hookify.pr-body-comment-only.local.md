---
name: pr-body-comment-only
enabled: true
event: bash
action: warn
pattern: "(ManagePullRequest.*update_pr|gh pr edit|append-pr-body\\.sh)"
---

# Layer 0 — PR body comment-only (Cursor agents)

**NEVER** automatically change an existing PR description.

## Do

- `ManagePullRequest post_comment`
- `gh pr comment`

## Never (blocked by hooks — fail-closed)

- `ManagePullRequest update_pr` with `body=` (including empty body)
- `gh pr edit` / `gh api` PR body mutations
- `append-pr-body.sh` without operator grant

Operator grant: interactive `scripts/cursor/grant-pr-body-human-override.sh` only.
After grant, agents may run **append-pr-body.sh** — not direct body writes.

Skill: `bin/orama-system/skills/cursor-pr-body/SKILL.md`.
