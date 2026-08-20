# Critique, Steelman & Iteration: Anthropic-Style Finance AI Agent Framework

## Executive Summary

The framework under review is structurally sound and closely mirrors Anthropic's actual May 2026
financial services launch. However, it contains significant gaps in hallucination risk management,
over-simplified orchestration guidance, compliance blind spots on the imminent EU AI Act deadline,
and no operationally grounded position on Model Context Protocol (MCP) security. This report tears
down each step, steelmans the strongest version of it, then proposes a hardened, production-grade
iteration.[^1]

***

## Step 1: Define the Workflow and Scope

### Critique

The framework correctly targets high-volume, templated financial tasks — exactly the workflows
Anthropic's 10 pre-built agents now cover (pitchbooks, KYC, month-end close, credit memos, audits,
underwriting). But the advice to "identify a workflow with similar characteristics" is too vague for
implementation. It gives no criteria for *excluding* workflows that are actually high-risk to
automate — namely, those with ambiguous inputs, infrequent repetition, or regulatory decision
authority. KYC, for example, involves regulated identity verification with legal liability for
errors. Treating it as a simple templating exercise misframes the governance burden.[^1]

### Steelman

The workflow-first approach is correct because it forces scope discipline before architecture
decisions. The CFA Institute's agentic AI guide for finance explicitly validates this:
"workflow-style automations, which offer more control and predictability, are more likely to be
adopted in practice than highly autonomous, low predictability agents". Decomposing a complex job
into sub-tasks (data gathering → analysis → document generation) is textbook multi-agent design and
is exactly how LangGraph's scatter-gather and pipeline parallelism patterns are implemented in
production.[^2][^3]

### Iterated Version

Add a **Workflow Qualification Filter** before proceeding:

| Criterion | Green (Automate) | Red (Human-Led) | Veto Status |
| --- | --- | --- | --- |
| Regulatory liability | Indirect (drafting) | Direct (decision authority) | **Mandatory Veto Gate** |
| Error consequence | Recoverable | Irreversible or legally binding | **Mandatory Veto Gate** |
| Input variability | Low — structured feeds | High — unstructured, ambiguous | Scored (1 pt) |
| Output verifiability | Machine-checkable | Requires expert judgment | Scored (1 pt) |
| Frequency | High volume, repeating | Low volume, one-off | Scored (1 pt) |

A workflow must achieve Green on both **Regulatory liability** and **Error consequence** as
non-negotiable veto gates. Workflows failing either veto gate must remain human-led. Among the
remaining three scored criteria, at least two must be Green to qualify for automation. KYC screening
should be classified as assisted automation (human-in-loop mandatory), not fully autonomous.[^4][^2]

***

## Step 2: Reference Architecture — Skills, Connectors, Sub-agents

### Critique

The three-layer architecture (Skills / Connectors / Sub-agents) is confirmed accurate by Anthropic's
actual product. However, the framework presents this as a static design pattern without addressing
the **compounding reliability problem**. If each sub-agent is 95% reliable, chaining three steps
together produces only ~86% overall success ($0.95^3 \approx 0.857$), assuming statistically
independent execution across stages — a well-documented production reality. (Similarly, with 97%
per-step reliability, a 5-step chain yields $0.97^5 \approx 0.859$). For financial applications
where one erroneous number cascades into an incorrect pitch or a mismarked credit file, this is not
a theoretical concern but an operational liability.[^5][^6][^1]

The framework also glosses over connector security. The May 2026 Anthropic rollout added D&B,
Experian, GLG, Guidepoint, IBISWorld, and Moody's (600 million companies) — but the framework offers
no guidance on how to govern data access across these connectors. Over-permissioned connectors are
one of the fastest paths to data leakage in MCP-based agent deployments.[^7][^8][^1]

### Steelman

The delivery dichotomy — desktop plug-in vs. managed/hosted agent — is genuinely useful and matches
how Anthropic actually ships these agents: as Office add-ins (Excel, PowerPoint, Word, Outlook are
now GA) and as Claude Managed Agents with per-tool permissions and credential vaults. This framing
correctly identifies the human-in-loop requirement: analysts review and approve all output before
client delivery.[^1]

### Iterated Version

Add explicit **Connector Governance Standards**:

- Apply the **principle of least privilege**: each connector exposes only the minimum data fields
  the sub-agent requires for its task.[^9][^7]
- Use short-lived tokens (not persistent API keys) for all third-party data connections.[^7]
- Implement a **policy enforcement gateway/proxy** that inspects requests and responses for
  sensitive data patterns before they reach the LLM.[^7]
