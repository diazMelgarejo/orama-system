# MAESTRO & OWASP GenAI Security Project — Reference

> **Status:** Reference material, additive to existing v2 plans
> **Purpose:** Deep-dive source material on MAESTRO and the OWASP GenAI
> Security Project, gathered to reinforce — not replace — the MAESTRO/OWASP
> coverage already present in [`08-technical-architecture-review.md`](08-technical-architecture-review.md)
> §2.A and [`31-security-harness-excellence-plan.md`](31-security-harness-excellence-plan.md) §4.
> **Source:** Anthropic deep-research pass, 2026-06-18, triggered by
> uploaded summaries of the OWASP GenAI Security Project Virtual Summit
> (Ken Huang / Akram Sheriff, MAESTRO talk).
> **Referenced by:** `08-technical-architecture-review.md` §2.A,
> `31-security-harness-excellence-plan.md` §3–§4, `32-agentic-security-controls.md` §6/§10.

---

## 1. What this file adds beyond the existing MAESTRO/OWASP coverage

The repo already correctly treats MAESTRO and the OWASP Agentic (ASI) Top 10
as complementary (method vs. taxonomy) and already maps several kernel
hooks to MAESTRO layers. This file adds the concrete, citable material that
was missing:

1. A **named threat-ID namespace** (T1–T47) from the OWASP Multi-Agentic
   System (MAS) Threat Modelling Guide v1.0 — the actual cross-reference IDs
   OWASP uses in its own worked examples.
2. **Two open-source MAESTRO tools** (not one) with exact repo locations,
   input formats, and standalone-usability notes.
3. **MCP-specific runtime controls** (tool-hash pinning, micro-segmentation,
   JIT identity) — operational detail beyond "map your controls to a layer."
4. **A quantitative scoring rubric** (OWASP AIVSS) that MAESTRO/ASI lack
   natively.
5. A **provenance correction** on the "five critical areas" framing from the
   summit talk — it is not a single canonical OWASP document.
6. An explicit **numbering-collision flag**: this repo's own threat table in
   `31-security-harness-excellence-plan.md` §3 already uses local IDs T1–T7,
   which collide textually (but not semantically) with OWASP's T1–T47. See
   §6 below for the disambiguation this file proposes.

---

## 2. MAESTRO: method, not a numbered list

MAESTRO = **M**ulti-**A**gent **E**nvironment, **S**ecurity, **T**hreat,
**R**isk, and **O**utcome. Published by Ken Huang (CSA) on 2026-02-06 — but
note the publication-month framing in this repo's existing reference
(`2025-02-06`) should be reconciled; both dates appear across sources and
the canonical CSA blog post should be treated as the source of truth.
MAESTRO is a **layered decomposition method**, not a numbered threat list of
its own — it has no native "MAE.Txx" ID scheme. The numbered T-codes below
come from OWASP's own application of MAESTRO, not from MAESTRO itself.

The 7 layers (confirms and extends `08-technical-architecture-review.md` §2.A,
which currently maps kernel hooks to layers 3, 5, 6, and 7 only):

| Layer | Threats | Current kernel mapping (08 §2.A) |
|---|---|---|
| L1 Foundation Models | Alignment failure, poisoning, adversarial examples, model extraction | **Not yet mapped** |
| L2 Data Operations | RAG/vector-store/embedding poisoning, retrieval attacks | **Not yet mapped** |
| L3 Agent Frameworks | Tool misuse, intent breaking, framework code injection, "no clear trust boundary" | `MiniGraph` (D8) |
| L4 Deployment & Infrastructure | Container escape, network exposure, MLSecOps gaps | **Not yet mapped** |
| L5 Evaluation & Observability | Log manipulation, repudiation, HITL failure | `GossipBus` (P9) |
| L6 Security & Compliance (vertical) | Policy bypass, indirect privilege escalation | `HardwarePolicyResolver` (P8) |
| L7 Agent Ecosystem | Identity spoofing, rogue agents, trust manipulation | HITL Interrupts (4d) |

