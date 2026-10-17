# Skill, Chain, Loop, and Graph Escalation

Use this card before CIDF execution when the work's control shape is unclear.
It helps select the least powerful sufficient shape; it does not modify CIDF's
ranked insertion method, automation gate, or verification contract.

## Select a Shape

| Shape | Use when | Must be explicit |
| --- | --- | --- |
| Skill | One bounded capability solves the task. | Inputs, output, and verification. |
| Chain | Steps are known and sequential. | Handoff values and failure boundary. |
| Bounded loop | A result must improve or converge. | Metric, budget, stagnation rule, and exit. |
| Graph | Conditional routes or independently owned state matter. | Node/edge semantics, authority, checkpoint, and recovery. |
| Constellation | Several repositories or owners compose a system. | Owner contracts, transport, evidence, and integration gates. |

Do not choose a graph because a request sounds complex. Escalate only when the
topology itself must be inspected or independently verified.

## Preflight

Before selecting the shape, record:

1. the outcome and non-goals;
2. the authority for inputs, state, effects, and completion;
3. the acceptance check and evidence destination;
4. the checkpoint, idempotency rule, recovery budget, and terminal condition;
5. the maker, evaluator, and any human approver.

If an external action has an unknown outcome, preserve that uncertainty. Do not
retry it as though it were known not to have happened.

## CIDF Stays in Charge of Insertion

After this preflight, return to [CIDF](../SKILL.md): select its lowest eligible
rank, run `lint_strict()`, execute with the supported fallback, and read back a
programmatic verification signature. This card cannot authorize scripting,
skip target verification, or turn a visual result into completion.

## Grounding Rules

- Name one authority for each state category; caches and indexes are derived
  unless a contract says otherwise.
- Bind claims to source, time, actor, and verification scope.
- Keep evaluation independent from mutation when the claim matters.
- Preserve contradiction, refusal, and failed-attempt records.
- Treat coordination events as signals, not approval or endorsement.
- Require explicit operator authority for non-delegated effects.

For the method-level gate, load [AFRP](../../afrp/SKILL.md). For the complete
workflow, load [the Orama system skill](../../SKILL.md). The repository-level
map is [ARCHITECTURE.md](../../../../ARCHITECTURE.md); the normative successor
graph contracts are linked there.
