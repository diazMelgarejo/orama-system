---
name: codex-openclaw-agent
description: "Creates and wires a named OpenClaw sub-agent (codex-agent) backed exclusively by Codex CLI + GPT-5.5. Invoked via `openclaw run codex-agent`. Does NOT touch the default routing (ollama/qwen3.5:9b-nvfp4), the main agent, or the coder agent (lmstudio-win). Use only when you need an explicit GPT-5.5/Codex execution path."
---

# codex-openclaw-agent thin wrapper

Canonical skill: `bin/orama-system/skills/codex-openclaw-agent/SKILL.md`

## Quick start

```bash
# Update canonical first
git fetch origin --prune
git pull --ff-only   # dirty tree: bin/orama-system/skills/git-history-surgery/references/safe-cross-host-sync-reference-card.md

# Bind codex-agent (idempotent)
bash bin/orama-system/skills/codex-openclaw-agent/scripts/bind_codex_backend.sh

# Preview without writing
bash bin/orama-system/skills/codex-openclaw-agent/scripts/bind_codex_backend.sh --dry-run

# Invoke the agent
openclaw run codex-agent --task "your task here"
```

## Windows UTF-8 note

```powershell
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```