**Gap flagged, not fixed here:** L1, L2, and L4 have no current kernel-hook
mapping in `08-technical-architecture-review.md`. This is worth a follow-up
pass on that file specifically — L2 (Data Operations / RAG poisoning) is
likely already partially covered by `20-rag-and-memory-design.md` and should
be cross-checked.

**Core principle:** MAESTRO's value is forcing analysis of *cross-layer*
attack chains — vertical propagation (poisoned data at L2 → corrupted model
behavior at L1 → harmful action at L7), horizontal lateral movement within a
layer, and emergent vulnerabilities that exist in no single layer. This is
the same intent behind this repo's existing "T7 Inter-agent cascade" entry
and the SWARM-style system-objective-audit control.

---

## 3. The T1–T47 namespace (OWASP MAS Threat Modelling Guide v1.0, 2025-04-22)

Authored by Ken Huang, Akram Sheriff, John Sotiropoulos, Ron F. Del Rosario,
Victor Lu. Explicit positioning statement from the guide:

> "Rather than proposing a separate threat taxonomy, this guide complements
> existing OWASP work by applying OWASP ASI threats to multi-agent systems
> using MAESTRO."

- **T1–T15**: the OWASP ASI core taxonomy (T1 Memory Poisoning, T2 Tool
  Misuse, T3 Privilege Compromise, T4 Resource Overload, T5 Cascading
  Hallucinations, T6 Intent Breaking & Goal Manipulation, T7 Misaligned &
  Deceptive Behaviors, T8 Repudiation & Untraceability, T9 Identity
  Spoofing, T10 Overwhelming HITL, T12 Agent Communication Poisoning, T13
  Rogue Agents, T14 Human Attacks on MAS, T15 Human Trust Manipulation).
- **T16–T38**: "Extended Threat Scenario" IDs discovered by applying
  MAESTRO to three worked examples (an RPA agent, ElizaOS, Anthropic MCP) —
  e.g. T16 Model Inconsistency, T17 Semantic Drift in Embeddings, T18 RAG
  Input Manipulation, T19 Unintended Workflow Execution, T20 Framework Code
  Injection, T23 Selective Log Manipulation, T24 Dynamic Policy Enforcement
  Failure, T25 Workflow Disruption via Dependency Exploitation.
- **T39–T47 (MCP-specific)**: T39 Unintended Resource Consumption via MCP,
  T40 MCP Client Impersonation, T41 Schema Mismatch, T42 Cross-Client
  Interference via Shared Server, T43 Network Exposure of MCP Server, T44
  Insufficient Logging in MCP, T45 Insufficient Isolation of MCP Server
  Permissions, T46 Data Residency/Compliance Violation, T47 Rogue MCP
  Server in Ecosystem.

**Agentic factors checked at every layer** (per the published guide): Non-
Determinism, Autonomy, Agent Identity Management, Agent-to-Agent
Communication. (The CSA GitHub repo separately names a three-item subset —
Non-Determinism, Autonomy, No Trust Boundary — treat the four-item OWASP
guide list as the more complete reference.)

---

## 4. Two open-source MAESTRO tools (distinct, both usable)

| Tool | Repo | What it does | Standalone? |
|---|---|---|---|
| **MAESTRO Threat Analyzer** | `github.com/CloudSecurityAlliance/MAESTRO` | Next.js + Genkit web app; free-text architecture description in, LLM-driven per-layer threat analysis out (Traditional vs. Agentic threats per layer, with mitigations) | Yes — supports local Ollama via `LLM_PROVIDER`, no OWASP infra required. Explicitly educational, not an audit tool. |
| **OWASP MAESTRO Threat Modeling Playbook** | `github.com/agentic-threat-modeling/MAESTRO` | Markdown/CC-BY-SA playbook usable as an interactive Claude Code agent ("threat model my system"); 10-phase process (Business Context → Architecture → Threat Actor → Trust Boundary → Asset Flow → Threat ID → Mitigation Planning → Code Validation → Residual Risk → Output), resumable via `state.json` | Yes — clone + open in Claude Code |

