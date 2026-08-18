# Collaborative Reasoning Safety

> **Source of truth** for Multi-Agent Safety (Meta-Layer M3).
> Referenced by: `bin/orama-system/SKILL.md` Mode 3 section.
>
> **On Claude Code:** the Four Mandatory Roles below map directly onto
> `Workflow`'s built-in "Adversarial verify" (Adversary/Critic) and
> "Judge panel" (Judge) quality patterns - use those primitives to
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

## Confidence Tracking (keep these separate - do not conflate)

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

The four roles are **epistemic roles, not authorization principals**. They can
research, propose, compare, criticize, and judge evidence. They cannot turn
consensus, confidence, or repeated agreement into permission for a consequential
action.

Human authority remains governed by the canonical
[`HUMAN-IN-LOOP-ACCOUNTABILITY.md`](../../../docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md)
contract:

- explicit user initiation or approval is the authority source, never agent consensus;
- chain research, persistent or always-on agents, swarms, paid execution, credential
  use, commits/deploys, external communications, and other consequential state changes
  proceed only when the current authorization contract covers that purpose and scope;
- when the accountability protocol requires a fresh scoped gate, pause and obtain it;
- a prior approval for analysis or another action is not automatically reusable for a
  later privileged action;
- an offline/local-only policy cannot be relaxed by collaborative agreement.

The Judge decides what the evidence supports. The Judge does not manufacture
permission to act on that conclusion.

---

## Advisory vs. Execution Boundary

| Class | Default authority |
| --- | --- |
| Research, analysis, critique, planning, local simulation | Proceed within the explicitly authorized task scope |
| Consequential external, financial, identity, credential, persistent-agent, commit/deploy, or communication action | Follow the current human-accountability gate before execution |

This boundary prevents a reasoning success from silently becoming an authority
escalation.

---

## Agent Governance

**Must do:**

- Challenge assumptions
- Surface uncertainty
- Preserve evidence
- Expose disagreement
- Document reasoning paths
- Preserve the human authority boundary when reasoning turns into action

**Must not:**

- Manufacture confidence
- Hide uncertainty
- Optimize for consensus alone
- Suppress dissenting evidence
- Treat consensus as authorization
- Self-authorize a privileged or consequential next step

---

## Human Initiation & Non-Self-Authorization

> Anchored in: [`HUMAN-IN-LOOP-ACCOUNTABILITY.md`](../../../docs/v2/references/HUMAN-IN-LOOP-ACCOUNTABILITY.md)

Applies to **all modes** — not optional, not overridable by any agent or orchestrator.

**Before any of the following may begin, a human operator must explicitly initiate and approve:**

- Chain-research runs (multi-step autonomous research sequences)
- Always-on / persistent agent activation
- Swarm launches (any multi-agent coordinated execution)

**Agents cannot self-authorize these actions.** Specifically:

- No agent may call `spawn_agents()`, activate a swarm, or start a long-running research chain on its own initiative.
- The `approval_token` must be present, issued out-of-band by a human operator, and HMAC-verified before execution begins (see `swarm_approval.py`).
- If no valid `approval_token` is present → reject with `ValueError`, log the attempt, do not proceed.

**This is the operational enforcement of the Amplifier Principle:**
> "Accountability should not be lost in agentic work. It amplifies human intent, and should never replace or displace our human values and morality."

