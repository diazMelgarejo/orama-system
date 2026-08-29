# Feature Extraction: Foundry Lifecycle & Evaluation

> **Reconciliation status (2026-08-28):** golden-dataset evaluation -- **MOVE UP** to the
> `orama-system` evaluator layer. Isolation principle -- **ADOPT** as effect/security policy, not
> engine scheduling. Dynamic routing -- **MOVE UP** to GraphSpec/runtime policy, which produces a
> concrete route MiniGraph executes. See
> [`RECONCILIATION-2026-08-27.md`](RECONCILIATION-2026-08-27.md).
>
> **Ref:** Microsoft Foundry (Azure AI Foundry)

## 1. Evaluation: "Golden Datasets" & LLM-as-a-Judge

Foundry treats evaluation as a mandatory unit test. It uses high-reasoning models to score sub-agent
outputs against a "Golden Dataset" of expected results.

### oramasys v2 Adaptation: evaluator-owned Verification Nodes

Verification policy belongs to the **`orama-system` evaluator/policy layer**, not to MiniGraph.
The outer layer decides whether a critical task requires verification, which evaluator/rubric is
authoritative, and what threshold controls promotion or retry. It may compile that decision into a
realized graph containing an ordinary Verification Node.

- **Mechanic**: A realized Verification Node may use a Critic model to score selected state/output.
- **Policy**: Thresholds, judge model/rubric versions, retry/promotion decisions, and golden datasets
  remain evaluator-layer authority.
- **Kernel boundary**: MiniGraph executes the realized node and its concrete route; it does not
  define what "verified" means or mandate verification topology itself.

## 2. Infrastructure: Isolated MicroVMs & Identity

Foundry runs each session in an isolated microVM and assigns each agent a unique identity (Entra
ID).

### oramasys v2 Adaptation: ToolNode Sandboxing (MAESTRO Layer 4)

We cannot provide full microVMs in a "nimble" stack, but we can repurpose the **Sandbox
Constraint**.

- **Mechanic**: Tool execution may use OS-native sandboxing where supported, but sandbox
  requirements and approvals belong to the effect/security policy layer rather than MiniGraph
  scheduling semantics.
- **Identity**: Every \`GossipBus\` event is tagged with the \`session_id\` and \`agent_id\`,
  creating an immutable audit trail of which "identity" took which action.

## 3. The "Magentic" Pattern: Dynamic Routing

Foundry supports "Magentic" orchestration where the system determines the best agent for the task on
the fly.

### oramasys v2 Adaptation: policy-owned dynamic routing

- **Mechanic**: GraphSpec/runtime policy selects or validates the agent/model route using relevant
  capability, hardware, endpoint, budget, and evaluation policy.
- **The Flow**: The outer policy layer realizes a concrete allowed route. MiniGraph then executes
  that route using its ordinary edge semantics; it does not become the agent/model-selection
  policy engine.
- **Hardware boundary**: Agate may contribute hardware fit/readiness evidence, but hardware facts do
  not themselves own task-level agent-selection policy.

## 4. Summary: The oramasys Way

We mine the **Accountability** of Foundry while preserving explicit ownership boundaries.

| Feature | Foundry Implementation | oramasys Adaptation |
| --- | --- | --- |
| Evaluation | LLM-as-a-Judge | `orama-system` evaluator policy + realized Verification Nodes |
| Isolation | MicroVMs | Effect/security policy + OS-native sandboxing where supported |
| Routing | Magentic | GraphSpec/runtime policy realizes a route; MiniGraph executes it |
