---
name: pr-body-append-only
enabled: true
event: bash
action: warn
pattern: "(ManagePullRequest|gh pr edit).*\\bbody\\b"
---

# PR body append-only (Cursor agents)

`ManagePullRequest update_pr` and `gh pr edit --body` **replace the entire PR body**.

Mandatory workflow before any PR body write (operator-authorized only):

```bash
touch ~/.cursor/pr-body-human-override-ack
export CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1
gh pr view <N> --repo <owner/repo> --json body --jq .body   # READ
# backup → .git/pr-body-backups/<slug>-pr<N>-<ts>.md         # BACKUP
bash scripts/cursor/append-pr-body.sh <owner/repo> <N> \
  --title "Follow-up: <title>" --file follow-up.md           # WRITE
```

Cursor hooks (`beforeMCPExecution`, `beforeShellExecution`, `failClosed`) enforce this.
Skill: `bin/orama-system/skills/cursor-pr-body/SKILL.md`.
