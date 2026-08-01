---
name: pr-body-comment-only
enabled: true
event: bash
action: warn
pattern: "(ManagePullRequest.*update_pr|gh pr edit)"
---

# Layer 0 — PR body comment-only (Cursor agents)

**NEVER** automatically change an existing PR description.

## Do

- `ManagePullRequest post_comment`
- `gh pr comment`

## Never (blocked by Cursor hooks — fail-closed)

- `ManagePullRequest update_pr` with `body=` (including empty body)
- `gh pr edit` with `--body` / `--body-file`
- `append-pr-body.sh` without operator authorization

Human override requires **both**:

1. Operator-created ack file: `touch ~/.cursor/pr-body-human-override-ack`
   (or `.git/pr-body-backups/.human-override-ack` in the repo)
2. `export CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1` in the shell running the write

Then append-only Layers 1–6 apply. Skill: `bin/orama-system/skills/cursor-pr-body/SKILL.md`.