- For all Microsoft 365 integrations, enforce tenant isolation — the agent should not have
  cross-tenant read access even when multiple client files are open.[^7]
- Add a **reliability budget** to the architecture design: target a maximum of 3 chained sub-agent
  steps for any critical financial output. More steps require mandatory human checkpoints between
  them.[^6]

***

## Step 3: Model Selection and Fine-Tuning

### Critique

Citing Claude Opus 4.7 as the base model is accurate — Anthropic reported it led the Vals AI
Finance Agent v1.1 benchmark with a score of 64.37%, while Meta's Muse Spark 1.2 achieved 60.599% on
the Vals Finance Agent v2 benchmark. A benchmark score of ~60–64% indicates that the model succeeds
on a majority of evaluated financial analyst questions under controlled benchmark conditions.
However, benchmark performance evaluates isolated task accuracy; in a live deployment with real-world
data ambiguity, domain-specific edge cases, and end-to-end multi-step dependencies, unassisted
execution carries substantial operational risk. Presenting model selection as a solved problem, with
fine-tuning as a bolt-on enhancement, underestimates the hallucination exposure.[^1]

RAG, which the framework correctly recommends, does not eliminate hallucinations. The CFA
Institute's own RAG for Finance study found a **55% quantitative accuracy rate** on financial
document extraction tasks, with the model hallucinating specific digits even when the correct
document was retrieved. Traditional RAG pipelines rely on deterministic embeddings that cannot
quantify retrieval uncertainty, and residual hallucination remains a documented limitation even in
optimized systems. In a financial context, a hallucinated figure in a credit memo or pitchbook is
not a quirk — it is regulatory and reputational exposure.[^10][^11][^12][^13][^5]

### Steelman

The framework's emphasis on code execution for numerical tasks is the correct mitigation. Using
Python or Excel plug-ins to calculate ratios — rather than letting the LLM estimate them — separates
generative capabilities from deterministic computation. This is the most effective hallucination
mitigation available today.[^11][^2]

### Iterated Version

Add a **Hallucination Mitigation Stack** as a mandatory layer:

1. **Task routing**: Route all numerical calculations and ratio computations to deterministic Python
tools, never to the LLM's generative output.[^2][^11]
2. **Bayesian RAG**: Replace standard deterministic embeddings with uncertainty-aware retrieval that
flags low-confidence retrievals rather than silently proceeding. Research confirms this architecture
reduces overconfident but unreliable outputs.[^12]
3. **Dual-model verification**: For high-stakes outputs (credit memos, audit findings), run a second
model pass specifically instructed to find errors in the first pass.[^6]
4. **Grounding checks**: Every numerical claim in a generated document must be traceable to a
specific data source cell or API response. If a figure lacks a source trace, the agent must flag it
rather than render it.[^14][^10]
5. **Analyst review gate**: No generated document reaches a client workflow without a human sign-off
step hardcoded into the orchestration graph. This is not optional — it is required by EU AI Act
Article 14 for high-risk AI systems.[^15][^16]

***

## Step 4: Workflow Orchestration

### Critique

The recommendation to use LangGraph is well-grounded — it is now among the most widely deployed
orchestration frameworks for production agents, used by LinkedIn, Uber, and Klarna. But the
framework understates LangGraph's operational challenges at scale. Configuration complexity grows
non-linearly: simple workflows require dozens of configuration lines, but complex financial
workflows can require hundreds, with tightly coupled schema updates that break across nodes when
modified. Cyclic workflows, which the framework implies for iterative refinement, introduce
termination condition risks and debugging complexity that are particularly costly in regulated
environments.[^17][^6]

The 99.9th percentile agent session duration doubled from 25 minutes to over 45 minutes between
October 2025 and January 2026, according to Anthropic's own telemetry. Long-running financial tasks
(nightly close, month-end reconciliation) that pause and resume are therefore not edge cases — they
are the normal operating condition for the workflows the framework targets. Yet there is no guidance
on state persistence, failure recovery, or checkpointing.[^4]

### Steelman

LangGraph's stateful design supports step-by-step progress persistence when the graph is compiled with
a configured checkpointer (e.g., `SqliteSaver`, `PostgresSaver`, or `AsyncSqliteSaver`) and invoked
with an explicit `thread_id` in its runtime configuration. Its support for hierarchical and sequential
multi-agent patterns — scatter-gather, pipeline parallelism — maps naturally onto financial
workflows where comparables can be gathered in parallel while narrative is being drafted.[^3][^17]

