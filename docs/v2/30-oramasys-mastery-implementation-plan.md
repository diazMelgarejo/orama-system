# ORAMASYS-MASTERY v3 — Implementation Plan

> **File:** `docs/v2/30-oramasys-mastery-implementation-plan.md`
> **Status:** Approved for execution — v2 migration
> **Human reference:** `docs/v2/29-oramasys-mastery-v3.md` (verbatim, review first)
> **Repo v2:** `github.com/oramasys/oramasys`

---

## 0. Principles Governing This Plan

- **Zero duplication.** Every piece of content lives in exactly one canonical file.
  All other references are pointers, not copies.
- **Minimal diff.** Only add what is missing; never rewrite what already works.
- **Spine prevails.** `bin/orama-system/SKILL.md` is the agent-facing source of
  truth. Meta-layers extend it via `references:` pointers, not inline text.
- **Human-facing vs agent-facing are separate files** with a clear contract
  between them.

---

## 1. Current State (verified 2026-06-13)

```
bin/orama-system/
  SKILL.md              ← mother skill (spine: AFRP, modes, CIDF, frugality)
  afrp/SKILL.md         ← AFRP gate detail
  cidf/SKILL.md         ← CIDF v1.2
  references/
    oramasys-5-stages.md     ← canonical 5-stage deep dive
    amplifier-principle.md   ← full Amplifier Principle essay
    content-insertion-framework.md

docs/v2/
  29-oramasys-mastery-v3.md  ← human-facing unified reference (NEW, verbatim)

.claude/skills/
  agent-methodology/SKILL.md  ← DEFECTIVE (divergent 5-stage sequence — GOAL.md AC1)
  oramasys-method/            ← not yet in repo (pending push)
```

**What the mother SKILL.md already has (do not duplicate):**
- AFRP gate (Type A/B/C/D, Novice/Practitioner/Expert, Mode 1/2/3)
- Full 5-stage sequence (references/oramasys-5-stages.md)
- 6 operational directives
- CIDF decision table + lint rules
- Frugality chain (gbrain → CRG → Brave → Perplexity → Grok)
- Mode 1/2/3 execution paths

**What is missing (the diff to add):**

| Meta-layer | Status | Action needed |
|---|---|---|
| M1: Spec Contract template | Missing from mother SKILL | Add as pre-AFRP section |
| M2: Amplifier Objective Tree | Missing from mother SKILL | Add as brief section |
| M3: Collaborative Reasoning Safety | Missing from all skills | New reference file + pointer |
| M4: Output Discipline (6-section) | In mastery doc only | Add to Stage 5 Crystallize |
| M5: Lessons Architecture | In docs/LESSONS.md preamble | Add pointer in SKILL.md |
| M6: Communication Guidelines | Missing from all skills | New reference file + pointer |

---

## 2. The Diff: What to Add to `bin/orama-system/SKILL.md`

**Total change: ~50 lines added, 0 lines changed.**

### 2a. Pre-AFRP block (insert before the AFRP section)

```markdown
## Pre-Flight: Spec Contract

Run before the AFRP gate. Sets the contract that AFRP then routes.
Full template: `docs/v2/29-oramasys-mastery-v3.md § M1`

Three questions every task must answer before execution:

**Role:** who are we in this context?
(Systems Architect / Research Scientist / Engineer / Teacher / Operator)

**Goal:** what outcome actually matters?
Not the activity. Not the task. The outcome. What must be true before success is declared?

**Constraints:** reality always wins.
Time, budget, security, compliance, compatibility. Constraints define the
shape of the solution.

Quick template:
```text
ROLE: <who you are>
GOAL: <what must be true when done>
CONSTRAINTS: <assumptions, limits, what to avoid>
```
```

### 2b. Amplifier Objective Tree (insert after AFRP, before Mode Router)

```markdown
## Amplifier Objective Tree

Every task has three layers. Identify all three before starting.
Full principle: `references/amplifier-principle.md`

| Layer | Question | Common failure |
|---|---|---|
| Explicit objective | What was requested? | Solve the stated problem instead of the real one |
| Hidden objective | What problem is actually being solved? | Stop here, miss the real value |
| System objective | What improves the larger system? | Ship a fix that breaks the surrounding contract |
```

### 2c. Collaborative Reasoning Safety pointer (insert in Mode 3 section)

