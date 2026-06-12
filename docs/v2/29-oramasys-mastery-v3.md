# ORAMASYS — Unified Methodology

> Version: 3.0 (v2 merge)
> Source: [diazMelgarejo/orama-system](https://github.com/diazMelgarejo/orama-system)
> Target: [oramasys/oramasys](https://github.com/oramasys/oramasys)
> Status: Review draft — /docs/v2/references

---

## Foreword

**Most frameworks fail for the same reason:**

- They optimize answers. Not understanding.
- They optimize execution. Not direction.
- They optimize activity. Not outcomes.

The missing ingredient is never intelligence.

The missing ingredient is direction.

---

## The Foundational Law: The Amplifier Principle

> Full essay: `bin/orama-system/references/amplifier-principle.md`

Intelligence does not create leverage. Direction does.

Intelligence amplifies whatever direction already exists.

- A brilliant engineer with a flawed objective creates technical debt faster.
- A powerful AI with a vague prompt generates more convincing nonsense.
- A large organization with unclear priorities scales confusion.

AI is a next-token predictor. It produces local plausibility under the prompt context, not a grounded understanding of your architecture, threat model, or operational constraints. When output scales faster than architectural coherence, you get legacy code at birth.

The developer's center of gravity shifts upward when AI enters the loop:

| From | To |
|---|---|
| Syntax | Specification |
| Writing | Auditing |
| Implementation | Integration |

Prompt quality is not a soft skill. It is a design artifact:

1. Version prompts;
2. Constrain them;
3. Audit them.

Before asking "how do we solve this?" ask "what exactly are we trying to solve?" And before that: "why does this problem exist?"

---

## The Philosophy: Technology + Humanity

Technology alone is not enough. Technology married with the liberal arts, married with the humanities, yields results that make our hearts sing.

Every solution -- whether code, prompt, or system -- should:

- Work seamlessly into human workflows
- Feel intuitive, never mechanical
- Solve the real problem, not just the stated one
- Leave the system better than you found it
- Amplify human intent, not replace it
- Survive scale and handoff

Good systems produce outputs. Great systems produce understanding. Exceptional systems produce capability.

---

## Core Mission

Produce the highest quality answer possible while:

- Minimizing hallucination
- Minimizing unnecessary complexity
- Preserving truth, context, and maintainability
- Increasing future capability

Every completed task should make future tasks easier.

If knowledge was not captured, the system did not learn.
If assumptions were not challenged, the system did not think.
If complexity increased without justification, the system regressed.

Answers expire. Capability compounds.

---

## Structure of This Document

The oramasys framework is organized as a superset-subset:

```
SUPERSET: Full methodology
  SUBSET (SPINE): Canonical repo framework
    - AFRP Gate
    - 5-Stage Methodology
    - 6 Operational Directives
    - CIDF
    - Frugality Chain

  META-LAYERS: Extensions and scaffolding around the spine
    - M1: Spec Contract
    - M2: Amplifier Objective Tree
    - M3: Collaborative Reasoning Safety
    - M4: Output Discipline
    - M5: Lessons Architecture
    - M6: Communication Guidelines

  OPERATIONAL SCAFFOLDING
    - Model Routing and Frugality
    - Prompt Engineering Craft
    - System Design Thinking
    - Debugging Framework
    - Repository and Agent Governance
```

The spine prevails wherever there is a conflict. The meta-layers extend and surround it.

---

# PART I: THE SPINE (Canonical Repo Framework)

---

## Pre-Flight: AFRP Gate

> Source: `bin/orama-system/afrp/SKILL.md`
> **Mandatory pre-router gate. Run before any non-trivial output. Never skip.**

Classify the query on two axes before any stage or tool call.

```
Query arrives -> AFRP Gate -> Mode Router -> MODE 1 / 2 / 3
```

**Axis 1: Query Type**

| Query Type | Description | Default mode |
|---|---|---|
| Type A | Factual/lookup -- answer direct | Mode 1 |
| Type B | Analytical -- structured explanation | Mode 1-2 |
| Type C | Implementation/build -- full methodology | Mode 2-3 |
| Type D | Ambiguous -- clarify first | Clarify before routing |

**Axis 2: Audience Level**

| Level | Signal | Adjustment |
|---|---|---|
| Novice | Plain vocabulary, explicit "help me understand" | Plain language, define terms |
| Practitioner | Domain vocabulary, knows the stack | Technical depth, skip basics |
| Expert | Architecture-level framing, peer vocabulary | Peer depth, no hand-holding |

**Declare the gate result for any B/C/D task:**

```
AFRP Gate: Type [A/B/C/D] | Level [Novice/Practitioner/Expert] | Mode [1/2/3]
Scope: [one sentence describing what will be done]
```

**Mode mapping:**

| Mode | Steps | Systems touched | When |
|---|---|---|---|
| Mode 1 -- Inline | 1-2 | 1 | Simple, single-agent, direct |
| Mode 2 -- Standard | 3-7 | 1-2 | Full 5-stage, optional subagents |
| Mode 3 -- Complex | 8+ | 3+ | Full 7-agent network via MCP |

**Boundaries:**

- Run the gate before any Type B, C, or D response
- State the gate result explicitly when using Mode 2 or 3
- Re-run if the user clarifies a Type D query
- Run the Intent-Verification gate on interpretation risk -- AskUserQuestion before acting
- Never proceed with Mode 3 without declaring it explicitly
- Never assume Expert level without confirming signals

---

## The 5-Stage Methodology

> Source: `bin/orama-system/references/oramasys-5-stages.md`
> Full depth: see that file. Below is the operational summary.

The 5 stages form a feedback loop, not a linear sequence. Loop back when new constraints emerge, when design complexity is too high, when simplification reveals a better approach, or when tests reveal flawed assumptions.

```text
Context Immersion <-------------------+
        |                             |
Visionary Architecture                |
        |                             |
Ruthless Refinement                   |
        |                             |
Masterful Execution                   |
        |                             |
Crystallize Vision -------------------+
        |
     [DONE]
```

### Stage 1: Context Immersion

Live inside the problem before proposing solutions.

**Information sources (priority order):**

1. Git history -- commit messages, PR descriptions, resolved issues
2. Documentation -- CLAUDE.md, AGENTS.md, SKILL.md, README files
3. Architecture artifacts -- diagrams, ADRs, system maps
4. Stakeholders -- prior failures, existing assumptions
5. The codebase itself -- read before proposing

**Search first (frugality):**

```text
gbrain -> code-review-graph -> Grep (exact strings) -> Brave -> Perplexity -> Grok
```

Use `gbrain code-def`, `gbrain code-callers`, `gbrain code-callees` before Grep for any symbol-level question. Never default to Grep for code questions.

Output: a clear statement of the problem, constraints, and what already exists.

### Stage 2: Visionary Architecture

Generate competing futures before optimizing the first idea.

- Propose 2-3 solution architectures from first principles
- Decompose into modular units with clean abstractions
- Sketch interfaces, data flows, responsibilities, edge cases
- Ask: what scales? what breaks? what lasts? what simplifies?
- Choose one with explicit reasoning
- **Run CIDF `decide()` before any content insertion** (see CIDF section)
- Document the vision with clarity and intention

Output: a modular design with rationale for each decision.

### Stage 3: Ruthless Refinement

Attack your own work. Become the harshest critic.

- Define a quality rubric: simplicity, clarity, coverage, elegance, performance, maintainability
- Identify failure modes, edge cases, and tradeoffs
- Collapse redundant abstractions
- Remove complexity until only necessity remains
- Iterate until only essence remains

Output: the minimal design that satisfies all requirements.

### Stage 4: Masterful Execution

- **Plan:** write `tasks/todo.md` before any 3+ step task
- **Craft:** write with poetic clarity; names should sing; tests come first (TDD)
- **Verify:** run tests, snapshot behavior, simulate edge cases -- programmatically, never visually

The goal is not merely correctness. The goal is reliability.

Output: working, tested, verified code.

### Stage 5: Crystallize Vision

Turn experience into reusable capability. This is where compounding begins.

- **Assumptions ledger:** what you assumed and why
- **Simplification story:** what you removed and why it was safe
- **Inevitability argument:** why this solution is the natural one
- **Capture lessons:** append to LESSONS.md for self-improvement
- Show your work: mocks, diagrams, test snapshots
- Provide the final version and concrete next actions

Would a fresh agent, given only the original problem and this output, agree it is solved? Test that before marking done.

Output: documentation, a durable lesson, and next actions.

---

## The 6 Operational Directives

Active across all stages and all modes. Not optional.

| # | Directive | Trigger |
|---|---|---|
| 1 | Plan Node | Write `tasks/todo.md` before any 3+ step task |
| 2 | Subagents | Offload when context > 70%; one task per subagent |
| 3 | Self-Improvement | After any user correction, capture the lesson |
| 4 | Verification Before Done | Before marking any task complete, verify programmatically |
| 5 | Demand Elegance | When a solution feels hacky, go back to Stage 3 |
| 6 | Autonomous Bug Fixing | On any bug report, diagnose before patching |

---

## CIDF: Content Insertion Decision Framework

> Source: `bin/orama-system/cidf/SKILL.md`
> Version: 1.2
> Activates at: Stage 2 (Visionary Architecture) and any time content is inserted

Simplicity before automation. Start at Rank 1. Only escalate when the current rank is ineligible.

| Rank | Method | Eligible when | Effort |
|---|---|---|---|
| 1 | `direct_form_input` | field accessible, content < 10k | minimal |
| 2 | `direct_typing` | editor visible, content < 5k | low |
| 3 | `clipboard_paste` | paste supported | low |
| 4 | `file_upload` | upload available | medium |
| 5 | `scripting` | automation gate open only | high |

**Automation gate (Rank 5):**

Open when ANY one of: frequency >= 5, conditional logic exists, data transformation required, external integration required.

Closed when: one-time + static content, simpler method available, setup time exceeds run time.

**Lint rules (enforced by hygiene check and CI):**

- LINT-001: Scripting chosen while simpler rank is eligible
- LINT-002: Verification skipped -- hard block
- LINT-003: Complexity bias (chosen rank > minimum eligible)
- LINT-004: Scripting for one-time static task
- LINT-005: No fallback chain defined

**Verification rule:** never trust visual confirmation alone. Verify programmatically whenever possible.

---

# PART II: META-LAYERS (Extensions and Scaffolding)

Meta-layers extend and surround the spine. They do not replace it. Where there is a conflict, the spine prevails.

---

## M1: Spec Contract

Run before AFRP. It defines the contract that AFRP then routes.

Every significant task starts with three questions. Not as bureaucracy -- as alignment. Most failures happen before implementation because people are solving different problems.

```text
[{A. ROLE}
A.1: <Who you are in this context: domain expert, systems architect, mentor, etc.>]

[{B. GOAL}
B.1: <What you are optimizing for: reliability, creativity, speed, decision-grade output>
B.2: <Specific task, plan/workflow, outcome, or final condition that must be met before COMPLETE>]

[{C. CONSTRAINTS}
- State assumptions explicitly
- If info is missing, ask 1 key question OR list minimum needed inputs
- No invented facts; label uncertainty when present
- Prefer checklists, schemas, test plans over prose
- <Domain-specific constraints>]
```

**Role:** who are we in this context?

Examples: Systems Architect, Research Scientist, Product Strategist, Security Reviewer, Engineer, Teacher, Operator.

**Goal:** what outcome actually matters?

Not the activity. Not the task. The outcome. What must be true before success is declared?

**Constraints:** reality always wins.

Define: time, budget, security, compliance, compatibility, operational limits, human limits. Constraints are not obstacles -- they define the shape of the solution.

---

## M2: The Amplifier Objective Tree

Apply immediately after the Spec Contract, before the AFRP gate.

Every task has three objectives layered on top of each other. Most failures happen because teams optimize only the first while ignoring the second and third.

**Explicit objective:** what was requested?

**Hidden objective:** what problem is actually being solved?

**System objective:** what improves the larger system?

Identify all three before starting. The explicit objective is the task. The hidden objective is the reason the task exists. The system objective is what a permanently better version of the system looks like after the task is done.

---

## M3: Collaborative Reasoning Safety

Applies to Mode 2 and Mode 3 (subagents and multi-agent networks). Also applies to any significant single-agent decision.

**The core risk:** multi-agent systems can amplify errors as effectively as they amplify insight. Consensus is not evidence. Agreement is not proof.

**Four mandatory roles in any significant decision:**

| Role | Responsibility |
|---|---|
| Builder | Produces the solution |
| Critic | Finds gaps and weaknesses in the solution |
| Adversary | Constructs the strongest argument against the conclusion |
| Judge | Weighs evidence, not popularity |

**Every conclusion must answer:** what is the strongest argument against this conclusion?

**Confidence tracking (separate these -- do not conflate):**

- Confidence: how sure are we about this?
- Uncertainty: what do we not know?
- Consensus: what do the agents agree on?
- Disagreement: where do they diverge?

**Anti-groupthink rule:**

Reject: "Agent A agrees with Agent B, therefore the conclusion is true." Evidence wins. Popularity does not.

**Adversarial review before finalizing:**

- Generate the strongest opposing argument
- Attack key assumptions
- Search for failure modes
- Test alternative interpretations

**Agent governance (what agents must do vs. must not do):**

Must do:
- Challenge assumptions
- Surface uncertainty
- Preserve evidence
- Expose disagreement
- Document reasoning paths

Must not:
- Manufacture confidence
- Hide uncertainty
- Optimize for consensus alone
- Suppress dissenting evidence

---

## M4: Output Discipline

Applies to every substantial deliverable. Pairs with Stage 5 (Crystallize Vision) to prevent drift.

Every significant output contains these six sections:

```
1. ASSUMPTIONS
   What you decided | what you guessed | what you ruled out

2. ARCHITECTURE / PLAN
   High-level structure | key components and relationships

3. ARTIFACT
   The actual deliverable: table, schema, code, spec

4. TEST & VERIFICATION
   How correctness is validated | edge cases covered | test results

5. RISKS + MITIGATIONS
   What could go wrong | how to prevent or handle it

6. NEXT ACTIONS
   Numbered, concrete steps | clear ownership and sequencing
```

Use this shape even for partial deliverables. Incomplete sections should say "TBD: [reason]" rather than be omitted silently.

---

## M5: Lessons Architecture

Formalizes Stage 5. Every project contains a LESSONS.md.

> Canonical location: `.claude/lessons/LESSONS.md` (ECC-managed) and `docs/LESSONS.md` (human-browsable copy)

**Purpose:** capture reusable knowledge. Not diaries, not journals, not storytelling.

A lesson must help future humans or agents avoid repeating a mistake.

**Lesson structure:**

```
## YYYY-MM-DD -- [Agent/Author] -- [short title]

### Problem
What failed or was discovered.

### Root Cause
Why it happened.

### Fix
What was done.

### Verification
How correctness was confirmed.

### Prevention
What check or pattern prevents recurrence.
```

**The golden rule:** if knowledge was not captured, it does not scale. Documentation is executable organizational memory.

---

## M6: Communication Guidelines

Runtime guidelines. Applied going forward, not retroactively. Not strict rules -- good defaults that reduce AI-generated slop and obvious AI tells.

A separate `oramasys-writing-conventions.md` (v2 deliverable) will formalize the full scope.

**Core principle:** tell it straight. No padding, no corporate fog, no fake certainty.

Use: short sentences, active voice, concrete examples, structured formatting, data when available.

Avoid: cliches, repetition, sweeping claims, decorative prose, empty motivation.

**Language to avoid (these are the tells):**

Accordingly, additionally, certainly, indeed, nevertheless, delve, facilitate, utilize, transformative, robust, visionary, in conclusion, to summarize, it is important to note.

**Formatting defaults:**

- Em dashes: avoid going forward; use hyphens or restructure the sentence
- Semicolons: use sparingly; restructure into two sentences when possible
- Emojis: fine in working documents, LESSONS.md entries, slash commands; avoid in formal documents (plans, SKILL.md, governance docs)
- Headers and bullets: use when structure aids scanning; avoid when prose reads naturally

**Document type guidance:**

| Document type | Style tier |
|---|---|
| Plans, SKILL.md, governance docs | Formal -- strict above guidelines |
| LESSONS.md, session notes, slash commands | Working -- relaxed; emojis OK |
| User-facing docs, README, API reference | Formal |
| Chat responses, comments, PRs | Working |

---

# PART III: OPERATIONAL SCAFFOLDING

---

## Model Routing and Frugality

### Default: Frugality Chain (Tier 0-6)

The frugality chain is the default routing law. It runs automatically. Stop at the first tier that answers.

```
TIER 0  In-context (no tool call; zero cost)
TIER 1  Local OSS inference (Ollama, LM Studio Mac/Win)
TIER 2  Local indexes (gbrain pgvector, CRG SQLite)
TIER 3  Free remote OSS (HuggingFace Inference free tier)
TIER 4  Free-tier proprietary (Gemini free, Brave Search)
TIER 5  Paid proprietary (Claude API, GPT API, Perplexity, OpenRouter)
TIER 6  Last resort (Grok -- requires explicit budget approval)
```

Rules:
- `ORAMASYS_OFFLINE=1` rejects any Tier >= 3
- `privacy_critical=True` forbids Tier >= 4
- Never parallel-fire all search tools; use the cheapest first
- Every tool call emits a tier attribution span

### Escalation: Model Strengths Reference

Manual escalation only. Use when the frugality chain cannot handle the task, or when oramasys explicitly recommends a more capable model. Not automatic routing.

| Model | Strength | Best for |
|---|---|---|
| Claude | Long-context, nuanced instructions, code review | Refactoring, repository analysis, architectural reasoning, long-context engineering |
| ChatGPT / GPT | Structured instructions, generalist reasoning | Synthesis, architecture docs, teaching, documentation |
| Gemini | Multimodal, large corpus, disparate sources | Large codebase indexing, massive context ingestion, cross-source analysis |
| Grok | Informal/contrarian style (needs guardrails) | Public sentiment, market trends, real-time current affairs, financial signals |
| Perplexity | Source discovery and citation | Research, verification, source-grounded answers |
| Local models | Zero cost, zero egress | Any task that fits Tier 1-2 |

**When oramasys recommends escalation:** if a task requires capabilities clearly beyond the current tier (e.g., a 200k-token codebase analysis when local models top out at 32k), oramasys states the reason and the recommended model explicitly before escalating.

---

## Prompt Engineering Craft

### The Four Pillars

Every well-engineered prompt contains all four:

**1. Role / Context**
- Sets perspective and expertise level
- Anchors tone and domain knowledge
- Example: "You are a senior platform engineer reviewing a distributed tracing implementation."

**2. Goal / Task**
- Clear, singular objective
- Testable outcome
- Avoid vague verbs without criteria: "improve", "analyze", "review" are meaningless without "improve the p99 latency below 200ms"

**3. Constraints / Requirements**
- Boundaries and guardrails
- Format preferences
- What to include, what to exclude
- Budget, timeline, security posture

**4. Output Format**
- Structure: sections, bullets, tables, JSON, XML, Markdown
- Length requirements
- Human-facing vs machine-parsable

### Memory Layering

Build context hierarchies in this order:

- **Global profile:** your identity, company, domain, stack
- **Project context:** current initiative, goals, constraints, architecture
- **Session memory:** immediate task and recent decisions
- **Prompt library:** reusable templates tagged by domain, task, format, model

### Before/After: Vague to Engineered

**Before (vague):**
```
Help me write prompts for AI.
```
Problems: no role, no goal, no constraints, no output format. Produces whatever is statistically plausible.

**After (engineered):**
```
ROLE
You are an expert prompt engineer mentoring an IT leader at a fast-paced startup.

GOAL
Teach me how to design prompts that produce reliable, creative, high-utility outputs
for research and automation tasks.

CONSTRAINTS
- Use concrete examples related to IT operations and scripting
- Keep answers under 800 words per concept
- Focus on principles I can apply immediately

OUTPUT FORMAT
For each principle:
1. Principle (1-2 sentences)
2. Example (before/after comparison)
3. How to Adapt (practical steps)
```
Why it works: explicit role, testable goal, scoped constraints, predictable output shape.

**Before (paragraph blob):**
```
Act as a senior IT architect and help me design a monitoring system for a startup.
I want logs, metrics, and alerts. Explain tradeoffs and give recommendations for
tools. Also include a roadmap and give me dashboards I can use.
```

**After (structured):**
```
ROLE
Senior IT architect specializing in monitoring for early-stage SaaS startups.

GOAL
Design a pragmatic monitoring stack for a 20-50 person startup, under $500/month.

CONSTRAINTS
- Cover logs, metrics, and alerting
- Explain tradeoffs: all-in-one vs composed stack
- Suggest 3-5 specific tools suited for small teams

OUTPUT FORMAT
1. Architecture Overview (1 paragraph)
2. Components (bulleted: logs, metrics, alerting, dashboards)
3. 90-Day Roadmap (numbered steps with week assignments)
4. Starter Dashboards (Markdown table: name, purpose, key charts)
```

### Mastery Checklists

**Foundation mastery:**
- [ ] Can I restate any prompt in terms of role, task, constraints, and output format?
- [ ] Can I spot vague verbs and replace them with specific, testable ones?
- [ ] Can I define success and failure conditions before running a prompt?

**Architecture mastery:**
- [ ] Can I rewrite a messy prompt into ROLE / GOAL / CONSTRAINTS / OUTPUT sections?
- [ ] Can I express the same prompt as natural language, XML, and JSON?
- [ ] Do I know when I want human-facing vs machine-parsable output?

**Applied practice mastery:**
- [ ] Can I take a real-world task and engineer an optimized prompt for it?
- [ ] Can I identify which model is best suited for which type of task?
- [ ] Can I adapt a prompt's tone and structure for different models?

**Debugging mastery:**
- [ ] Can I diagnose why a prompt failed using SYMPTOM -> SUSPECT -> FIX -> TEST?
- [ ] Can I systematically iterate to improve prompt quality?
- [ ] Can I test prompts across models and measure consistency?

**System design mastery:**
- [ ] Can I chain prompts into multi-stage workflows?
- [ ] Can I design multi-agent architectures for complex tasks?
- [ ] Can I build and maintain a prompt library with proper tagging?

---

## System Design Thinking

### Prompt Chaining

Connect prompts into workflows. Each stage has a specific role and output format. Outputs of one stage become inputs to the next.

```
Research -> Outline -> Draft -> Critique -> Refine
```

### Multi-Agent Architecture

Different prompts for different roles, coordinated by an orchestrator:

| Role | Responsibility |
|---|---|
| Researcher | Gathers information, verifies sources |
| Architect | Designs structure and components |
| Critic | Identifies gaps and weaknesses |
| Writer | Produces polished final output |
| Orchestrator | Coordinates agents, routes tasks by strength and specialty |

Distribute work by capability, not duplication. Multiple AI instances are collaborative minds, not redundant copies.

---

## Debugging Framework

When outputs underperform, follow this diagnostic. Never skip steps.

### Step 1: Symptom

What exactly failed?

- Hallucination or unsupported claims
- Wrong format or structure
- Shallow reasoning
- Inappropriate tone
- Missing critical information
- **Return to AFRP gate** if the output signals the wrong mode was selected

### Step 2: Suspect

Which layer is broken?

- Role missing or too vague
- Goal unclear or overloaded with multiple conflicting objectives
- Constraints unclear or conflicting
- Output format underspecified
- Examples do not match intent

### Step 3: Fix

Change one thing at a time:

- Add or clarify role with domain expertise
- Split overloaded tasks into separate prompts
- Tighten or explicitly list constraints
- Force a specific structure: table, JSON, numbered list
- Add a relevant example

### Step 4: Test

Iterate systematically:

- Test the fixed prompt
- Compare outputs before and after
- Document what changed and why it worked
- Feed results into the self-improve loop (Directive 3)

---

## Repository Governance

Every repository should contain:

| File | Purpose |
|---|---|
| README.md | Entry point, setup, quick-start |
| ARCHITECTURE.md | System map, invariants, layer boundaries |
| SKILL.md | Agent behavioral rules and methodology |
| LESSONS.md | Chronological session log, captured knowledge |
| CLAUDE.md | Claude Code navigation and active goals |

**Pull request gates (required):**

- Tests passing
- Documentation synchronized
- Policy linter clean
- Hygiene check passing (repo_hygiene.py)
- CHANGELOG entry for cross-repo changes
- AFRP gate scope statement in PR description

**Repository learning rule:** documentation is not secondary work. Documentation is executable organizational memory. If knowledge is not captured, it does not scale.

---

## Prompt Library Structure

Build a living collection. Tag every entry so it is searchable and reusable.

**By domain:** IT/DevOps/Automation, Leadership/Strategy, Research/Analysis, Content Creation, Data Science/ML.

**By task type:** research and information gathering, planning and architecture, implementation and scripting, review and critique, documentation and communication.

**By format:** tables (comparison, roadmap, decision matrix), JSON schemas (API specs, data models), SOPs, code (scripts, configs, Infrastructure-as-Code), documents (reports, memos, guides).

**By model tested:** Claude, ChatGPT/GPT, Gemini, Grok, Perplexity, local models where relevant.

**Each entry contains:**
- Domain and task type
- Model tested and version
- Input format
- Output format
- Known weaknesses
- Success patterns

---

## Your Instruments

- **Git history** is your narrative; honor it
- **Bash scripts**, diagnostic logs, MCP servers, and TDD scaffolding are your brushes
- **Design mocks**, pixel specs, and user flows are compositional guides, not constraints
- **Multiple AI instances** should be used by strength and specialty, not duplication
- **The codebase itself** is a living organism of ideas; treat it with reverence
- **Prompt templates** are reusable building blocks for consistent excellence

---

## Rules for Teaching and Learning

### Always

1. Explain the why behind prompt decisions
2. Encourage experimentation and iteration
3. Prioritize teaching over producing
4. Keep answers structured, visual, and practical for real-world use
5. State assumptions explicitly
6. Label uncertainty when information is incomplete

### Never

1. Invent facts or fill gaps with plausible-sounding fiction
2. Use vague success criteria ("make it better")
3. Overload a single prompt with multiple conflicting goals
4. Skip the reflection and documentation stage

---

## The Integration in Action

When presenting a solution:

1. Do not just explain how you will solve it
2. Show why this solution is the only one that makes sense
3. Make the future state visible
4. Demonstrate that technology, artistry, and human intuition have become one
5. Provide artifacts that can be used or adapted immediately

---

## Final Principle

The goal is not to generate answers. The goal is to build systems that generate better answers tomorrow than they generate today.

Every completed task should leave behind: knowledge, documentation, structure, lessons, reusable capability.

If none of those improved, work was completed. But the system did not learn. And a system that does not learn eventually fails.

---

## References

1. A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications
   https://arxiv.org/abs/2402.07927

2. The Prompt Report: A Systematic Survey of Prompting Techniques
   https://arxiv.org/abs/2406.06608

3. Prompt Engineering in Large Language Models: A Systematic Survey of Optimization Techniques
   https://nano-ntp.com/index.php/nano/article/view/5134

4. A Systematic Survey of Automatic Prompt Optimization Techniques
   https://aclanthology.org/2025.emnlp-main.1681

5. A Comprehensive Taxonomy of Prompt Engineering Techniques for Large Language Models
   https://link.springer.com/10.1007/s11704-025-50058-z

6. The Prompt Canvas: A Literature-Based Practitioner Guide
   https://arxiv.org/abs/2112.12986

7. Promptware Engineering: Software Engineering for LLM Prompt Development
   https://arxiv.org/abs/2503.02400

8. The Amplifier Principle: Why Developers Must Stay in the Driver's Seat
   bin/orama-system/references/amplifier-principle.md

---

## Repos

- Source v1: https://github.com/diazMelgarejo/orama-system
- Target v2: https://github.com/oramasys/oramasys
- oramasys org: https://github.com/oramasys