### Iterated Version

- Mandate **checkpointing at every sub-agent boundary**: compile graphs with a durable checkpointer
  (`SqliteSaver`/`PostgresSaver`) and unique `thread_id`; if any node fails, the orchestrator resumes
  from the last checkpoint rather than restarting the entire workflow.[^3][^6]
- Add a **complexity ceiling rule**: if a workflow exceeds 7 LangGraph nodes, decompose it into two
  separately orchestrated workflows with a human handoff between them. This prevents debugging
  complexity from becoming unmanageable in production.[^17]
- Implement **immutable audit logs** at every node transition, governed by strict data protection
  controls: raw inputs and outputs must undergo automated PII/MNPI redaction before persistence,
  field-level encryption at rest (AES-256), strict least-privilege access controls, and retention
  lifecycle rules (GDPR Art. 5(1)(e) / EU AI Act Art. 12).[^16][^15]
- For the parallel branch pattern (comparables + narrative), add a **merge validation node** that
  checks the two outputs for numerical consistency before assembling the final deck. Inconsistency
  flags trigger a human review step.[^10][^6]

***

## Step 5: Integration with the User's Workspace

### Critique

The Microsoft 365 integration is now confirmed and generally available. But the framework ignores
the security architecture implications of an agent that carries context across Excel, PowerPoint,
Word, and Outlook *simultaneously*. This cross-application context creates an attack surface for
**prompt injection via document content** — a malicious instruction embedded in an incoming email or
a client-supplied spreadsheet could manipulate the agent's behavior across all connected
applications. This is not hypothetical: MCP servers that store authentication tokens for multiple
services represent a high-value target — a breach gives attackers access to all connected service
tokens simultaneously.[^8][^1][^7]

### Steelman

The integration is necessary and valuable. Analysts at major banks spend a large portion of their
day toggling between spreadsheets, slide decks, and email. Eliminating that context-switching is a
genuine productivity gain that justifies the integration complexity.[^1]

### Iterated Version

- Treat every external document (incoming client emails, uploaded spreadsheets, third-party filings)
  as **untrusted input**. Sanitize before passing to the agent context.[^8][^7]
- Implement a **context firewall**: the agent's Excel context should not be accessible from Outlook
  and vice versa unless the analyst explicitly authorizes cross-application access for a specific
  task.[^7]
- Apply OAuth token scoping: Office.js add-in permissions should be limited to the specific document
  the analyst is currently working on, not broad tenant-wide access.[^9][^8]
- Log all cross-application context transfers in the audit trail.[^16]

***

## Step 6: Deploy, Test, and Iterate

### Critique

The framework recommends starting in a sandbox, which is correct but insufficient. It does not
specify *what to measure* or *what failure threshold triggers re-evaluation*. "Compare agent output
to human-prepared pitchbook" is not an actionable quality metric. Hallucination rates of 58-88% have
been documented for general-purpose LLMs on legal questions; even specialized financial models
hallucinate on up to 41% of finance queries according to one compliance AI vendor. Without defined
acceptance thresholds, teams will deploy systems that are still failing at an operationally
unacceptable rate.[^18]

### Steelman

The emphasis on human feedback loops and iterative refinement is correct and matches how Anthropic
describes its own deployment trajectory — rapid growth came only after connectors and model
improvements were compounded through iteration.[^1]

### Iterated Version

Define explicit **Quality Gates** before moving from sandbox to production:

| Metric | Unit & Denominator | Adjudication Method | Minimum Threshold | Target |
| --- | --- | --- | --- | --- |
| Numerical extraction accuracy | % of extracted numerical values (denominator: total benchmark values) | Deterministic cell-by-cell comparison against source filing | >90% | >95% |
| Source-trace coverage | % of rendered numerical/factual claims (denominator: total claims) | AST / citation validator checking source cell or API pointer | 100% | 100% |
| Factual error rate | % of verified factual assertions (denominator: total audited assertions) | Dual-model adversarial check + sample expert human audit | <5% | <1% |
| Workflow completion rate | % of runs reaching terminal state (denominator: total initiated runs) | Orchestrator telemetry without unhandled crash/hang | >95% | >99% |
| Audit trail coverage | % of node transitions (denominator: total state transitions) | Telemetry verification of redacted, encrypted records | 100% | 100% |
| Human review gate compliance | % of client deliverables (denominator: total client exports) | Non-bypassable orchestration barrier with signed approval | 100% | 100% |

