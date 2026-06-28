# 26 — TDD + Outsourced Review Doctrine

> **Status:** CANONICAL — enshrines `tdd.md` (OpenClaw root pointer) into the v2 doc tree.
> This doc is the source of truth; `tdd.md` is a thin pointer to this file + the maintained
> skill body below. See also: `skills/tdd-workflow/SKILL.md` (via `vendor/ecc-tools`).
> Added: 2026-06-05.

---

## 1 — Why TDD is non-negotiable here

Agentic coding is the primary execution mechanism. The autoresearcher loop (doc 25) runs
code continuously. Without test-first discipline, accumulated defects compound faster than
reviews can catch them. TDD is the **only forcing function** that keeps each increment
small, provably correct, and regression-free at AI iteration speed.

Additional advantages at agentic scale:
- Simpler, more modular code (tests define minimal interface before implementation exists)
- Fewer regressions (each green test suite = evidence the lego still fits)
- Easier to troubleshoot (failures are isolated, test name tells you exactly what broke)
- Token-efficient long runs (fewer large debugging detours)

---

## 2 — The RED → GREEN → REFACTOR loop (8 steps, strict)

This is the canonical per-feature cycle. **No exceptions** for "simple" changes.

```
1. Write a test that fails for the target behavior.
2. Run the test — confirm it FAILS (not errors). If it errors, fix the test until it
   fails cleanly, then continue.
3. Write the minimal code to make the test pass.
4. Run the test — confirm it PASSES.
5. If it fails, return to step 3.
6. Once passing, verify that the task intent is satisfied (not just the test assertion).
7. If intent is not satisfied, return to step 1 with a more precise test.
8. REFACTOR: clean up implementation and test, keeping green. Commit.
```

**Key discipline:**
- Step 1 is always writing the test, never writing the implementation first.
- "Minimal code" in step 3 means the smallest change that makes the test pass — not a
  full implementation that happens to pass the test.
- Step 6 is the intent-verification gate: a passing test that doesn't prove the real
  behavior is a false negative. Fix the test before moving on.

---

## 3 — Outsourced review policy (frugality + heterogeneity)

TDD is token-hungry upfront. To maintain quality without burning context on planning and
review, work is **outsourced to specialist roles**:

| Role | Tool | What it does |
|------|------|--------------|
| **Plan** | GPT-5.5 (OpenAI) | Code architecture, approach selection, API design before writing any test |
| **Review** | Gemini 3.1 Thinking (Google) | Post-implementation adversarial code review — correctness, security, coverage gaps |
| **Merge / harmonize** | Opus 4.8 PLAN-mode (this agent) | Receives plans from GPT-5.5 and reviews from Gemini 3.1; harmonizes into the canonical decision, breaking ties and enforcing orama-way constraints |

**Process:**
1. Before writing the first test for a non-trivial feature: dispatch a plan request to
   GPT-5.5 ("design the API / data structure / node interface for X").
2. Complete TDD loop internally (steps 1–8 above).
3. After green + refactor: dispatch review to Gemini 3.1 Thinking.
4. Opus 4.8 reviews Gemini's findings, applies CIDF (additive merge), and closes or
   escalates each finding via a PR comment / fix commit.

This keeps the main context lean (no large inline planning monologues) while ensuring
heterogeneous adversarial review on every non-trivial increment.

---

## 4 — ECC submodule relationship

The **maintained TDD skill body** lives at:
```
vendor/ecc-tools/skills/tdd-workflow/SKILL.md   (in Perpetua-Tools + orama-system)
```

This doc (`26-tdd-...`) is the **v2 architectural policy** — the "why" and the "what".
The SKILL.md is the **executable implementation** — the step-by-step agent instructions.

The relationship:
- This doc sets policy; SKILL.md operationalizes it. They must stay in sync.
- `tdd.md` at the OpenClaw root is a **thin pointer** to both (as it already claims to be).
  It must not duplicate content from either.
- When ECC tools updates `tdd-workflow/SKILL.md` via the submodule, review this doc for
  drift and update the cross-reference if needed.

**Do NOT** duplicate the 8-step loop in SKILL.md vs here — one owns prose policy (this
doc), the other owns agent-executable instructions (SKILL.md). If they diverge, this doc wins
on intent; SKILL.md wins on mechanism.

---

## 5 — Applying TDD to the autoresearcher loop

Every iteration fired by the heartbeat (doc 25 §3) follows this protocol:

```
heartbeat fires
  → read queue: pick next build item
  → GPT-5.5: plan the test interface
  → write failing test (step 1–2)
  → implement minimally (step 3–5)
  → verify intent (step 6–7)
  → refactor + commit (step 8)
  → Gemini 3.1: review the commit diff
  → Opus 4.8: harmonize review findings → fix or defer
  → update heartbeat queue
  → stop (or continue if budget allows)
```

The heartbeat never merges or deploys — it only commits to the playground branch. Merge
to main happens in supervised iterations (operator reviews the PR).

---

## 6 — docs/v2 coverage requirement

From this doc forward, **every Phase-2 and Phase-3 feature** in the autoresearcher scope
must have:
- A failing test before any implementation code is written.
- Evidence of the RED state (test run output logged or commented).
- Evidence of the GREEN state (test run after implementation).
- The commit that closes the cycle follows RED → GREEN → REFACTOR order.

This is enforced by the pre-commit hook (`scripts/git/check_tdd_commit.sh` — to be added
in Phase 1, item TDD-hook in doc 25 §4).

---

## 7 — Cross-references

- `docs/v2/25-autoresearcher-doctrine-and-againtra-flagship.md` — parent doctrine
- `vendor/ecc-tools/skills/tdd-workflow/SKILL.md` — maintained TDD skill body
- `tdd.md` (OpenClaw root) — thin pointer (must stay pointer-only, no duplicate content)
- `docs/v2/04-build-order.md` — Phase gates that now require TDD evidence
