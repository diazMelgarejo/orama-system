# Collaborative Reasoning Safety

> **Source of truth** for Multi-Agent Safety (Meta-Layer M3).
> Referenced by: `bin/orama-system/SKILL.md` Mode 3 section.
>
> **On Claude Code:** the Four Mandatory Roles below map directly onto
> `Workflow`'s built-in "Adversarial verify" (Adversary/Critic) and
> "Judge panel" (Judge) quality patterns — use those primitives to
> implement this doctrine, don't hand-roll a parallel mechanism. See
> `claude-code-workflow-canonical.md`.

Applies to Mode 2 and Mode 3. Also applies to any significant single-agent decision.

**Core risk:** multi-agent systems amplify errors as effectively as they amplify insight.
Consensus is not evidence. Agreement is not proof.

---

## Four Mandatory Roles

Every significant decision includes all four:

| Role | Responsibility |
| --- | --- |
| Builder | Produces the solution |
| Critic | Finds gaps and weaknesses |
| Adversary | Constructs the strongest argument against the conclusion |
| Judge | Weighs evidence, not popularity |

---

## Mandatory Challenge

Every conclusion must answer: **what is the strongest argument against this conclusion?**

---

## Confidence Tracking (keep these separate — do not conflate)

- **Confidence:** how sure are we?
- **Uncertainty:** what do we not know?
- **Consensus:** what do the agents agree on?
- **Disagreement:** where do they diverge?

---

## Anti-Groupthink Rule

Reject: "Agent A agrees with Agent B, therefore the conclusion is true."

Evidence wins. Popularity does not.

---

## Adversarial Review (before finalizing)

- Generate the strongest opposing argument
- Attack key assumptions
- Search for failure modes
- Test alternative interpretations

---

## Human Approval Boundary

Multi-agent reasoning may propose, compare, simulate, and critique autonomously.
It may not convert its own consensus into authority for a consequential external action.

Human initiation or explicit approval is required before:

- starting chain-research, always-on-agent, or swarm designs that materially expand runtime scope;
- spending money or invoking a paid execution tier;
- committing, merging, force-pushing, deploying, publishing, or sending external communications when the user has not already authorized that action;
- creating, rotating, revealing, or changing credentials, identity, access, or security boundaries;
- executing an irreversible action outside the local reasoning/review surface.

Approval must bind to the concrete purpose and scope being executed. A prior approval for
analysis or advisory work is not implicit approval for a later external side effect.

---

## Advisory vs. Execution Boundary

Keep these two classes explicit:

| Class | Default authority |
| --- | --- |
| Research, analysis, critique, planning, local simulation | May proceed within the task's stated scope |
| External, irreversible, financial, identity, credential, commit, deploy, or communication action | Requires the task's existing explicit authorization or a fresh human approval |

The Judge role evaluates evidence; it does not manufacture permission. Consensus never
upgrades advisory output into execution authority.

---

## Agent Governance

**Must do:**

- Challenge assumptions
- Surface uncertainty
- Preserve evidence
- Expose disagreement
- Document reasoning paths
- Preserve the human approval boundary when reasoning turns into action

**Must not:**

- Manufacture confidence
- Hide uncertainty
- Optimize for consensus alone
- Suppress dissenting evidence
- Treat agent consensus as permission for a consequential external action
