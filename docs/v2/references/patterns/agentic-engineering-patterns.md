# Feature Extraction: Agentic Engineering Patterns

> **Reconciliation status (2026-08-28):** deterministic harness/March of Nines pattern -- **ADOPT**.
> Sentinel-as-kernel-mechanic -- **MOVE UP**: verification topology and acceptance policy live in
> `orama-system`; MiniGraph executes an ordinary realized node, it does not understand "verified"
> or "golden dataset." See
> [`RECONCILIATION-2026-08-27.md`](RECONCILIATION-2026-08-27.md).
>
> **Ref:** Andrej Karpathy (March of Nines)

## 1. The Core Mechanic: Deterministic Harnessing

Rather than prompting an agent to "Fix this bug," we define a harness: **"Write a failing test → Fix
the bug → Run test again."** This makes a 90%-reliable LLM nearly 100% reliable by wrapping it in
deterministic code.

## 2. Best Practices to Mine

- **LLM-Wiki (Project Memory)**: Agents must read \`LESSONS.md\` and \`SKILL.md\` before every
  implementation task.
- **Probe Nodes**: Every write operation must be preceded by a read operation to verify the target
  state.
- **Success Criteria**: The `orama-system` evaluator/policy layer may require an independent
  Verification/Sentinel step and compile that requirement into the realized workflow. MiniGraph
  executes that node like any other node; it does not own the verification policy.

## 3. oramasys v2 Adaptation

Adopt the **Sentinel pattern as an `orama-system` evaluator/policy integration**, not as MiniGraph
kernel semantics. The outer layer defines the acceptance rule, evaluator version, and whether a
Sentinel step is required; the realized graph may then contain an ordinary verification node.

**Reference implementation hint for a realized evaluator node:**

```python
# Ordinary graph node produced/required by the outer evaluator policy.
def sentinel_check(state: PerpetuaState):
    if not state.metadata.get("test_ran"):
        raise RuntimeError("Sentinel Violation: Agent attempted implementation without a test run.")
    return {"status": "verified"}
```

This snippet illustrates node behavior only. It is not a claim that MiniGraph owns the policy that
chooses the Sentinel, defines "verified," or controls promotion.
