---
name: oramasys-method
description: >-
  Use when the user asks for ultrathink, oramasys, deep multi-step reasoning,
  architecture, a complex refactor, careful planning, or an additive PR merge.
  The successor to ultrathink-system applies the orama-system five-stage method,
  AFRP gate, and CIDF guard.
version: "1.3.4"
license: Apache 2.0
compatibility: claude-code, cowork, codex, openclaw
allowed-tools: bash, file-operations, web-search, subagent-creation, mcp-oramasys
triggers:
  - ultrathink
  - oramasys
  - system overhaul
  - architecture work
  - rigorous multi-step plan
when_to_use: Use for non-trivial, design-heavy, or cross-branch work; use a direct answer for a small factual lookup.
---

# oramasys-method

## Purpose

The orama-system methodology (orama = *vision / revelation*), packaged as a
user-invocable skill for Claude, Codex, OpenClaw, and other agent harnesses.
**This is the successor to the legacy `ultrathink-system`.**
Any "ultrathink" trigger activates this skill and is handled by the orama-system
path. It is the user-facing companion to the orama-system mother skill;
harness-specific routing is in `references/harness-compatibility.md`.

## When To Use

Use this method for non-trivial implementation, architecture, planning, or
additive branch-integration work. Use a direct answer for a small factual lookup.

## When Not To Use

Do not use the full method for a self-contained, low-risk formatting change.

## Step 0 — AFRP Gate (mandatory, runs before anything else)

Classify the query on two axes **before** any stage or tool. Never skip.

| Axis 1 — Query Type | Axis 2 — Audience |
| --- | --- |
| **A** factual/lookup → answer direct | Novice → plain language |
| **B** analytical → structured explanation | Practitioner → technical, skip basics |
| **C** implementation/build → full 5-stage | Expert → peer depth, no hand-holding |
| **D** ambiguous → clarify first | (detect from vocabulary) |

State the gate result for any Type B/C/D task:

```text
AFRP: Type [A/B/C/D] | Level [Novice/Practitioner/Expert] | Mode [1/2/3]
Scope: <one sentence>
```

Type → Mode mapping:

- A / small B → **Mode 1** (inline, no subagents)
- C (3-7 steps) → **Mode 2** (5-stage, optional subagents)
- C (8+ steps, parallel) → **Mode 3** (full 7-agent network via MCP; on
  Claude Code, execute via the `Workflow` tool under its own
  `ultracode`/explicit-ask opt-in gate, never a bespoke dispatch loop, with
  mandatory tiered model selection; see the workflow reference.)

## Step 1 — Search FIRST (frugality, non-negotiable)

Before broad Grep, Read, or any web/paid tool, query local semantic memory when
the current harness exposes it.
See `references/search-frugality.md` for the full decision tree.

**Frugality chain (stop at first that answers):**

```text
gbrain → code-review-graph (CRG) → Brave → Perplexity → Grok
```

Quick rules when the tool exists:

- Semantic intent → `gbrain search "<terms>"` or `gbrain query "<q>"`
- Symbol defined where? → `gbrain code-def <symbol>`
- What calls Y? → `gbrain code-callers <symbol>`
- Past decisions/plans → `gbrain search "<terms>" --source gstack-brain-<user>`
- Multi-file code question → CRG MCP tools BEFORE Grep
- Known exact string → Grep is correct
- Web → prefer the harness-approved browser/search path; in Claude/gstack
  environments, use `/browse` rather than raw browser MCP calls.

## Step 2 — The 5 Stages

Full detail in `references/5-stage-methodology.md`.

1. **Context Immersion** — scan git, docs, patterns, constraints via gbrain/CRG first.
2. **Visionary Architecture** — elegant solution; run CIDF `decide()` before any insertion.
3. **Ruthless Refinement** — eliminate everything non-essential.
4. **Masterful Execution** — Plan → Craft (TDD) → Verify programmatically, never visually.
5. **Crystallize Vision** — assumptions ledger, simplification story, lessons captured.

The **6 directives** stay active: Plan Node, Subagents, Self-Improvement, Verification
Before Done, Demand Elegance, Autonomous Bug Fixing.

