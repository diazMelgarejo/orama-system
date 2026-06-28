---
name: codex-openclaw-agent
description: "Creates and wires a named OpenClaw sub-agent (codex-agent) backed exclusively by Codex CLI + GPT-5.5. Invoked via `openclaw run codex-agent`. Does NOT touch the default routing (ollama/qwen3.5:9b-nvfp4), the main agent, or the coder agent (lmstudio-win). Use only when you need an explicit GPT-5.5/Codex execution path."
---

<!-- THIN-WRAPPER: canonical skill lives in orama-system/bin/orama-system -->

# codex-openclaw-agent (thin wrapper)

Canonical, permanent implementation: `../../../bin/orama-system/skills/codex-openclaw-agent/`.
**Read it before proceeding** — this wrapper only carries discovery metadata.

Pre-wrapper body preserved at `SKILL.md.premerge-20260628.bak`.