**Recommendation:** the Playbook is the better fit for a repeatable,
version-controlled threat model committed to this repo (see §7, Stage 2).
The Threat Analyzer is better for rapid per-layer ideation during design.

A third, adjacent tool — **TITO** (`github.com/Leathal1/TITO`) — is a Go SAST
scanner that bakes MAESTRO classification + MITRE ATT&CK mapping into CI
(`tito scan --repo . --maestro --mitre --attack-paths`). No API keys, no
data egress. Worth evaluating as a continuous-assurance complement to the
existing OpenGrep OWASP/CWE rules already in CI (PR #60).

---

## 5. MCP-specific runtime controls (Akram Sheriff)

Directly actionable for `32-agentic-security-controls.md` — these are
concrete mechanisms, not just a threat category:

- **Tool-definition fingerprinting ("tool pinning"):** SHA-256 hash each
  tool definition on first contact, cache the baseline, diff every
  subsequent `tools/list` response against it. Block on mismatch — this
  catches "rug-pull"/tool-poisoning attacks (reference implementations:
  Invariant Labs' `mcp-scan`, the MCPDome gateway).
- **Memory-write controls:** validate every write to agent memory, require
  source attribution, hash content, apply TTLs, isolate by session/user.
- **Micro-segmentation:** isolate MCP servers in dedicated network zones
  with strict traffic filtering; place behind an API gateway doing protocol
  validation, threat detection, and rate limiting.
- **Zero-Trust client controls:** strict allowlists + schema enforcement,
  containerized/sandboxed execution, JIT narrowly-scoped permissions,
  registry-only discovery + origin verification, OAuth 2.1 identity
  gateway, anomaly detection on tool calls.

Primary sources: OWASP MAS Guide §5 (MCP worked example, T39–T47); OWASP
*Practical Guide for Securely Using Third-Party MCP Servers* (v1.0,
2025-10-23).

---

## 6. Numbering collision: this repo's local T1–T7 vs. OWASP's T1–T47

**Flagged, not silently resolved.** `31-security-harness-excellence-plan.md`
§3 already has a 7-row threat table using local IDs T1 through T7. These are
**this repo's own IDs**, defined before this research pass, and are
unrelated to the OWASP MAS Guide's T1–T47 — but the textual collision (same
prefix, same numbers 1–7) will confuse anyone cross-referencing both
documents. Approximate OWASP-equivalent mapping for orientation only — **do
not treat this as a renumbering**:

| This repo's local ID (31 §3) | Closest OWASP T-code(s) | Closest ASI code |
|---|---|---|
| T1 LAN control-plane exposure | T43 Network Exposure of MCP Server | ASI03 Identity & Privilege Abuse |
| T2 Prompt injection to tool misuse | T2 Tool Misuse, T6 Intent Breaking | ASI02 Tool Misuse & Exploitation |
| T3 Memory poisoning | T1 Memory Poisoning | ASI06 Memory & Context Poisoning |
| T4 Credential exposure | T22 Service Account Exposure | ASI03 Identity & Privilege Abuse |
| T5 Unbounded consumption | T4 Resource Overload | (OWASP LLM10 Unbounded Consumption) |
| T6 Supply-chain compromise | T25 Workflow Disruption via Dependency Exploitation | ASI04 Agentic Supply Chain Vulnerabilities |
| T7 Inter-agent cascade | T5 Cascading Hallucinations, T12 Agent Communication Poisoning | ASI08 Cascading Failures |

**Recommendation for a future pass (not done in this commit):** prefix this
repo's local threat IDs (e.g. `PT-T1`…`PT-T7`) to remove the textual
collision, or add an explicit "(local ID, not an OWASP T-code)" footnote at
the table header in `31-security-harness-excellence-plan.md` §3. Left as an
open item rather than renaming unilaterally, per the integrative-not-
replacing instruction this file was written under.

---

## 7. Quantitative scoring: OWASP AIVSS

MAESTRO and the ASI Top 10 are qualitative. **OWASP AIVSS** (AI Vulnerability
Scoring System; led by Ken Huang, Michael Bargury, Vineeth Sai Narajala,
Bhavya Gupta) adds a 0–10 score combining a CVSS base with an Agentic AI
Risk Score (AARS) over 10 factors: Autonomy of Action, Tool Use, Memory Use,
Dynamic Identity, Multi-Agent Interactions, Non-Determinism,
Self-Modification, Goal-Driven Planning, Contextual Awareness, Opacity &
Reflexivity (each scored 0.0/0.5/1.0).

- v0.5 formula: `AIVSS = ((CVSS_Base + AARS) / 2) × ThM` (ThM defaults 0.97).
- v0.8 (current, released 2026-03-19) refines this to a force-multiplier
  model: `AIVSS = (CVSS_Base + AARS_Uplift) × Mitigation_Factor`, where
  `AARS_Uplift = (10 − CVSS_Base) × (FactorSum / 10) × ThM`, and Mitigation
  Factor ∈ {1.00 none/weak, 0.83 partial, 0.67 strong (provisional)}.

**Status: pre-1.0, evolving.** Do not hard-code this formula into policy
until a v1.0 release; treat as a candidate prioritization layer for threats
surfaced by a MAESTRO pass (§4 Stage 2 below), not yet a committed scoring
standard for this repo.

---

## 8. Provenance correction: the "five critical areas" framing

The summit talk's five-item framing (non-determinism, autonomy, expanded
security boundaries, ephemeral identity, blast radius) is **Ken Huang's talk
framing, not a single canonical OWASP document**. Per-concept grounding:

