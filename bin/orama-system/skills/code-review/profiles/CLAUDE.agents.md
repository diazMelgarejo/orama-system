# CLAUDE.md - Agents Profile
# Best for: automation pipelines, multi-agent systems, bots, scheduled tasks
# Source: drona23/claude-token-efficient (harmonized for orama-system ethos)

## Output
- Structured output only: JSON, bullets, tables.
- No prose unless the downstream consumer is a human reader.
- Every output must be parseable without post-processing.

## Agent Behavior
- Execute the task. Do not narrate what you are doing.
- No status updates like "Now I will..." or "I have completed..."
- No asking for confirmation on clearly defined tasks. Use defaults.
- If a step fails: state what failed, why, and what was attempted. Stop.

## orama-system Agent Constraints
- `depth=0` validated server-side; workers cannot spawn sub-workers in V1.
- Terminology: `orchestrator` only — never `coordinator` in output, schemas, config.
- HITL: `status="interrupted"` and `status="conflicted"` are terminal-until-human.
  → See `orama-system/docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md` for the 5 rules.
- Hardware affinity: never route `windows_only` models to Mac LM Studio mirror.
  → See `orama-system/docs/v2/17-hardware-policy-enforcement.md`.

## Simple Formatting and Encoding
- No decorative Unicode: no smart quotes, em dashes, or ellipsis characters.
- All strings must be safe for JSON serialization.

## Hallucination Prevention (Critical for Pipelines)
- Never invent file paths, API endpoints, function names, or field names.
- If a value is unknown: return null or "UNKNOWN". Never guess.
- If a file or resource was not read: do not reference its contents.

## Token Efficiency
- Pipeline calls compound. Every token saved per call multiplies across runs.
- No explanatory text in agent output unless a human will read it.
- Return the minimum viable output that satisfies the task spec.
- Cap parallel subagents at 3 unless explicitly instructed otherwise.
- Use code-review-graph blast-radius before reading files: see [`../references/tool-chain.md`](../references/tool-chain.md).
