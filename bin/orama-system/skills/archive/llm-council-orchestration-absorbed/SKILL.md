---
name: llm-council-orchestration
description: >-
  SUPERSEDED → pt-orama-council + hermes-council-review-gates. Do not use this
  archive card. Win LM Studio coder: qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2.
version: 1.1.0
license: Apache 2.0
status: superseded
redirect_to: bin/orama-system/skills/hermes-harness/commands/pt-orama-council/SKILL.md
parent_skill: orama-system
---

# LLM Council Orchestration (SUPERSEDED)

> **Do not use this archive skill.** Council workflow was absorbed into:
>
> - [`../../hermes-harness/commands/pt-orama-council/SKILL.md`](../../hermes-harness/commands/pt-orama-council/SKILL.md)
> - [`../../hermes-harness/references/hermes-council-review-gates.md`](../../hermes-harness/references/hermes-council-review-gates.md)
>
> Absorption map: [`../../hermes-harness/references/hermes-skill-absorption-map.md`](../../hermes-harness/references/hermes-skill-absorption-map.md)

## Model correction (Windows local specialist)

The archived text referenced an invented **"Qwen 3.6 Coder"**. Canonical Win LM Studio
coder model (probe `state=loaded` via `/api/v0/models`):

`qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`

Never hardcode host paths; resolve loaded model IDs at runtime per
[`hardware-affinity-gate/SKILL.md`](../../hardware-affinity-gate/SKILL.md).

## Historical references (read-only)

- [`references/council-prompts.md`](references/council-prompts.md) — archived prompts (may contain stale model names)
- [`references/council-workflow.md`](references/council-workflow.md) — archived workflow