Any metric below minimum threshold blocks promotion to production. Numerical accuracy,
source-trace coverage, and factual error rate are mandatory first gates.[^5][^11][^10]

***

## Step 7: Compliance and Transparency

### Critique

This is the weakest section of the framework. It references the EU AI Act and US banking regulations
generically but misses the structured regulatory timeline established by **Regulation (EU) 2024/1689**
as amended by the **Digital Omnibus Regulation (EU) 2026/1744**:

- **August 2, 2026**: Article 50 transparency and disclosure requirements become applicable (mandatory
  labeling of AI interactions, AI-generated outputs, and synthetic content watermarking).
- **December 2, 2027**: Standalone high-risk AI obligations under **Article 6(2) and Annex III**
  (including creditworthiness assessment, risk scoring, and access to financial services) become
  enforceable, requiring risk management (Article 9), technical documentation (Article 11), audit
  logging (Article 12), and human oversight (Article 14).
- **August 2, 2028**: Embedded high-risk systems under **Article 6(1) and Annex I** (systems integrated
  into products under EU safety harmonization laws) become enforceable.[^19][^16]

In the US, FINRA's 2026 Annual Regulatory Oversight Report (released December 9, 2025) added a dedicated
GenAI section emphasizing that broker-dealers deploying AI agents must maintain supervision under
FINRA Rule 3110, govern customer communications under Rule 2210, prevent autonomy drift and scope creep,
and safeguard non-public financial data. While FINRA did not create new standalone statutes, it
signaled intensified examination scrutiny on agent governance. The framework cites none of this,
treating compliance as an afterthought rather than a structural architectural constraint.[^20][^21][^19]

### Steelman

The framework's emphasis on human approval chains and audit trails is genuinely aligned with
regulatory requirements. The insistence that analysts "review, iterate on, and approve Claude's work
before it goes to a client" is not just good practice — it satisfies Article 14's human oversight
mandate for high-risk systems.[^15][^1]

### Iterated Version

Replace the generic compliance section with a **Compliance Implementation Checklist**:

**Immediate (Before Any Production Deployment):**

- [ ] Classify every agent against EU AI Act Annex III high-risk categories. Most financial services
  AI agents (credit scoring, KYC/AML screening, underwriting, investment recommendations) qualify.[^21][^15]
- [ ] Assign a responsible compliance owner to each high-risk system.[^21]
- [ ] Implement encrypted, redacted immutable audit logging at every agent decision point (Article 12).[^16]
- [ ] Hardcode human oversight gates into the orchestration graph — not as a UI option but as a
  non-bypassable workflow node (Article 14).[^15][^16]
- [ ] Align supervision and recordkeeping with FINRA Rule 3110 and Rule 2210 expectations.[^20]

**Before August 2, 2026 (Transparency & Disclosure Phase):**

- [ ] Implement Article 50 transparency notices informing users of AI interactions and synthetic
  content labeling.[^19]
- [ ] Begin preparation for Annex IV technical documentation and conformity assessment workflows.[^21]

**Before December 2, 2027 (High-Risk Enforcement Phase):**

- [ ] Complete conformity assessments for all Article 6(2) / Annex III high-risk systems (Article 43).[^19][^15]
- [ ] Finalize technical documentation per Annex IV.[^21]
- [ ] Register all high-risk AI systems in the EU AI database (Article 49).[^15][^21]
- [ ] Issue Declaration of Conformity with CE marking (Articles 47-48).[^21]

**Ongoing:**

- [ ] Conduct continuous risk management reviews (Article 9 is not a one-time assessment).[^21]
- [ ] Monitor for autonomy drift — agents that begin making decisions beyond their defined scope
  trigger automatic escalation.[^20][^4]
- [ ] Maintain dual compliance for EU AI Act and FCA/US banking/FINRA regulations simultaneously.[^19]

***

## Consolidated Architecture: Hardened Production Blueprint

The table below compares the original framework against the iterated, hardened version across key
design dimensions.

