---
name: ecc-sync
description: Post-merge ECC Tools sync — run after any ECC Tools PR merges into orama-system
disable-model-invocation: true
---

Run immediately after any ECC Tools PR is merged.

**Dirty worktree?** Stash first — [`../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md).

```bash
git pull origin main
```

Then in Claude Code:

```bash
/instinct-import .claude/homunculus/instincts/inherited/orama-system-instincts.yaml
/instinct-status
```

Then commit:

```bash
git add -A
git commit -m "chore(ecc): post-merge instinct import sync $(date +%Y-%m-%d)"
git push origin main
```

If `/instinct-import` unavailable: check ECC Tools MCP is running, or run `python .claude/homunculus/import_instincts.py` directly.

Related: `.claude/lessons/LESSONS.md` · `.claude/commands/ecc-sync.md` (legacy alias)
