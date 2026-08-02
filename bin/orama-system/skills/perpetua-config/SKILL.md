---
name: perpetua-config
description: "This document outlines the model registry and device configuration for the ECC-tools ecosystem. Each device (Mac, Windows, shared Ollama) can run multiple backends (`ollama`, `mlx`, `lm-studio`), and each model is prioritized based on…"
---

# perpetua-config

This is a thin cross-repo redirect stub. The canonical skill lives in
[Perpetua-Tools](https://github.com/diazMelgarejo/Perpetua-Tools) on GitHub
`main` — do not assume a sibling checkout layout.

- **Canonical (GitHub):** [`config/SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md)
- **Local checkout:** resolve the same relative path inside your
  `Perpetua-Tools` clone (`$PERPETUATOOLSROOT`, `$PERPETUA_TOOLS_ROOT`,
  `$PERPETUA_TOOLS_PATH`, or wherever you cloned the repo).

Cross-repo link policy: [`../oramasys-method/references/cross-repo-links.md`](../oramasys-method/references/cross-repo-links.md)

## Before Use

Sync your local clone when one exists:

```bash
PT_ROOT="${PERPETUATOOLSROOT:-${PERPETUA_TOOLS_ROOT:-${PERPETUA_TOOLS_PATH:-${OPENCLAW_HOME:-$HOME}/Perpetua-Tools}}}"
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

Open and follow the [canonical perpetua-config SKILL.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md). When working locally, read the same path in your checkout. Do not copy behavior from this wrapper.

## Windows UTF-8 Note

On Windows PowerShell, set UTF-8 explicitly before reading or writing skill files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```
