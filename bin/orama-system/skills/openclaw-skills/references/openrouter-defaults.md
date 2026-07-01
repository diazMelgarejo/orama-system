# OpenRouter Default Model Stack

> **Source of truth:** `v1/OpenRouter.md` in OpenClaw root.
> **Version:** 0.9.2
> **Last reviewed:** 2026-07-01

## ClinePass as the preferred coding path

**For coding tasks (refactoring, file editing, agentic tool loops), prefer the
`cline` CLI via `cline-pass/glm-5.2` (Cline Credits) over the OpenRouter free
stack.** ClinePass is the better default because:

- **No rate limits** — OpenRouter free is limited to 50 req/day, 20 RPM
- **1M context** — full GLM-5.2 with reasoning + structured output + tool loops
- **Dedicated billing** — Cline Credits (`app.cline.bot/credits`) are separate
- **Auto-refreshing auth** — the Cline CLI handles WorkOS token refresh

Use the OpenRouter free stack below only for **lightweight routing/triage** that
doesn't need tool loops, or as a fallback when Cline Credits are exhausted.

See [cline-openclaw-agent/SKILL.md](../../cline-openclaw-agent/SKILL.md).

## Canonical fallback chain (lightweight routing / fallback)

When a caller does NOT specify an agent, the openclaw-skills MUST route to OpenRouter free models in this order:

| Tier | Model ID | Context | Role |
|------|----------|---------|------|
| A (primary) | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 1M | Default agent brain — long-context, agentic, SWE-Bench/AIME-strong |
| B | `openrouter/minimax/minimax-m2.5:free` | 205K | Coding fallback — 80.2% SWE-Bench Verified |
| C | `openrouter/deepseek/deepseek-v4-flash:free` | 1.05M | Fast triage — heartbeat analysis, log review |
| D | `openrouter/openai/gpt-oss-120b:free` | 131K | Reasoning + tool use |
| E | `openrouter/z-ai/glm-4.5-air:free` | 131K | Agentic backup |
| F | `openrouter/inclusionai/ling-2.6-flash:free` | 262K | Lightweight tasks |
| Z (last resort) | `openrouter/openrouter/free` | varies | Auto-router |

## Local-first preference

When the workload does NOT need network egress, prefer in this order:
1. `ollama qwen3.5:9b-nvfp4` (Mac, `localhost:11434`) — small/medium tasks
2. `qwen3-coder:480b-cloud` (Mac, when loaded) — heavy code tasks
3. OpenRouter chain (above)

## Gemini routing — specialized only

Gemini is NOT in the default fallback. Reserved for:
- Visual diff / screenshot comparison
- Whole-repo architecture mapping (>5000-line diffs)
- Multi-file stale-doc detection
- Second-opinion code review when explicitly requested

## openclaw.json shape

```jsonc
{
  "env": { "OPENROUTER_API_KEY": "sk-or-..." },
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/qwen3.5:9b-nvfp4",
        "fallbacks": [
          "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
          "openrouter/minimax/minimax-m2.5:free",
          "openrouter/deepseek/deepseek-v4-flash:free",
          "openrouter/openai/gpt-oss-120b:free",
          "openrouter/z-ai/glm-4.5-air:free",
          "openrouter/inclusionai/ling-2.6-flash:free",
          "openrouter/openrouter/free"
        ]
      },
      "models": {
        "ollama/qwen3.5:9b-nvfp4": {},
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free": {},
        "openrouter/minimax/minimax-m2.5:free": {},
        "openrouter/deepseek/deepseek-v4-flash:free": {},
        "openrouter/openai/gpt-oss-120b:free": {},
        "openrouter/z-ai/glm-4.5-air:free": {},
        "openrouter/inclusionai/ling-2.6-flash:free": {},
        "openrouter/openrouter/free": {}
      }
    }
  }
}
```

> If `agents.defaults.models` is set, it becomes an allowlist — `/model` overrides outside it fail with "Model is not allowed."

## Smart-merge rules

When patching `openclaw.json` for an existing OpenClaw instance:
- **PRESERVE** the user's `agents.defaults.model.primary` (which on Mac MUST stay `ollama/qwen3.5:9b-nvfp4` per hard requirement) unless `--force-primary` is passed
- **REMOVE** Gemini from the front of any existing fallbacks list before appending the OpenRouter chain
- **PUSH** Gemini to the end of fallbacks (3rd-choice fallback for analyzer use-cases only)
- See `scripts/apply-openrouter-free-defaults.sh` in orama-system for the canonical apply script

## Rate-limit guidance

- Free OpenRouter: 50 requests/day, 20 RPM
- Pay-as-you-go with ≥$10 credits: up to 1000 free-model requests, still 20 RPM
- For production / sensitive workflows, keep human confirmation and wrapper controls

## See also

- Canonical routing policy: `bin/orama-system/mcp-orchestration/SKILL.md` §2
- Apply script: `orama-system/scripts/apply-openrouter-free-defaults.sh`
- Verify script: `orama-system/scripts/verify-openrouter-models.sh`
