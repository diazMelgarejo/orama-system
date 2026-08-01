---
name: ecc-sync
description: Post-merge ECC Tools sync — run after any ECC Tools PR merges into orama-system
disable-model-invocation: true
---

# ecc-sync

Run immediately after any ECC Tools PR is merged.

**Dirty worktree?** Stash first — [`../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md).

```bash
git pull origin main
```

## Harmonization rules (periscope pattern)

| Rule | Detail |
| ------ | -------- |
| Supplement, don't replace | Add session YAML under `instincts/inherited/`; append to `*-instincts.yaml` bundle |
| Exclude timestamp churn | Skip `ecc-tools.json` / `identity.json` unless intentional |
| Quality gate | 2–4 curated instincts per stack — no bulk auto-dumps |

Full ritual: [`../../references/learn-eval-ecc-ritual-reference-card.md`](../../references/learn-eval-ecc-ritual-reference-card.md)

Then in Claude Code:

```bash
/instinct-import .claude/homunculus/instincts/inherited/orama-system-instincts.yaml
/instinct-status
```

Or import a session file first, then merge triggers into the bundle:

```bash
/instinct-import .claude/homunculus/instincts/inherited/guard-sync-pr251-2026-08-01.yaml
```

Then commit:

```bash
git add -A
git commit -m "chore(ecc): post-merge instinct import sync $(date +%Y-%m-%d)"
git push origin main
```

If `/instinct-import` unavailable: check ECC Tools MCP is running, or run
`python .claude/homunculus/import_instincts.py` directly.

Related: `.claude/lessons/LESSONS.md` · `.claude/commands/ecc-sync.md` (legacy alias)
