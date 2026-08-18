# 04 — Human Accountability & Forward-Looking Plan
# oramasys + perpetua v2.1 → v2.5 Development Ladder

> **Document type:** Forward-looking statements and architectural doctrine
> **Anchored in:** Amplifier Principle → MAESTRO/SWARM Frameworks → EU AI Act Annex III
> **Live date:** 2026-08-18
> **Status:** Canonical — sync to Perpetua-Tools `/docs/v2/references/04-HUMAN-ACCOUNTABILITY-FORWARD-PLAN.md`
> **Related docs:**
> - [HUMAN-IN-LOOP-ACCOUNTABILITY.md](./HUMAN-IN-LOOP-ACCOUNTABILITY.md)
> - [collaborative-reasoning-safety.md (M3)](../../../bin/orama-system/references/collaborative-reasoning-safety.md)

---

## Foundational Doctrine: The Amplifier Principle

> *"Accountability should not be lost in agentic work. It amplifies human intent,
> and should never replace or displace our human values and morality."*

This is not a compliance statement. It is the **values foundation** from which all
technical decisions in oramasys+perpetua derive. Any agent behavior that contradicts
the Amplifier Principle is wrong — even if it passes every technical check, every
benchmark, and every regulatory gate.

**Practical consequence:** when choosing between two architecturally equivalent
designs, choose the one that keeps the human more visible, more accountable, and
more in control. The system exists to amplify what humans want to do — not to
substitute for their judgment.

---

## Part I — Human-in-the-Loop: Non-Negotiable Initiation Gates

### 1.1 The Three Mandatory Human-Initiation Classes

Regardless of framework (MAESTRO, SWARM, always-on, chain-research), these three
workflow classes **require explicit human initiation before any execution begins**:

| Class | Trigger | Minimum Verification |
| --- | --- | --- |
| **Chain-Research** | Any multi-step autonomous research sequence | GPG-signed initiation token or OIDC assertion |
| **Always-On Agent** | Any persistent / background agent activation | OIDC (real-world certified identity) + 24-hour renewal |
| **Swarm Launch** | Any multi-agent coordinated execution | OIDC + HMAC `approval_token` per-swarm, logged pre-execution |

**Agents cannot self-authorize any of these three classes.** The `approval_token` must be:
1. Issued out-of-band by a verified human operator
2. HMAC-verified by `swarm_approval.py` (orama-system) or `contracts.py` (Perpetua-Tools)
3. Logged *before* the action executes — the audit trail must prove authorization preceded action

If no valid `approval_token` is present → `ValueError`, log the attempt, do not proceed.

### 1.2 Cryptographic Verification Tiers (Tiered by Consequence)

| Tier | Action Class | Required Credential | Implementation |
| --- | --- | --- | --- |
| **T1 — Initiation** | Start chain-research or background agent | GPG or HMAC token | `swarm_approval.py` |
| **T2 — Consequential Output** | Any output leaving the system toward a financial/legal decision | OIDC (real-world certified identity) | GitHub OIDC or OAuth2 PKCE |
| **T3 — Irreversible Action** | Permanent deletion, funds movement, legal filing, system-wide config | One-time HMAC token + OIDC, logged pre-action | `approval_token` + audit log entry |

**T2 and T3 require real-world certified identity.** GPG alone proves cryptographic
key possession — it does not prove real-world identity. OIDC (GitHub, Google
Workspace, or equivalent certified IdP) binds the approval to a verified human being.

### 1.3 The 24-Hour Always-On Renewal Requirement

Always-on agents must request human renewal every 24 hours. This prevents silent
scope creep — the most common failure mode in production always-on systems. Renewal
cannot be auto-acknowledged by another agent; a human must confirm. The operator
verifies the agent is still doing what they think it is doing.

---

## Part II — MAESTRO Framework: Gate Architecture

### 2.1 The Four Gate Classes + Emergency Stop

