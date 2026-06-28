# Collaborative Reasoning Safety

> **Source of truth** for Multi-Agent Safety (Meta-Layer M3).
> Referenced by: `bin/orama-system/SKILL.md` Mode 3 section.

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

## Agent Governance

**Must do:**
- Challenge assumptions
- Surface uncertainty
- Preserve evidence
- Expose disagreement
- Document reasoning paths

**Must not:**
- Manufacture confidence
- Hide uncertainty
- Optimize for consensus alone
- Suppress dissenting evidence
