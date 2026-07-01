---
name: oramasys-method
description: >-
  Successor and drop-in replacement for the legacy ultrathink-system method.
  Applies the orama-system 5-stage methodology (Context Immersion → Visionary
  Architecture → Ruthless Refinement → Masterful Execution → Crystallize) with
  the AFRP pre-router gate and CIDF content-insertion guard. Prefer local
  memory/search tools before paid or external tools, and route heavy reasoning
  through the orama MCP server when the current agent harness exposes it. ALWAYS
  use this skill when the user says
  "ultrathink", "ultrathink this", "think deeply", "5-stage", "systematic
  approach", "oramasys", "apply oramasys", or asks for deep multi-step problem
  solving, architecture or re-architecture work, a rigorous or multi-step plan,
  a complex refactor, a system overhaul, or careful task planning — even when
  the exact word "ultrathink" or "oramasys" is absent, and even if they use the
  old "ultrathink" name. If a request is non-trivial, multi-step, or design-heavy,
  prefer this skill. It replaces ultrathink-system; treat any ultrathink
  invocation as an oramasys invocation. **Also use for PR merges, conflict
  resolution, nested-branch integration, and any edit that must harmonize two
  divergent branches additively (never delete-and-replace).**
version: "1.2.0"
license: Apache 2.0
compatibility: claude-code, cowork, codex, openclaw
allowed-tools: bash, file-operations, web-search, subagent-creation, mcp-oramasys
---

# oramasys-method

The orama-system methodology (orama = *vision / revelation*), packaged as a
user-invocable skill for Claude, Codex, OpenClaw, and other agent harnesses.
**This is the successor to the legacy `ultrathink-system`.**
Any "ultrathink" trigger activates this skill and is handled by the orama-system
path — same muscle memory, new engine.

> **Upstream alignment:** The `orama-system` mother skill already carries the AFRP
> gate, CIDF, search policy, and MCP routing; the repo's `agent-methodology` card
> is Claude-only background knowledge (`user-invocable: false`). This skill is the
> user-invocable front door tying them together and guaranteeing the legacy
> "ultrathink" alias keeps working. The 5 stages below match the repo's canonical
> 5-stage methodology exactly.

## Agent Harness Compatibility

This skill is intentionally agent-neutral:

- Use native planning, shell, file, browser, and MCP tools from the current harness.
- Treat named integrations such as `gbrain`, `gstack`, CRG, and `mcp-oramasys` as
  preferred local tiers when available, not as permission to invent unavailable tools.
- If a tier is unavailable, state the fallback briefly and use the cheapest
  available equivalent before escalating to network or paid tools.
- Preserve the method and verification standard even when the exact tool names differ.

---

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
- C (8+ steps, parallel) → **Mode 3** (full 7-agent network via MCP)

---

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

---

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

---

## Step 3 — Route heavy reasoning through the MCP server

For Mode 2/3, offload deep reasoning to the orama MCP server when available.

- MCP tool: **`mcp-oramasys`** (canonical, when exposed by the harness)
- Legacy `mcp-ultrathink-*` names are deprecated aliases pointing to the same server
- HTTP backup: `POST /oramasys` port 8001

---

## Step 4 — Verify before done

- Apply the **TDD gate** (`references/tdd-gate.md` → canonical `docs/TDD.md`) before marking Stage 4 complete
- Run tests / programmatic check (never visual only)
- Confirm the artifact actually changed: re-read it, check the signature
- For multi-agent work: confirm each subagent output before aggregating

---

## Boundaries

### Always Do

- Run AFRP gate before any non-trivial output
- Search local memory/CRG equivalents before broad Grep/Read/web when available
- Apply CIDF `decide()` before any content insertion (start at rank 1)
- Treat "ultrathink" and "oramasys" as the same trigger
- **On PR/conflict work:** follow `references/integrative-merge.md` (additive harmonization)

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

---

## References

- `references/5-stage-methodology.md` — full 5-stage process + 6 directives
- `references/integrative-merge.md` — **PR merge / conflict harmonization (additive, never-delete)**
- `references/search-frugality.md` — gbrain + gstack + CRG decision tree
- `references/graceful-degradation.md` — unified fallback ladders (oramasys + PT model selection)
- `references/cidf-and-mcp.md` — CIDF ranks, MCP names, legacy compatibility map
- `references/tdd-gate.md` — TDD prescriptive gate (links `docs/TDD.md`)