| Gate | Class | Description | Bypass Allowed? |
| --- | --- | --- | --- |
| **G0 — Passive** | Read/observe only | Agent reads context, no write | No gate needed |
| **G1 — Advisory** | Proposes action, human accepts/rejects | Draft review, analysis output | Human optional review |
| **G2 — Supervised** | Agent acts, human sees every step | Monitored execution | Human may interrupt |
| **G3 — Consequential** | High-impact action requiring pre-approval | Financial output, external API write | Human approval required |
| **G4 — Emergency Stop** | Unconditional halt | Any agent, any state, immediately | **Never bypassable** |

**G4 is not a setting.** It is an architectural node that bypasses the agent entirely.
Agents cannot tamper with their own shutdown. G4 routes around the agent, not through it.

### 2.2 Gate Placement Rules

- Multi-step workflows: G3 required before any external system write
- Parallel swarm branches: merge validation node before final assembly; numerical
  inconsistency triggers G3
- Chain depth > 3 sub-agents: mandatory G2 human checkpoint at each boundary
- Irreversible actions: always T3 credential + G3 gate — never G1 or G2 alone

---

## Part III — SWARM Framework: Accountability at Scale

### 3.1 Swarm Accountability Chain

In a swarm, accountability must never dissolve into "the swarm decided."
Every action traces to:

1. **A named human operator** who issued the `approval_token` for the swarm
2. **A named orchestrator agent** responsible for the swarm's scope
3. **An immutable audit log entry** at every node transition

The human operator's OIDC-verified identity is embedded in the swarm's initiation
record. No swarm may be launched without this record.

### 3.2 Scope Creep Prevention

Agents inside a swarm:
- Cannot expand their scope beyond the original task description
- Cannot spawn sub-swarms without a new `approval_token` from the human operator
- Must log any self-identified scope ambiguity and pause for human clarification
  — not resolve it autonomously

Autonomy drift triggers automatic G3 escalation, not silent continuation.

### 3.3 Compounding Reliability Budget

If each sub-agent is 95% reliable, chaining three yields ~86% overall success.
For financial applications, one erroneous number cascades into an incorrect output.

**Maximum chain depth for critical financial outputs: 3 sub-agents.**
Chains > 3 require mandatory human checkpoints at every boundary.

---

## Part IV — EU AI Act Annex III Compliance Ladder

### 4.1 High-Risk Classification

Most oramasys+perpetua financial use cases (credit analysis, KYC, M&A research,
investment recommendations, fraud detection) qualify as high-risk under EU AI Act
Annex III. The August 2, 2026 enforcement deadline for Articles 6–49 is in effect.

This is not an enterprise-only concern. A personal deployment producing output
that influences a financial decision falls within scope if used commercially
or professionally.

### 4.2 v2.1 → v2.5 Compliance Ladder

| Version | Compliance Deliverable |
| --- | --- |
| **v2.1** | Art. 12: Immutable audit logs at every agent decision point. Art. 14: G3 gates non-bypassable in orchestration graph. |
| **v2.2** | Art. 9: Risk management docs for all Annex III workflows. Workflow Qualification Filter (4/5 green criteria). |
| **v2.3** | Art. 43: Conformity assessments for all high-risk systems. Hallucination Mitigation Stack (5 layers). |
| **v2.4** | Art. 49: Registration in EU AI database. Bayesian RAG replacing deterministic embeddings for financial doc extraction. |
| **v2.5** | Art. 47–48: Declaration of Conformity + CE marking. Full FINRA 2026 guidance integration. Ongoing Art. 9 continuous review cycle. |

### 4.3 Quality Gates (Production Promotion Blockers)

No system promoted to production until all five metrics meet minimum threshold:

| Metric | Minimum Threshold | Target |
| --- | --- | --- |
| Numerical accuracy (RAG extraction) | >90% on quantitative queries | >95% |
| Hallucination rate (source-grounded outputs) | <5% of claims unsourced | <1% |
| Workflow completion rate | >95% without human intervention (Tier 1) | >99% |
| Audit trail coverage | 100% of agent actions logged | 100% |
| Human review gate compliance | 100% — no client deliverable without sign-off | 100% |

