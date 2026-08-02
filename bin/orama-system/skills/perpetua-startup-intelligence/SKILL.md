---
name: perpetua-startup-intelligence
description: "Startup scenario classification, probe retry, history-driven adaptive timeouts, cloud fallback, and env-local override detection for Perpetua-Tools and orama-system. Use when startup fails to reach backends, when you need to understand…"
---

# startup-intelligence

This is a thin cross-repo redirect stub. The canonical skill lives in
[Perpetua-Tools](https://github.com/diazMelgarejo/Perpetua-Tools) on GitHub
`main` — do not assume a sibling checkout layout.

- **Canonical (GitHub):** [`hardware/startup-intelligence/SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/hardware/startup-intelligence/SKILL.md)
- **Local checkout:** resolve the same relative path inside your
  `Perpetua-Tools` clone (`$PERPETUA_TOOLS_PATH`, `$OPENCLAW_HOME/Perpetua-Tools`,
  or wherever you cloned the repo).

Cross-repo link policy: [`../oramasys-method/references/cross-repo-links.md`](../oramasys-method/references/cross-repo-links.md)

## Before Use

Sync your local clone when one exists:

```bash
PT_ROOT="${PERPETUA_TOOLS_PATH:-${OPENCLAW_HOME:-$HOME}/Perpetua-Tools}"
if [[ -d "$PT_ROOT/.git" ]]; then
  cd "$PT_ROOT"
  git fetch origin --prune
  git status --short --branch
  if git status --porcelain | grep -q .; then
    echo "dirty worktree — see safe-cross-host-sync before pull"
  else
    git pull --ff-only
  fi
else
  echo "No local clone at PT_ROOT=$PT_ROOT — use GitHub canonical or: git clone https://github.com/diazMelgarejo/Perpetua-Tools.git"
fi
```

If the worktree is dirty, use [`git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md) (stash → `pull --ff-only` → pop → commit → push). If the branch is not tracking origin or fast-forward is impossible, report drift — never `git reset --hard` or force-push `main`.

## Load Canonical Skill

Open and follow the [canonical startup-intelligence SKILL.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/hardware/startup-intelligence/SKILL.md). When working locally, read the same path in your checkout. Do not copy behavior from this wrapper.

## Windows UTF-8 Note

On Windows PowerShell, set UTF-8 explicitly before reading or writing skill files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```
