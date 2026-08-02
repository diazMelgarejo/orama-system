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
  `$PERPETUA_TOOLS_PATH`, `$PT_HOME`, or `.paths` / sibling discovery — see
  [`../oramasys-method/references/sync-local-pt-checkout.md`](../oramasys-method/references/sync-local-pt-checkout.md)).

Cross-repo link policy: [`../oramasys-method/references/cross-repo-links.md`](../oramasys-method/references/cross-repo-links.md)

## Before Use

Run the fail-closed sync in
[`../oramasys-method/references/sync-local-pt-checkout.md`](../oramasys-method/references/sync-local-pt-checkout.md)
with:

```bash
export CANONICAL_PT_URL="https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md"
# paste/run the _resolve_pt_root + validation block from sync-local-pt-checkout.md
```

On any resolver, branch, cleanliness, fetch, or `pull --ff-only origin main`
failure — **stop** and use the [canonical perpetua-config SKILL.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md). Never `git reset --hard` or force-push `main`.

If the worktree is dirty, use [`git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md) only with **explicit operator approval** before any commit or push.

## Load Canonical Skill

Open and follow the [canonical perpetua-config SKILL.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md). Use a local checkout only when the sync procedure above succeeds. Do not copy behavior from this wrapper.

## Windows UTF-8 Note

On Windows PowerShell, set UTF-8 explicitly before reading or writing skill files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```
