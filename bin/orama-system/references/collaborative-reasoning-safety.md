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
|---|---|
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

## Human Authority Boundary

Multi-agent reasoning may research, compare, critique, and recommend. It does not
create authority merely by becoming a chain, swarm, scheduled worker, or always-on
agent.

**Human initiation and approval are required before:**

- starting chain research, a persistent/always-on agent, or a swarm design;
- spending money or invoking a paid external provider beyond an already approved bounded task;
- committing, pushing, deploying, publishing, sending communications, or changing external state;
- using credentials, identity, or permissions beyond the scope explicitly granted for the task.

Approval must bind the intended purpose and scope. A Builder, Critic, Adversary,
or Judge cannot self-approve the next privileged action. Advisory output remains
advisory until an authorized human or an existing narrowly scoped automation
contract permits execution.

---

## Agent Governance

**Must do:**
- Challenge assumptions
- Surface uncertainty
- Preserve evidence
- Expose disagreement
- Document reasoning paths
- Distinguish advisory/research output from external or irreversible action
- Preserve the human approval boundary for privileged, paid, identity-bearing, or persistent execution

**Must not:**
- Manufacture confidence
- Hide uncertainty
- Optimize for consensus alone
- Suppress dissenting evidence
- Treat consensus as authorization
- Self-authorize chain research, persistent agents, swarms, paid execution, commits, deploys, communications, or credential use
