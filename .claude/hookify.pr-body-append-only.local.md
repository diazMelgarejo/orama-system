---
name: pr-body-append-only
enabled: true
event: bash
action: block
pattern: "(ManagePullRequest|gh pr edit).*\\bbody\\b"
---

# PR body append-only (Cursor agents)

`ManagePullRequest update_pr` and `gh pr edit --body` **replace the entire PR body**.

Mandatory workflow before any PR body write:

```bash
gh pr view <N> --repo <owner/repo> --json body --jq .body   # READ
# backup → .git/pr-body-backups/<slug>-pr<N>-<ts>.md         # BACKUP
bash scripts/cursor/append-pr-body.sh <owner/repo> <N> \
  --title "Follow-up: <title>" --file follow-up.md           # WRITE
```

Cursor hooks (`beforeMCPExecution`, `beforeShellExecution`) enforce this automatically.
Skill: `bin/orama-system/skills/cursor-pr-body/SKILL.md`.
