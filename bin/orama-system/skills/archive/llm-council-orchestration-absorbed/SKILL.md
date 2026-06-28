---
name: llm-council-orchestration
description: Orchestrate a three-model LLM Council: Host/Executor (Codex/orama), Reviewer/Critic (Antigravity Gemini), and Local Specialist (Hermes + LM Studio + Qwen 3.6 Coder). Cross-harness workflow for high-quality agentic execution.
version: 1.1.0
license: Apache 2.0
compatibility: hermes, codex, windows, antigravity
parent_skill: orama-system
triggers:
  - llm council
  - council orchestration
  - three-model council
  - multi-agent workflow
  - pt-orama onboarding
---

# LLM Council Orchestration

Cross-harness multi-model council workflow for high-quality agentic execution. Based on the ECC (External Context Compiler) principle: **durable workflow assets in one repo, adapted at the harness edge**.

## Overview

This skill implements a three-model LLM Council architecture:

- **Host/Executor**: Codex CLI or main orama agent — handles planning, tool use, and execution.
- **Reviewer/Critic**: Google Antigravity (Gemini) — elite structured critique, catches hallucinations and quality issues.
- **Local Specialist**: Hermes Agent + LM Studio + Qwen 3.6 Coder — private tasks, heavy computation, and persistent local memory.

## Council Protocol

The council follows strict review gates: **Plan → Review → Execute → Review → Finalize**. Only proceed past a review gate when the Reviewer marks the delivery as **CLEAN**.

### Core References

- [`references/council-prompts.md`](references/council-prompts.md): Exact templates for Host, Reviewer, and Specialist.
- [`references/council-workflow.md`](references/council-workflow.md): Detailed gate loop and iteration patterns.

## Prerequisites

### 1. Host (Codex CLI / orama)
- `npm install -g @openai/codex`
- `codex auth login`

### 2. Reviewer (Google Antigravity / AGY)
- Install from [antigravity.google](https://antigravity.google)
- Use a dedicated "Council Reviewer" agent in Agent Manager.

### 3. Specialist (Hermes + LM Studio + Qwen 3.6 Coder)
- **LM Studio**: Load `Qwen 3.6 Coder` (27B/35B, Q5_K_M+). Start local server at `http://localhost:1234/v1`.
- **Hermes**: Configure with `hermes model` → LM Studio → provide exact model ID.

## When to Use

- Complex multi-step coding or refactoring tasks.
- High-risk architecture or security decisions.
- Tasks requiring both cloud speed and local privacy.
- Establishing a default workflow for PT-orama orama-system onboarding.

**Do not use for:**
- Simple one-shot queries (direct single-model access is faster).
- Purely local exploratory research.

## Windows Readiness

- **Pathing**: Use Git Bash or PowerShell with explicit path conversion (see `references/council-prompts.md`).
- **Encoding**: Ensure UTF-8 without BOM for all generated skill or code artifacts.
- **Canaries**:
  - AGY: `agy --print "AGY_READY"` must emit visible stdout.
  - Hermes: `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --max-turns 1` one-shot check.

## Cross-Harness Adaptation

| Harness | Loading Mechanism |
|---------|-------------------|
| **Codex** | Reads `AGENTS.md` and `.codex-plugin/plugin.json`. |
| **Hermes** | `python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py`. |
| **Antigravity** | Managed via `.agent/` thin adapter. |

## Related Skills

- [`../hermes-harness/SKILL.md`](../hermes-harness/SKILL.md): Windows-aware Hermes bring-up.
- [`../mcp-orchestration/SKILL.md`](../mcp-orchestration/SKILL.md): Parallel worker dispatch.
- [`../agent-methodology/SKILL.md`](../agent-methodology/SKILL.md): Oramasys 5-stage loop.
