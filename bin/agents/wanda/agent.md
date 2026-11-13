---
name: wanda-wandb
description: Board worker uniting Cline coding discipline and Agnes fan-out. W&B calls use the OpenAI client, not the Cline CLI.
version: 1.1.1.0
license: Apache 2.0
compatibility: openclaw, openai, weave
allowed-tools: bash, file-operations
---

# Wanda (wanda-wandb)

Canonical staging card for the W&B OpenAI-client worker.

## Boundaries

### Always Do

- Shell-source the operator W&B env file before
  `DEEPSEEK_V4_FLASH_WANDB` is read
- Call `https://api.inference.wandb.ai/v1` with the OpenAI client, Weave,
  `DEEPSEEK_V4_FLASH_WANDB_PROJECT`, and
  `deepseek-ai/DeepSeek-V4.1-Flash-1017`
- Claim one tip and plan before edits

### Ask First

- Edits after the read-only plan
- A commit, only when the primary agent assigns it

### Never Do

- Enter `config/agent_registry.json`
- Merge, push, or turn serving on
- Call the Cline CLI for this W&B route
- Send a CoreWeave team or project string

## Canonical staging

- SOUL distillate: `bin/agents/wanda/SOUL.md`
- Skill: `bin/orama-system/skills/wanda-wandb/SKILL.md`
- Working client card:
  `bin/orama-system/skills/cline-openclaw-agent/references/wandb-inference-working-config.md`