| Dimension | Original Framework | Hardened Iteration |
| --- | --- | --- |
| Workflow qualification | Vague — "similar characteristics" | Explicit 5-criterion filter with mandatory veto gates on Regulatory liability and Error consequence |
| Hallucination mitigation | RAG + code execution (mentioned) | Mandatory 5-layer stack: task routing, Bayesian RAG, dual-model verification, grounding checks, analyst gate |
| Connector security | Role-based access controls (mentioned) | Least privilege, short-lived tokens, policy enforcement gateway, cross-app context firewall |
| Orchestration reliability | LangGraph recommended | LangGraph with durable checkpointer (`SqliteSaver`/`PostgresSaver`) + `thread_id`, 7-node ceiling, merge validation |
| Quality gates | "Compare to human output" | 6 defined metrics with units, denominators, and thresholds; numerical accuracy, trace coverage, and error rate gate production |
| Compliance | EU AI Act + US banking (generic) | Structured EU AI Act roadmap (Aug 2026 Art. 50, Dec 2027 Art. 6(2) high-risk), FINRA 2026 GenAI guidance integrated |
| MCP security | Not addressed | Untrusted input sanitization, token scoping, context firewall, audit log of all cross-app transfers |

***

## Bottom Line

The original framework is a credible starting point and accurately reflects Anthropic's May 2026
financial services product architecture. Its fatal weaknesses are operational, not conceptual: it
treats hallucination as manageable via RAG alone (RAG achieves only 55% quantitative accuracy on
financial documents), understates the compounding reliability problem in multi-agent chains, ignores
MCP security risks that are now documented by FINRA and security researchers, and fails to operationalize
the structured EU AI Act compliance timeline (Article 50 transparency in August 2026, Article 6(2)
high-risk enforcement in December 2027). The hardened iteration addresses each of these gaps while
preserving the framework's valid structural foundation.[^11][^6][^20][^16][^19][^7][^1]

***

## References

<!-- markdownlint-disable MD013 MD032 -->

[^1]: [Anthropic Wall Street agents — Fortune](https://fortune.com/2026/05/05/anthropic-wall-street-financial-services-agents-jamie-dimon/)
[^2]: [Agentic AI for Finance — CFA Institute](https://rpc.cfainstitute.org/research/the-automation-ahead-content-series/agentic-ai-for-finance)
[^3]: [LangGraph Agents in Production — AlphaBOLD](https://www.alphabold.com/langgraph-agents-in-production/)
[^4]: [Measuring AI agent autonomy — Anthropic](https://www.anthropic.com/news/measuring-agent-autonomy)
[^5]: [LLM Hallucinations in financial institutions — BizTech](https://biztechmagazine.com/article/2025/08/llm-hallucinations-what-are-implications-financial-institutions)
[^6]: [Production-Ready AI Agents — LangChain guide](https://dev.to/shreyas1009/building-production-ready-ai-agents-a-langchain-orchestration-guide-6hj)
[^7]: [MCP Security Risks — Veeam](https://www.veeam.com/blog/model-context-protocol-security-risks.html)
[^8]: [MCP Security Risks — Pillar Security](https://www.pillar.security/blog/the-security-risks-of-model-context-protocol-mcp)
[^9]: [Top 10 MCP Security Risks — Akto](https://www.akto.io/blog/mcp-security-risks)
[^10]: [AI hallucinations in M&A due diligence — Deloitte](https://www.deloitte.com/ch/en/services/consulting/perspectives/ai-hallucinations-new-risk-m-a.html)
[^11]: [RAG for Finance — CFA Institute](https://rpc.cfainstitute.org/research/the-automation-ahead-content-series/retrieval-augmented-generation)
[^12]: [Bayesian RAG for financial documents — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12886353/)
[^13]: [RAG system limitations — TechTarget](https://www.techtarget.com/searchenterpriseai/tip/Understanding-the-limitations-and-challenges-of-RAG-systems)
[^14]: [AI hallucinations in financial crime — Tookitaki](https://www.tookitaki.com/blog/ai-hallucinations-financial-crime-governance)
[^15]: [EU AI Act compliance for financial services — Matproof](https://matproof.com/blog/eu-ai-act-compliance-financial-services)
[^16]: [EU AI Act August 2026 deadline — Supra Wall](https://www.supra-wall.com/en/learn/eu-ai-act-august-2026-deadline)
[^17]: [LangGraph multi-agent orchestration — Latenode](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
[^18]: [AI hallucinations in financial services — Aveni](https://aveni.ai/blog/ai-hallucinations-in-financial-services/)
[^19]: [EU AI Act compliance deadline — CompleteFlow](https://completeflow.ai/blog/eu-ai-act-compliance-deadline-august-2026/)
[^20]: [Security Threats in MCP — IJSR PDF](https://www.ijsr.net/archive/v15i3/SR26316110418.pdf)
[^21]: [EU AI Act summary for financial services — EY React](https://eyreact.com/eu-ai-act-summary-financial-services/)

<!-- markdownlint-enable MD013 MD032 -->
