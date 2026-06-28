---
name: local-inference
description: >-
  Thin wrapper → hardware-affinity-gate. Local-inference routing absorbed into
  canonical hardware-affinity-gate (orama methodology). PT runtime SSoT via
  pt-hardware-policy command. Load canonical card before acting.
---

# local-inference

This is a thin wrapper. The canonical skill lives in this repo at the path below
(resolve the repo root at runtime; paths are never hardcoded).

- Canonical skill path (repo-relative): `bin/orama-system/skills/hardware-affinity-gate/SKILL.md`
- Hermes command edge: `bin/orama-system/skills/hermes-harness/commands/pt-hardware-policy/SKILL.md`
- Absorption map: `bin/orama-system/skills/hermes-harness/references/hermes-skill-absorption-map.md`

## Before Use

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT/bin/orama-system/skills/hardware-affinity-gate"
git fetch origin --prune
git status --short --branch
```

If the repo is on a tracking branch and the worktree is clean: `git pull --ff-only`.
If dirty or not tracking, report drift and read the canonical card with that caveat.

## Load Canonical Skill

Open and follow `bin/orama-system/skills/hardware-affinity-gate/SKILL.md`. Do not copy behavior from this wrapper.

## Windows UTF-8 Note

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```