### Integrative PR merge (mandatory when modifying PRs)

**Before resolving any merge conflict or pushing PR fixes**, load
`references/integrative-merge.md` and apply the **orama-way** merge doctrine:

- **Synthesize, never amputate** — blend, union, and supersede; do not delete working
  content from either branch.
- **Six modes:** additive → union → superset → synthesize → architecturally-correct →
  api-correct; archive instead of delete when content must leave the active path.
- **Simulate first** (`git merge --no-commit --no-ff` + `--diff-filter=U` + abort).
- **One harmonization pass** — no `<<<<<<<` markers; run targeted pytest before push.

This is the same protocol as `bin/orama-system/references/multi-agent-collaboration-protocol.md`
§ Nested-Branch Merge, packaged for PR work and agent harnesses.

### Contract migrations (mandatory at cross-module boundaries)

When a change alters persisted state, a return shape, an event envelope, a
transport payload, or lifecycle behavior, load
`references/contract-migration.md`. Build and verify the complete vertical
slice: persistence → contract → callers → transport → lifecycle → tests.
Do not accept a leaf-only repair that leaves another consumer on the old
contract.

## Step 3 — Route Heavy Reasoning

For Mode 2 or 3, follow `references/harness-compatibility.md`.

---

## Step 4 — Verify before done

- Apply the **TDD gate** (`references/tdd-gate.md` → canonical `docs/TDD.md`) before marking Stage 4 complete
- Run tests / programmatic check (never visual only)
- Confirm the artifact actually changed: re-read it, check the signature
- For multi-agent work: confirm each subagent output before aggregating
- For memory/security policy edits: apply the portable-memory local-topology
  invariant in `docs/v2/47-portable-memory-local-topology-invariant.md` —
  tracked rules name categories only; concrete local fragments stay in
  local-only registries outside git.

### File Truncation Check

Apply `references/file-truncation-check.md` after every whole-file write.

---

## Boundaries

### Always Do

- Run AFRP gate before any non-trivial output
- Search local memory/CRG equivalents before broad Grep/Read/web when available
- Apply CIDF `decide()` before any content insertion (start at rank 1)
- Treat "ultrathink" and "oramasys" as the same trigger
- **On PR/conflict work:** follow `references/integrative-merge.md` (additive harmonization)
- **Verify file truncation** after every whole-file write

### Ask First

- Escalating to a paid search tier (Perplexity/Grok)
- Spawning the full Mode-3 7-agent network
- Any destructive action

### Never Do

- Skip the AFRP gate for complex queries
- Parallel-fire all search tools at once (frugality violation)
- Bypass the current harness's approved browser/search path
- Trust visual confirmation as verification
- Reintroduce `mcp-ultrathink-*` names in new config or skills
- **Resolve merge conflicts by wholesale `--ours` / `--theirs` without classifying mode**
- **Commit a file without a truncation check**

---

## Runbook And Glossary

Runbook: classify, search locally, design the smallest coherent change, verify,
then record only the result needed for the next agent. AFRP is the query/audience
router; CIDF is the content-insertion guard; CRG is code-review-graph.

---

## References

- `references/5-stage-methodology.md` — full 5-stage process + 6 directives
- `references/integrative-merge.md` — **PR merge / conflict harmonization (additive, never-delete)**
- `references/search-frugality.md` — gbrain + gstack + CRG decision tree
- `references/graceful-degradation.md` — unified fallback ladders (oramasys + PT model selection)
- `references/cidf-and-mcp.md` — CIDF ranks, MCP names, legacy compatibility map
- `references/tdd-gate.md` — TDD prescriptive gate (links `docs/TDD.md`)
- `references/contract-migration.md` — vertical-slice contract migration and regression method
- `references/harness-compatibility.md` — tool and MCP routing by host
- `references/file-truncation-check.md` — mandatory complete-write verification
- `../../references/contribution-standards.md` — CONTRIBUTING.md + PR-template baseline and the method's raised contribution standard (PT PR #247); pairs with `post-review-micro-remediation.md`
- `../../references/skill-architecture-guide.md` — the repo's own SKILL.md standard this file is audited against
