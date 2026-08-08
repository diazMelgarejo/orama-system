# PT ↔ orama-system Minimal Synergy Plan

**Date:** 2026-08-07
**Status:** proposed — awaiting human review before any item is executed
**Scope:** the fewest changes that close the *verified* (not merely
suspected) synergy gaps between Perpetua-Tools and orama-system, in
service of `docs/v2/references/ORAMASYS-MASTERY-v3.md`'s mission. This is a
**synergy** plan, not a unification plan — the two repos keep their
layering (PT = L2 runtime/state, orama = L3 stateless methodology); nothing
here proposes merging them or collapsing the boundary.

## Method

Three independent passes, then reconciled by hand, not averaged:

1. `agy` produced a first-pass research brief (existing-synergy claims +
   friction claims), scoped to `CLAUDE.md`/`AGENTS.md` navigation files.
2. `codex` and `cursor-agent` independently critiqued that brief
   adversarially, reading the actual cited files rather than trusting the
   brief's prose. They disagreed with each other and with the brief on
   severity and framing in several places — recorded below, not smoothed
   over.
3. I read both critiques, re-verified the highest-severity disputed claims
   myself, cross-checked against `docs/plans/2026-07-22-frugality-privacy-
   reconciliation-and-navigator-closeout.md`, `docs/reference/tiered-model-
   implementation-navigator.md`'s Cross-Repo Plan Register, and
   `docs/plans/2026-07-22-cross-repo-out-of-scope-closure.md` (which already
   dispositioned most of the "is this plan stale" open questions from an
   earlier session), and PT's `.agent/memory` for anything those docs
   already settled.

## What's already correctly wired (don't touch)

Both critiques agree these are real, working synergy, not just documented
intent:

- PT `CLAUDE.md` → orama `docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md` as
  the architecture source of truth (verified: table of banned terms,
  principles, hard requirements, shared types, verifier gate all present
  and current).
- Git attribution guards: canonical in orama `scripts/git/`, synced
  byte-identical to PT — file-hash verified by both critiques
  independently, and by this session's own `check-guard-sync-divergence.sh`
  runs today.
- `docs/LESSONS.md` cross-linking (PT → orama is explicit; orama → PT is
  not reciprocated in the same file, but this is low severity — see below).
- Endpoint transport and hardware-affinity peer contracts (cursor-agent's
  finding, codex's brief didn't surface these) — real, working, CI-enforced
  one-way-import contracts. Working correctly. Not touched by this plan.

## Where the two critiques disagreed with each other (resolved here)

