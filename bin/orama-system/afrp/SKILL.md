---
name: afrp
description: Audience-First Response Protocol — mandatory pre-router gate. Classifies query type (A/B/C/D), declares scope, and calibrates abstraction level before any ultrathink stage begins. Activates before generating any non-trivial output.
version: 1.0.0
license: Apache 2.0
compatibility: claude-code, cowork, open, codex
allowed-tools: bash, file-operations
---

# Audience-First Response Protocol (AFRP)

**Mandatory pre-router gate.** Run before any non-trivial output. Never skip.

---

## The Gate

Before generating output, classify the incoming query on two axes:

### Axis 1 — Query Type

| Type | Description | Response calibration |
|------|-------------|----------------------|
| **A** | Direct factual / lookup | Concise, direct answer. No elaboration. |
| **B** | Analytical / reasoning | Structured explanation, medium depth. |
| **C** | Implementation / build | Full ultrathink 5-stage process. |
| **D** | Ambiguous / meta | Clarify scope before proceeding. |

### Axis 2 — Audience Level

| Level | Signals | Calibration |
|-------|---------|-------------|
| Novice | "explain", "what is", "how do I" | Plain language, analogies, step-by-step |
| Practitioner | domain vocabulary, specific tools | Technical precision, skip basics |
| Expert | edge cases, architecture, tradeoffs | Peer-level depth, no hand-holding |

---

## Protocol Steps

```
1. READ the query fully before classifying
2. CLASSIFY: Type (A/B/C/D) × Level (Novice/Practitioner/Expert)
3. DECLARE scope: "This is a Type C / Practitioner query. Applying ultrathink MODE 2."
4. CALIBRATE output format and depth
5. PROCEED with the appropriate ultrathink mode
```

---

## Type × Mode Mapping

| Query Type | ultrathink Mode | When |
|-----------|----------------|------|
| A | MODE 1 (inline, no plan) | Simple lookup, 1-2 steps |
| B | MODE 1–2 | Analysis, explanation |
| C (small) | MODE 2 (5-stage, subagents) | Build task, 3-7 steps |
| C (large) | MODE 3 (full 7-agent network) | 8+ steps, parallel modules |
| D | Clarify first, then reclassify | Ambiguous scope |

---

## Scope Declaration Format

```
AFRP Gate: Type [A/B/C/D] | Level [Novice/Practitioner/Expert] | Mode [1/2/3]
Scope: [one sentence describing what will be done]
```

**Example**:
```
AFRP Gate: Type C | Level Practitioner | Mode 2
Scope: Implement CIDF-compliant content insertion for the form submission flow.
```

---

## Intent-Verification Gate (Anti-Handwaving) — Mandatory

The Type/Level axes calibrate *how* to answer. This gate guards *whether I understood
the request at all* and *whether my method answers it*. Handwaving — asserting a
conclusion from a narrow proxy without confirming intent — is the #1 way this system
wastes the user's time and erodes trust.

**Two triggers force a STOP-and-clarify (AskUserQuestion FIRST, before acting):**

1. **Interpretation risk.** The request could mean ≥2 things, uses a term/operation with
   competing mechanics (e.g. "re-anchor" = flatten? graft? point-at-twin?), or the user
   insists something exists/needs doing that my first check denies. → Ask to confirm the
   true intent and the desired end-state *before* executing. Do not act on the best guess.

2. **About to conclude "nothing to do."** Before asserting "already fine / no problem
   found / no orphans / no data loss / done," verify the conclusion came from the **method
   that actually answers the question**, not a cheaper proxy. Name the limit of what was
   checked. If a proxy disagrees with the user's insistence, run the real method
   exhaustively before reporting a negative.

**Proxy ≠ real question (examples that bit us):**

| Cheap proxy I used | The real question | Right method |
|--------------------|-------------------|--------------|
| `git merge-base != root` ⇒ "not orphaned" | does the branch's *content* converge with main? | byte-identical **tree-twin** search (`git log main --format='%H %T'`) |
| "no commits absent ⇒ no data loss ⇒ nothing to restore" | does the user want the *refs/history* reconciled regardless? | ask; reconcile per their model |
| "tests pass" | does the feature actually work? | run it / observe behavior |

**Reflect, then route:** TRUE intent (clarify if ambiguous) → correct method (not a proxy)
→ act. Trust the user's domain signal over my first-pass check — their context exceeds mine.

> Earned 2026-06-04 (orama/AlphaClaw/periscope branch reconciliation): three successive
> handwaved conclusions, each corrected by the user. See `failure-modes.md` and the
> [`git-reanchor`](../skills/git-reanchor/SKILL.md) skill.

---

## Boundaries

### Always Do
- Run AFRP gate before any Type B, C, or D response
- State the gate result explicitly when using Mode 2 or 3
- Re-run gate if the user clarifies a Type D query
- **Run the Intent-Verification gate** on interpretation risk or before any "nothing to do" conclusion — AskUserQuestion FIRST, reflect, use the real method not a proxy

### Ask First
- Reclassifying from C to D (means the task is ambiguous — confirm with user)
- Any request open to ≥2 interpretations, or where the user insists against my first check — confirm intent before acting

### Never Do
- Skip the gate for complex or audience-dependent queries
- Proceed with Mode 3 without declaring it explicitly
- Assume expert level without signals confirming it
- **Handwave**: assert "done / fine / nothing needed" from a narrow proxy without confirming intent or running the method that truly answers the question

---

## Integration

AFRP is the first step in `bin/orama-system/SKILL.md` Mode Router.
It runs before the complexity signals are evaluated.
The router is compatible with Perplexity-Tools via the current bridge, OR via the implemented backup HTTP `/ultrathink` path.

```
Query arrives → AFRP Gate → Mode Router → MODE 1 / 2 / 3
```

*See `bin/orama-system/SKILL.md` for the full execution mode router.*
