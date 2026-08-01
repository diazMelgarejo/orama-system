---
name: pr-body-comment-only
enabled: true
event: bash
action: block
pattern: "(ManagePullRequest.*update_pr|gh pr edit|append-pr-body\\.sh)"
---

# Layer 0 — PR body comment-only (Cursor agents)

**NEVER** automatically change an existing PR description.

## Do

- `ManagePullRequest post_comment`
- `gh pr comment`

## Never (blocked by hooks)

- `ManagePullRequest update_pr` with `body=`
- `gh pr edit` / `append-pr-body.sh`
- Delta-only "refresh" of the Summary

Human override: `CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1` then append-only rules apply.
Skill: `bin/orama-system/skills/cursor-pr-body/SKILL.md`.