```markdown
> **Mode 3 safety:** See `references/collaborative-reasoning-safety.md`
> for the mandatory Builder/Critic/Adversary/Judge roles, anti-groupthink
> rules, and confidence-tracking requirements.
```

### 2d. Output Discipline (append to Stage 5 / Crystallize Vision)

```markdown
**Output shape** — every substantial deliverable contains these six sections:

1. ASSUMPTIONS — what you decided, guessed, or ruled out
2. ARCHITECTURE / PLAN — structure and component relationships
3. ARTIFACT — the actual deliverable
4. TEST & VERIFICATION — how correctness is validated
5. RISKS + MITIGATIONS — what could go wrong and how to handle it
6. NEXT ACTIONS — numbered, concrete, with clear ownership
```

### 2e. References block (append to footer of SKILL.md)

```markdown
## Extended References

| Reference | Content |
|---|---|
| `references/amplifier-principle.md` | Full Amplifier Principle essay |
| `references/oramasys-5-stages.md` | Deep dive on 5-stage methodology |
| `references/collaborative-reasoning-safety.md` | Multi-agent safety (M3) — NEW |
| `references/communication-guidelines.md` | Writing guidelines (M6) — NEW |
| `docs/v2/29-oramasys-mastery-v3.md` | Human-facing unified mastery reference |
```

---

## 3. New Reference Files to Create

### 3a. `references/collaborative-reasoning-safety.md`

Content: The full M3 section from `docs/v2/29-oramasys-mastery-v3.md`:
- Four mandatory roles (Builder, Critic, Adversary, Judge)
- Every conclusion must answer: "what is the strongest argument against this?"
- Confidence tracking (4 axes: confidence, uncertainty, consensus, disagreement)
- Anti-groupthink rule
- Adversarial review before finalizing
- Agent governance (must/must not table)

### 3b. `references/communication-guidelines.md`

Content: The full M6 section from `docs/v2/29-oramasys-mastery-v3.md`:
- Core principle: tell it straight
- Language to avoid (the AI tells list)
- Document type guidance table (formal vs working)
- Em-dash ban, semicolon guidance, emoji scope

Note: mark these as "runtime guidelines, not retroactive strict rules."

---

## 4. Fix Required Before Any of the Above

**GOAL.md AC1 must land first.** The `.claude/skills/agent-methodology/SKILL.md`
currently defines a divergent 5-stage sequence. If we extend the mother SKILL.md
before fixing the card, agents will still find the wrong sequence in the card.

Sequence:
```
1. Fix agent-methodology (GOAL.md AC1)
2. Run: python scripts/eval/oramasys_trigger_eval.py  (AC8)
3. Apply diffs from § 2 to bin/orama-system/SKILL.md
4. Create reference files from § 3
5. Run hygiene check
6. Commit: feat(v1.1): apply oramasys-mastery meta-layers to mother SKILL.md
```

---

## 5. v2 Repo Migration Plan (oramasys/oramasys)

The v2 target repo at `github.com/oramasys/oramasys` is a clean break from v1.
This is the migration path:

### 5a. What moves verbatim

| v1 path | v2 path | Notes |
|---|---|---|
| `bin/orama-system/SKILL.md` | `skills/oramasys/SKILL.md` | After § 2 diffs applied |
| `bin/orama-system/references/` | `references/` | All reference files |
| `bin/orama-system/skills/oramasys-method/` | `skills/oramasys-method/` | The user-invocable skill |
| `docs/v2/29-oramasys-mastery-v3.md` | `docs/ORAMASYS-MASTERY.md` | Pinned at root of docs |
| `docs/LESSONS.md` | `docs/LESSONS.md` | Canonical, with thin wrappers |

### 5b. What changes in v2

- `ultrathink` names: all renamed to `oramasys` (GOAL.md P0 prerequisite)
- `bin/orama-system/` nesting removed: flat `skills/`, `references/` at repo root
- `bin/shared/ultrathink_core.py` → `core/oramasys_core.py`
- Frugality router (`orchestrator/frugality_router.py`) implemented (PT v1.1)
- `POST /ultrathink` shim removed (v1.1 P0.4)
- `docs/v2/` content promoted to `docs/` (flat)

### 5c. What v2 adds new

- `skills/prompt-engineering/SKILL.md` — distillation of PEM craft section
  (mastery checklists, four pillars, before/after examples, prompt library schema)
