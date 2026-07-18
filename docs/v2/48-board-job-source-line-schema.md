# 48 — Board-job source-line schema (`source_ref` / `expected_base_sha`)

> **Repository standard:** additive to [`46-repository-standard.md`](46-repository-standard.md).
> **Status:** Provisional / experimental — optional now, not enforced.
> May become required at a v2 checkpoint once both repos' queue producers
> and every claimant consistently populate it; no such commitment yet.
> **Date:** 2026-07-19
> **Parent:** [`22-worktree-parallel-agents.md`](22-worktree-parallel-agents.md),
> [`43-gossipbus-mesh-transport.md`](43-gossipbus-mesh-transport.md)
> **Sibling-repo doctrine:** `Perpetua-Tools` `.agent/AGENTS.md` §"Multi-agent
> merge conflict protocol" → "Board-job source line"

## What this is

When a job board row (a `GossipBus`-backed queued task, or any future
orama-side equivalent) is claimed by an agent, the claimant needs to know
**which exact source state** the job was scoped against — otherwise "same
board, same repo" isn't enough to guarantee the claimant starts from the
work the job author actually intended. Two optional fields on the
`task_enqueue` payload carry that:

- `source_ref` — the git ref (branch or commit-ish) the job's work is
  based on.
- `expected_base_sha` — the exact SHA `source_ref` should resolve to at
  claim time; a claimant creates a fresh worktree from this and stops if
  `HEAD` differs, rather than silently working from a moved branch tip.

## Current status: optional and provisional, not enforced

This is a **schema convention**, not a hard requirement, as of this entry.
Concretely, in `Perpetua-Tools`:

- `scripts/agent_coordination_core.py` and `agent_coordination_legacy.py`'s
  `_queue_add()` accept both fields as optional keyword arguments.
- When provided, both are validated (`source_ref` non-empty after
  stripping; `expected_base_sha` matches a 7–40 character hex pattern) and
  persisted into the task's `task_enqueue` payload.
- When omitted, `_queue_add()` behaves exactly as it always has — every
  existing caller, test, and real invocation continues to work unmodified.
- Claimants are **not** currently required to check these fields before
  starting work; the "create a fresh worktree and stop if HEAD differs"
  behavior described in PT's `AGENTS.md` is the target consumer-side
  contract for once this schema is populated consistently, not something
  enforced today.

**Why optional-and-validated instead of hard-required:** making the fields
mandatory outright would break every existing producer/caller in both
repos with no coordinated rollout, and orama-system currently has no
board/queue system of its own to mirror the code-level change into (this
repo's multi-agent coordination is the merge-conflict doctrine in
[`integrative-merge.md`](../../bin/orama-system/skills/oramasys-method/references/integrative-merge.md),
not a job-claiming board). Flipping this to required is a deliberate v2
decision to be made once there's an actual second producer to coordinate
with, not something to bundle silently into one repo's fix.

## What would need to be true before this becomes required (v2 candidate)

Not committed, listed here so a future v2 planning pass has the checklist
rather than reconstructing it:

1. Every `_queue_add`-equivalent producer (in `Perpetua-Tools`, and in
   orama-system if/when it grows an equivalent job-board mechanism)
   populates both fields on every enqueue, not just optionally.
2. Every claimant path (`_queue_claim` and any future orama-side
   equivalent) actually performs the "fresh worktree, stop if HEAD
   differs" check `AGENTS.md` describes, not just parses the fields.
3. A migration plan for already-queued jobs created before this schema
   existed (they will have neither field — claimants need a defined
   fallback, not a hard failure, for pre-existing rows).
4. Regression coverage in both repos proving the enforced path actually
   blocks a claim against a stale/moved source ref, not just that the
   fields round-trip correctly.

## See also

- `Perpetua-Tools` `.agent/AGENTS.md` — the full "Board-job source line"
  doctrine text and its place in the multi-agent merge protocol.
- `Perpetua-Tools` `references/branch-local-review-remediation.md` —
  referenced by that doctrine for the underlying remediation procedure.
- [`22-worktree-parallel-agents.md`](22-worktree-parallel-agents.md) — the
  parallel-worktree model this schema exists to keep claimants honest against.