| Point | agy's brief | codex | cursor-agent | Resolution |
|---|---|---|---|---|
| Is `ORAMASYS-MASTERY-v3.md` the current canonical architecture doc? | Implied yes (treated PT's silence on it as drift) | No — it's a "Review draft," `UNIFIED-ABSORPTION-PLAN.md` remains canonical | Same as codex, plus: `docs/reference/tiered-model-implementation-navigator.md` says the *agent-facing spine* is `bin/orama-system/SKILL.md`, a third document | **codex+cursor are right.** There are now three "which doc is the spine" candidates (UNIFIED plan, mother SKILL.md, MASTERY-v3-as-review-draft). This is the one real structural gap worth fixing — see Item 1. |
| Is the PT↔orama bridge (`orama_bridge.py` in PT, `dispatcher.py`/`OramaToPTBridge` in orama) a friction point or intentional design? | Called it "friction," implied circularity | Said cited PT file doesn't import orama Python modules directly, so not literal import circularity, but flagged doc/code naming mismatch | Went further: quoted `UNIFIED-ABSORPTION-PLAN.md`'s own "Error 1" section, which explicitly names PT-owned contracts as **the fix** for a previously-real circular-import problem, not a new one | **cursor-agent is right, most thoroughly.** This is documented-intentional architecture that already resolved a past circularity concern. Not a gap. Not in this plan. |
| Root-level file duplication (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`ANTIGRAVITY.md`/`SKILL.md` in both repos) | Called them "identical or parallel," treated as intrinsic risk | Agreed duplication exists, flagged PT's own conflicting self-description (`SKILL.md` calls PT "top-level orchestrator" vs. the L2/L3 story) | Ran real `diff`, confirmed files are **not** identical (line counts differ by 15-30%), and that GEMINI.md/ANTIGRAVITY.md divergence is *architectural* (orama = thin adapter, PT = full agentic-stack portable brain), not accidental copy-paste drift | **cursor-agent is right that "identical" is false**, and codex's PT-`SKILL.md` self-contradiction finding is the one real, fixable piece — see Item 2. GEMINI/ANTIGRAVITY divergence is left alone (correctly architectural per cursor-agent). |

## The four minimal items (ranked by verified severity, not by how they were phrased)

Every item below was independently confirmed by at least one adversarial
pass reading the actual file, not just the brief's prose. Items are scoped
to be the smallest fix that closes the gap — no restructuring, no new
abstraction layers, no repo merges.

### Item 1 — Name one navigation spine, explicitly (Medium-High; doc-only)

**Problem, verified:** Three documents each plausibly claim to be "the"
architecture/methodology entry point for an agent: `UNIFIED-ABSORPTION-
PLAN.md` (what both repos' `CLAUDE.md` §0 actually point to today),
`bin/orama-system/SKILL.md` (what `docs/reference/tiered-model-
implementation-navigator.md` calls the agent-facing spine), and
`ORAMASYS-MASTERY-v3.md` (a labeled "Review draft" nobody currently points
to from either repo's `CLAUDE.md`). None of this is contradictory *content*
— codex confirmed MASTERY-v3's Core Mission and 5-stage/6-directive
structure matches the mother skill's own content — but an agent arriving
cold has no single stated precedence order.

**Minimal fix:** add one paragraph to **both** repos' `CLAUDE.md` § 0 (the
section that's already supposed to stay in lockstep per PT's own stated
rule) stating the precedence explicitly: `UNIFIED-ABSORPTION-PLAN.md` is
the architecture-contract source of truth; `bin/orama-system/SKILL.md` is
the agent-behavioral spine; `ORAMASYS-MASTERY-v3.md` is a review-draft
methodology reference, not yet promoted, cited for principle-level context
only. No file moves, no content changes to any of the three documents
themselves — just a precedence sentence where agents already look.

**Why minimal:** one paragraph, in a place both repos already read every
session, using documents that already exist and already say true things.
No new document, no restructuring.

### Item 2 — Fix PT `SKILL.md`'s self-contradicting orchestrator claim (Medium; doc-only)

**Problem, verified (codex + cursor-agent independently):** PT `SKILL.md`
describes PT as the **"Orchestrator & instance manager"** owning top-level
lifecycle — language that reads as PT being the top of the stack. This sits
next to PT's own `CLAUDE.md`, which correctly states PT is L2 and orama is
L3 orchestration. Both are true at different scopes (PT orchestrates *its
own* job queue/instances; orama orchestrates *methodology/planning*), but
the word "orchestrator" unqualified in `SKILL.md` reads as a claim to the
same role `CLAUDE.md` assigns to orama.

**Minimal fix:** one-line qualifier in PT `SKILL.md` at the point it says
"Orchestrator & instance manager" — e.g. "(runtime/instance orchestration
at L2; methodology/planning orchestration is orama's L3 role, see
`CLAUDE.md` §0)". Does not change what PT's orchestrator actually does or
any code — only disambiguates a word that means two different things in
two adjacent files.

### Item 3 — orama `AGENTS.md`'s stale endpoint-policy path (High; doc-only, but CI-adjacent)

**Problem, verified (cursor-agent found; codex's brief missed this
entirely):** orama's `AGENTS.md` tells agents PT owns
`.agent/endpoint-policy-contract.yml`. PT's actual, current, CI-enforced
file is at `config/endpoint-policy-contract.yml`. This is a real,
CI-relevant path an agent could act on incorrectly (e.g. editing/creating
the wrong path, or failing to find the real contract file when asked to
check it) — higher real-world severity than either critique's headline
findings, because it's the one item on this list that a code-writing agent
could act on wrongly today, not just a documentation-precedence ambiguity.

**Minimal fix:** correct the single path string in orama `AGENTS.md`. No
code change — the contract file itself, its schema, and PT's
`check_endpoint_policy_core.py` are all already correct; only the
cross-repo *pointer* to it is stale.

### Item 4 — Reciprocal LESSONS.md pointer (Low; doc-only, optional)

**Problem, verified:** PT `CLAUDE.md` §1 points to orama's
`docs/LESSONS.md` as a companion; orama's `CLAUDE.md` §1 does not point
back to PT's. Low severity — an agent working in orama who wants PT's
lessons can still find `../Perpetua-Tools/docs/LESSONS.md` by the same
sibling-path convention used everywhere else in this codebase — but it's a
one-line addition that makes the existing convention actually symmetric
instead of accidentally one-directional.

**Minimal fix:** add the one companion-link line to orama `CLAUDE.md` §1,
mirroring PT's existing line exactly.

## Explicitly NOT in this plan (named, not silently dropped)

- **GEMINI.md/ANTIGRAVITY.md divergence** — cursor-agent confirmed this is
  intentional architecture (orama's thin-adapter model vs. PT's full
  agentic-stack portable brain), not drift. Aligning them would be *adding*
  fragmentation risk, not removing it. Left alone.
- **PT↔orama bridge naming (`orama_bridge.py` vs. `OramaToPTBridge`)** —
  cursor-agent's finding that this is confusing-but-intentional, already
  resolved a real past circularity concern per `UNIFIED-ABSORPTION-PLAN.md`
  §0 Error 1. A rename is cosmetic risk for zero functional gain; not
  proposed here.
- **MASTERY Tier 0-6 model-routing chain vs. PT's search-only frugality
  citation** — real hierarchical-not-contradictory overlap per cursor-agent
  (search chain is consistent with MASTERY Tier 2, just narrower scope).
  The actual model-routing frugality gate (`frugality_router.py` as single
  policy gate) was **already designed, decided, and landed** on
  2026-07-22 (PT commit `13f09c42`) — see the frugality-privacy
  reconciliation plan. Nothing left to reconcile here; this plan does not
  re-open it.
- **PT's `docs/2026-05-31-tri-repo-alignment-completion-plan.md`** — its
  own header still says "active resume anchor," which could read as
  another silently-stale doc, but `docs/plans/2026-07-22-cross-repo-out-of-
  scope-closure.md` already dispositioned it on 2026-07-22: item #1
  implemented and verified (22/22 + 6/6 tests), stale gap text corrected,
  items #2/#3/#8 explicitly deferred to v2 with named blocking reasons.
  Already closed out; re-litigating it here would duplicate settled work.
- **Skill-vendoring mirror tree in PT (`.agents/skills/`)** — cursor-agent
  flagged this as "positive synergy when synced, silent drift when not."
  Real, but no evidence of *current* drift was found in either critique or
  my own pass — flagging for a future audit, not proposing a fix against a
  problem not yet shown to exist.
- **PT ADR-001's stale role language** — cursor-agent's finding is
  accurate (the ADR still uses pre-consolidation terminology), but PT's own
  `docs/adr/` files are documented as machine-generated pointers synced
  from orama `docs/v2/` (per this workspace's top-level `CLAUDE.md`
  invariant) — the fix belongs in whatever generates that pointer, not a
  hand-edit here, and is out of this plan's doc-only scope.

## Execution shape

All four items are documentation-only, additive (no deletions, no
restructuring), and independently landable — no ordering dependency between
them. Recommended: one PR per repo touched (Items 1 and 4 touch both
repos' `CLAUDE.md`; Items 2 and 3 each touch exactly one file in one repo),
kept in lockstep per PT `CLAUDE.md`'s own existing §0 lockstep rule for
Item 1 specifically (since it edits the section that rule already governs).

**Explicit non-goal:** this plan does not re-open, re-score, or re-verify
any finding already dispositioned in the 2026-07-22 closure pass or the
frugality/privacy reconciliation plan. Where this plan's research
overlapped with that prior work, it is cited, not repeated.