Numerical accuracy and hallucination rate are mandatory first gates. No negotiation.

---

## Part V — Hallucination Mitigation Stack (Mandatory — Not Optional)

1. **Task routing** — all numerical calculations → deterministic Python tools, never LLM generative output
2. **Bayesian RAG** — uncertainty-aware retrieval flags low-confidence results; does not silently proceed
3. **Dual-model verification** — high-stakes outputs run a second model pass instructed to find errors in the first
4. **Grounding checks** — every numerical claim must trace to a specific data source cell or API response; no trace → agent flags it, does not render
5. **Analyst review gate** — no generated document reaches a client workflow without human sign-off hardcoded as a non-bypassable orchestration node

---

## Part VI — Baked-In Design Decisions (oramasys-method)

These are architectural constants — not configuration options:

| Decision | Rationale |
| --- | --- |
| `WorkflowQualifier` uses 4/5 (not 5/5) green criteria | Strict 5/5 rejects too many legitimate automations; 4/5 balances safety with utility |
| `MergeValidator` extracts numbers via regex before LLM comparison | Deterministic check — never ask LLM to spot its own inconsistencies |
| `HumanGate` uses `approval_token`, not a boolean flag | Gates cannot be bypassed by setting a config value; require actual out-of-band approval signal |
| G4 Emergency Stop bypasses agent entirely | Agents cannot tamper with their own shutdown |
| Always-On renewal every 24 hours | Operator confirms system is still doing what they think it is |
| T2/T3 require OIDC, not just GPG | GPG proves key possession; OIDC binds approval to a verified human being |
| Connector least-privilege | Each MCP connector exposes only minimum data fields required for its task |
| Short-lived tokens only | No persistent API keys for third-party data connections |
| Cross-app context firewall | Excel context ≠ Outlook context unless human explicitly authorizes cross-app access |
| LangGraph complexity ceiling | Workflows > 7 nodes → decompose into two workflows with human handoff between them |

---

## Part VII — Forward-Looking Statements (v3.x and Beyond)

### 7.1 Intent for v3.x

- **Multi-operator co-signature protocol** — irreversible actions require N-of-M human signers (e.g., 2-of-3), not a single approval
- **Federated identity integration** — OIDC federated across org boundaries so external collaborators issue valid T2/T3 approvals without sharing credentials
- **Automated conformity assessment** — continuous compliance scoring against EU AI Act Annex III, surfaced in the oramasys dashboard
- **Behavioral audit trails** — agents log not just what they did, but what they considered doing and why they did not

### 7.2 Values Anchoring Statement

As oramasys+perpetua grows in capability — more agents, more connectors, longer
autonomous sessions, higher-stakes outputs — the Amplifier Principle becomes
*more* important, not less.

The risk of capability growth without values anchoring is not a technical risk.
It is a civilizational one. The framework is designed to scale human accountability
alongside agent capability, so that at every level of autonomy, a named human being
remains responsible, identifiable, and in control.

This is the foundation of all work in this project.

---

## Pre-Deployment Checklist

- [ ] All five quality gate metrics meet minimum threshold
- [ ] `approval_token` HMAC enforcement live in orchestrator
- [ ] G3 gates non-bypassable in orchestration graph (Article 14)
- [ ] Immutable audit logs at every node (Article 12)
- [ ] Pre-commit hook installed: `bash scripts/install-hooks.sh`
- [ ] OIDC identity verified for all T2/T3 action classes
- [ ] Workflow Qualification Filter applied (4/5 green minimum)
- [ ] Hallucination Mitigation Stack: all 5 layers active
- [ ] Conformity assessment completed for Annex III workflows (Article 43)
- [ ] EU AI database registration complete (Article 49)

---

*Sync this document to Perpetua-Tools `/docs/v2/references/04-HUMAN-ACCOUNTABILITY-FORWARD-PLAN.md`
after every material revision. Last sync: 2026-08-18.*