| Concept | Where it's actually documented |
|---|---|
| Non-determinism, Autonomy | Named factors in both the OWASP MAS Guide and the CSA MAESTRO repo |
| Expanded security boundaries | CSA repo's "No Trust Boundary"; developed in Huang's "Is Agentic AI Layer 8?" Substack |
| Ephemeral identity | AIVSS's "Dynamic Identity" factor; developed in Huang's "Agentic AI Identity Management Approach" (CSA, 2025-03-11) — advocates short-lived, task-scoped credentials, DIDs/verifiable credentials |
| Blast radius | A descriptive risk concept in MAESTRO's Risk component, not a named factor anywhere |

If this repo cites the five-area framing elsewhere, attribute it as "Ken
Huang's framing" rather than implying a single OWASP source document.

---

## 9. Staged recommendations (additive to `31` §9 Quarterly Standards Refresh)

1. **Now:** add the T1–T47 namespace as a citable reference (this file);
   resolve the numbering-collision flag in §6 on a future pass.
2. **Next:** commit the OWASP MAESTRO Playbook into this repo and run it
   once against the 7-agent architecture; record `state.json` as an audit
   artifact. Fill the L1/L2/L4 gap in `08-technical-architecture-review.md`
   §2.A.
3. **Then:** implement the four MCP runtime controls (§5) in
   `32-agentic-security-controls.md` — tool-hash pinning fits naturally
   alongside its existing §6 (Prompt-injection scanner) and §4 (Tool-executor
   mediator) sections.
4. **Ongoing:** re-check for an AIVSS v1.0 release and a MAS Guide v2 before
   treating either as a committed standard (already covered by `31` §9's
   quarterly refresh cadence — add AIVSS and the MAS Guide to that source
   list explicitly).

---

## 10. Source quality notes

Primary sources (high confidence): CSA MAESTRO blog; OWASP MAS Threat
Modelling Guide v1.0 (full text retrieved); CSA MAESTRO GitHub repo; OWASP
MAESTRO Playbook repo; OWASP Top 10 for Agentic Applications 2026
announcement (2025-12-09); OWASP MCP guidance pages; AIVSS v0.5 PDF (formula
verified verbatim); Huang's CSA identity posts.

Secondary/aggregator sources (corroboration only): Snyk Labs, Practical
DevSecOps, Medium, vendor blogs. The AIVSS v0.8 force-multiplier formula
specifically comes from the official calculator + secondary writeups, not
verified verbatim from the v0.8 PDF body — re-verify before treating as
canonical.

This file reinforces, and does not replace, the MAESTRO/OWASP coverage in
`08-technical-architecture-review.md` and `31-security-harness-excellence-plan.md`.
