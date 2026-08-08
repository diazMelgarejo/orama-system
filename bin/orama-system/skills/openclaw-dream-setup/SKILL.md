---
name: openclaw-dream-setup
description: "Configure nightly dream-memory distillation with enforced token budgets, cron scheduling, and startup wiring."
---

# openclaw-dream-setup

This is a thin wrapper. The canonical skill lives in this repo at the path below
(resolve the repo root at runtime — paths are never hardcoded).

- Canonical skill path (repo-relative): `bin/orama-system/skills/openclaw-skills/skills/openclaw-dream-setup/SKILL.md`

## Before Use

Before relying on the canonical card, check whether the canonical repository can safely sync:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT/bin/orama-system/skills/openclaw-skills/skills/openclaw-dream-setup"
git fetch origin --prune
git status --short --branch
```

If the repo is on a tracking branch and the worktree is clean:

```bash
git pull --ff-only
```

If the worktree is dirty, use [`git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md) (stash → `pull --ff-only` → pop → commit → push). If the branch is not tracking origin or fast-forward is impossible, report drift — never `git reset --hard` or force-push `main`.

## Load Canonical Skill

Open and follow `bin/orama-system/skills/openclaw-skills/skills/openclaw-dream-setup/SKILL.md` (relative to the repo root). Do not copy behavior from this wrapper.

## Windows UTF-8 Note

On Windows PowerShell, set UTF-8 explicitly before reading or writing skill files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```