- `skills/spec-contract/SKILL.md` — M1 as a standalone user-invocable skill
- `core/frugality_router.py` — the Tier 0-6 dispatch chokepoint
- `config/pipelines.yml` — OpenRouter tiered pipeline (P2, flag-off by default)
- `.github/workflows/mastery-eval.yml` — AC8 trigger eval on every PR

### 5d. Dependency order for v2 migration

```
P0: Rename (GOAL.md) — no broken references in v2
  |
P1: Apply SKILL.md diffs (§ 2 above)
  |
P2: Create reference files (§ 3)
  |
P3: v2 repo scaffold (flat structure, new skills from § 5c)
  |
P4: Frugality router + pipelines (v1.1 plan)
  |
P5: Tag v1.1.0 lockstep
```

---

## 6. Programmatic Application Strategy

**The key insight:** oramasys-mastery content maps 1:1 to specific files.
No content should live in two places. A script can verify this.

### 6a. Deduplication check (add to `test_repo_hygiene.py`)

```python
def check_mastery_no_duplication(root: Path) -> list[str]:
    """
    Key phrases from the mastery doc should appear in exactly ONE canonical file.
    If found in more than one non-wrapper file, flag as duplication.
    """
    canonical_map = {
        "direct_form_input": "bin/orama-system/cidf/SKILL.md",
        "Context Immersion": "bin/orama-system/references/oramasys-5-stages.md",
        "Amplifier Principle": "bin/orama-system/references/amplifier-principle.md",
        "Builder/Critic/Adversary": "bin/orama-system/references/collaborative-reasoning-safety.md",
        "communication-guidelines": "bin/orama-system/references/communication-guidelines.md",
    }
    errors = []
    for phrase, canonical in canonical_map.items():
        hits = []
        for f in root.rglob("*.md"):
            if ".git" in str(f) or "docs/v2/29-oramasys" in str(f):
                continue  # skip the mastery doc itself
            if phrase.lower() in f.read_text().lower():
                hits.append(str(f.relative_to(root)))
        non_canonical = [h for h in hits if canonical not in h]
        if len(non_canonical) > 1:
            errors.append(
                f"Duplication: '{phrase}' appears in {non_canonical} "
                f"(canonical: {canonical})"
            )
    return errors
```

### 6b. Auto-apply script (for v2 migration)

```bash
# scripts/migrate/apply-mastery-diffs.sh
# Applies the § 2 diffs to the mother SKILL.md and creates § 3 reference files.
# Idempotent -- checks for existing markers before inserting.
set -euo pipefail

SKILL="bin/orama-system/SKILL.md"
REF="bin/orama-system/references"

# Check: is the Spec Contract already in SKILL.md?
if grep -q "Pre-Flight: Spec Contract" "$SKILL"; then
  echo "Spec Contract already present -- skipping"
else
  # Insert before the AFRP section
  # (implementation: sed or Python patch script)
  python3 scripts/migrate/patch_skill_md.py --section spec-contract
fi

# Similar checks for each meta-layer...
python3 scripts/migrate/patch_skill_md.py --check-all
```

---

## 7. Acceptance Criteria

These extend GOAL.md for the mastery implementation pass:

- [ ] **AC-M1** `bin/orama-system/SKILL.md` contains "Pre-Flight: Spec Contract" section
- [ ] **AC-M2** Mother SKILL.md contains "Amplifier Objective Tree" section
- [ ] **AC-M3** `references/collaborative-reasoning-safety.md` exists and is linked from SKILL.md
- [ ] **AC-M4** Mother SKILL.md Stage 5 mentions the 6-section output shape
- [ ] **AC-M6** `references/communication-guidelines.md` exists and is linked from SKILL.md
- [ ] **AC-M7** `check_mastery_no_duplication()` returns 0 errors
- [ ] **AC-M8** `docs/v2/29-oramasys-mastery-v3.md` verbatim == uploaded source
- [ ] **AC-M9** `.claude/lessons/LESSONS.md` is a thin wrapper (<= 30 lines, no session entries)
- [ ] **AC-M10** `docs/LESSONS.md` sorted newest-first, contains all entries from both files

---

## 8. One-Line Summary

> Apply the mastery framework as a pointer network, not a content copy:
> the mother SKILL.md gains ~50 lines of meta-layer stubs; all detail lives
> in dedicated reference files; the human-facing mastery doc is the index.
