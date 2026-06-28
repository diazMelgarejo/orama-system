# Recursive Spawn Protocol

This protocol governs safe recursive skill execution for OpenClaw agents routed through PT.

## Hard Limit
`MAX_RECURSION_DEPTH = 3` is defined in PT:
`orchestrator/openclaw_skill_resolver.py`

No invocation may exceed this depth.
Depth is counted from the initial parent envelope as level 0.

## Envelope Lineage
Every `SkillEnvelope` must include `parent_chain`.
`parent_chain` is append-only and records traversal history.

Required lineage fields per hop:
- envelope id
- parent envelope id
- skill id
- agent id
- depth
- timestamp

## Loop Detection
Resolver must detect loops by inspecting `parent_chain`.
At minimum, reject repeated `(agent_id, skill_id, args_fingerprint)` cycles
within the active chain.

If loop conditions are detected, resolver must hard-fail before dispatch.

## Per-Level Resource Budgets
Apply stricter budgets at deeper levels.
Suggested baseline:
- Level 0: up to 120k tokens, 20 minutes, 80 file touches
- Level 1: up to 80k tokens, 12 minutes, 50 file touches
- Level 2: up to 40k tokens, 8 minutes, 30 file touches
- Level 3: up to 20k tokens, 5 minutes, 15 file touches

Budgets are maximum caps, not targets.

## Budget Enforcement
PT resolver should attach effective budgets to each child envelope.
Execution layers must honor these budgets and stop early on exceed events.

If a budget is exceeded, PT raises `RecursionBudgetExceeded`.

## Mandatory Error Propagation
When PT raises `RecursionBudgetExceeded`, the calling agent MUST:
- propagate a structured error upstream
- include lineage context and failing budget dimension
- avoid swallowing or rewriting the core error class

Required structured error shape:
- `status`: `error`
- `error_type`: `RecursionBudgetExceeded`
- `message`: concise cause
- `meta.parent_chain`: lineage snapshot
- `meta.depth`: current depth

## Retry Policy
Do not blind-retry recursion budget failures.
Retry is allowed only after reducing scope, depth, or payload size.

## Safety Defaults
- Prefer non-recursive execution when equivalent.
- Spawn children only for bounded parallel subtasks.
- Collapse trivial child calls into parent when possible.

## Audit Requirements
Persist for each recursive invocation:
- envelope ids and parent linkage
- assigned budget vs observed usage
- completion status
- termination reason on failure

## Compliance Outcome
Any agent that suppresses recursion errors is non-compliant.
Non-compliant callers should be flagged for policy remediation.
