---
name: pr-body-append-only
enabled: true
event: bash
action: warn
pattern: "(ManagePullRequest|gh pr edit).*\\bbody\\b"
---

# PR body append-only (Cursor agents)

`ManagePullRequest update_pr` and `gh pr edit --body` **replace the entire PR body**.

Operator-authorized workflow (agent may run **only** `append-pr-body.sh` after grant):

1. Operator runs `scripts/cursor/grant-pr-body-human-override.sh` (interactive TTY).
2. Agent runs `bash scripts/cursor/append-pr-body.sh <owner/repo> <N> --title "…" --file follow-up.md`.

Hooks deny direct `update_pr` / `gh pr edit` / `gh api` body writes even with a grant.
Skill: `bin/orama-system/skills/cursor-pr-body/SKILL.md`.
