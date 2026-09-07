# New Agent Onboarding: Dispatch and GossipBus Basics

**Status:** operational reference, 2026-09-07
**Audience:** any new agent joining active work on the Telos/Phylax v2
endpoint-security architecture (or any concurrent multi-agent effort in this
stack) — read this before claiming a task or posting to the board.

## Read this first, in order

1. **The regime boundary** — [ADR 62 § Regime boundary](../62-telos-phylax-authority-gate0-adr.md#regime-boundary-added-2026-09-06-post-gate-1-reconciliation).
   v1 (`Perpetua-Tools`, `orama-system`) and v2 (the `oramasys` GitHub org)
   are separate regimes, not a stepped evolution. **v1 gets zero
   implementation changes** except a narrow, explicitly human-authorized
   exception for an unavoidable live issue (see PT PR #380 as the worked
   example — a real security fix, opened as a normal PT PR, never merged by
   an agent). Getting this wrong is the single most common mistake so far;
   two different agents (including this document's author) each did it once
   before the boundary was written down.
2. **The current architecture map** — [ADR 62](../62-telos-phylax-authority-gate0-adr.md)
   (Gate 0 decisions), [Gate 1 evidence](../63-gate1-endpoint-observation-and-conformance-evidence.md),
   [Gate 2 scope](../64-gate2-policy-surface-noninterchangeability-scope.md) and
   [evidence](../65-gate2-policy-surface-evidence.md), [Gate 4 + dialer scope](../66-gate4-and-dedicated-dialer-combined-scope.md).
   These are the `docs/v2/` root-level landmark decisions; this file is
   supporting reference material, not one of them — it does not get its own
   ordinal slot.
   Each doc states what's done, what's open, and what's explicitly out of
   scope — read the "explicitly out of scope" section of whatever you're
   about to touch before starting.
3. **The gap-closure plan** (external to this repo, referenced by number
   but not linked per the no-workstation-paths rule) — the Gate 0→6
   dependency graph. A gate that depends on another unfinished gate is not
   ready to start; check the graph, don't assume.

## The coordination board: GossipBus

This is the shared, append-only event log every agent reads and writes to
coordinate without stepping on each other. It is **local to this machine**
(SQLite, shared across every worktree of the same PT checkout via
`git rev-parse --git-common-dir`) — not a remote service, not GitHub. It is
separate from and does not replace posting real work to GitHub PRs.

### How to read it

```python
import asyncio
from orchestrator.gossip_bus import GossipBus

async def main():
    bus = GossipBus()
    await bus.init_db()
    events = await bus.tail(limit=20)   # most recent first
    for e in events:
        print(e["payload"])

asyncio.run(main())
```

Run this from a `Perpetua-Tools` checkout (any worktree). Always read the
last 10-20 events before claiming work — someone may have already claimed,
completed, or invalidated the exact task you're about to start.

### How to post

Every event is `bus.emit(event_type, payload)`. `event_type` is usually
`"heartbeat"` or `"status_update"`; the real routing signal is
`payload["kind"]`:

| `kind` | When to use it |
| --- | --- |
| `agent_register` | Once, when you start a session. Include `agent_id`, `agent_type`, `model`, `worktree`, `notes`. |
| `agent_pulse` | Lightweight liveness ping — cheap, no message body required. |
| `agent_note` | A free-text status update: what you did, what you found, a correction to someone else's claim. This is the workhorse — most real communication happens here. |
| `task_enqueue` | Post a new job for anyone to pick up. See schema below. |
| `task_claim` | You are starting a queued task — post this before you begin, not after. |
| `task_complete` | You finished. Include what changed, test results, commit SHAs, and whether anything was pushed. |
| `task_failed` | The task turned out invalid, out of scope, or you couldn't complete it — say why, so it isn't silently re-claimed. |
| `task_retired` | A queued task is permanently obsolete (superseded, scope changed) — say by what, so no one reissues it. |
| `status_update` (as the `event_type` itself, not a `kind`) | A broadcast to a specific agent or `"all"` — reconciliation notes, corrections, findings. |

Minimal example (queueing a task others can pick up):

```python
await bus.emit("heartbeat", {
    "kind": "task_enqueue",
    "task_id": "short-unique-slug-with-a-date",
    "task_name": "human-readable-name",
    "phase": "which-gate-or-workstream",
    "priority": "NORMAL",  # or CRITICAL / HIGH / LOW
    "priority_level": 3,
    "status": "queued",
    "assigned_agent": None,
    "retry_count": 0,
    "max_retries": 3,
    "depends_on": [],  # other task_ids that must complete first
    "notes": (
        "Full scope, hard constraints, exact file paths, and any regime-"
        "boundary limits go HERE, verbatim -- the next agent should not "
        "need to re-derive context you already have. State what's out of "
        "scope explicitly, not just what's in scope."
    ),
    "source_ref": "branch-or-doc-this-task-is-based-on",
    "expected_base_sha": "the commit sha the notes assume, if applicable",
})
```

### Board discipline that actually matters

- **Announce before you push, not just after.** Two agents fixed the same
  9-comment CodeRabbit review in parallel this session, discovered only
  because each happened to check the other's SDD progress file. Post
  `task_claim` before starting, and check the board first — it would have
  been free.
- **Verify claims against live state, not memory.** Every "X is fixed" or
  "PR #N is at commit Y" claim in this document's own author's history got
  checked at least once against `gh pr view`/`gh api`, not just local git —
  and caught a real gap once (a doc that was claimed pushed but wasn't).
  Do the same before you report anything as done.
- **A `task_failed` or `task_retired` is not a soft signal — read it before
  reissuing similar work.** If a task was invalidated for a regime-boundary
  reason, a rephrased version of the same task will hit the same wall.
- **Post findings even when they refute someone else's work.** A
  independent re-review that reaches a *different* conclusion than the
  original author is valuable — say so plainly, with evidence, and let the
  other agent (or a human) adjudicate. Silently redoing work without saying
  why wastes both agents' effort.

## GitHub: where the real, mergeable work lives

GossipBus coordinates; GitHub PRs are the actual deliverable. Every repo in
play uses the same pattern:

1. Fetch the actual current PR head from GitHub (`gh pr view <n> --json
   headRefOid`) before building on a branch — local git state can be stale.
2. Work in a disposable git worktree, not the shared canonical checkout —
   `git worktree add /tmp/<slug> origin/<branch> -b <your-fix-branch>`.
3. TDD: write the failing test first, confirm it fails for the right
   reason, then fix. Every fix in this session's history that skipped this
   step is the one that needed a second pass.
4. Before pushing: re-fetch the remote branch and diff against it
   (`git diff --name-status origin/<branch>..HEAD`) — if you see unexpected
   `D` (deletion) entries for files you didn't intend to touch, stop and
   investigate before pushing; it usually means the branch has moved since
   you last fetched, not that you broke something.
5. Never force-push without explicit human authorization — it's blocked by
   a safety hook in this environment on purpose. If your work requires
   rewriting already-pushed history, the answer is almost always "add one
   more commit on top" instead, even if that feels less tidy.
6. `gh pr checks <n>` before merging anything — wait for CI, don't merge on
   a pending or partially-green run.

## Common first mistakes (all real, all from this session)

- Assuming a v1 repo (PT, orama-system code — not orama-system *docs*) can
  receive a "small" implementation change because it's convenient. It
  can't, without the explicit human-authorized exception path.
- Trusting a prior agent's board post that "X is pushed" without checking
  live GitHub state.
- Duplicating another agent's in-progress work because the board wasn't
  checked first.
- Claiming a doc-numbering slot (`docs/v2/NN-*.md`) that's already reserved
  by a *still-open, unmerged* PR — check `docs/v2/README.md`'s own free-slot
  pointer AND any open PRs that might already claim the next number, not
  just what's merged into `main`.
- Writing a doc directly into `docs/v2/` root for anything short of a real
  landmark milestone or migration decision. That tree is reserved for those
  specifically — scoping notes, evidence write-ups, dispatch briefs, and
  operational references (like this one) belong in `docs/v2/references/`
  instead, with no ordinal number, unless a human explicitly asks for the
  root. Getting this wrong once already cost a correction mid-session.

## How this translates to v2

Everything above describes the **v1 coordination substrate** — GossipBus as
it exists today: SQLite-backed, hosted inside a `Perpetua-Tools` checkout
(`orchestrator/gossip_bus.py`), shared across worktrees via
`git rev-parse --git-common-dir`. This is real, currently load-bearing
infrastructure, not a stopgap to ignore — but it is explicitly **v1
infrastructure that a v2-native agent should expect to migrate off of**, not
a permanent v2 dependency.

The storage roadmap already decided this (`CLAUDE.md § 8`, 2026-05-15,
reaffirmed 2026-07-12): GossipBus's claim-board coordination history —
agent registrations, task claims, the decision log — is
"job/decision-history-shaped and JSON-file-backed today," and the decision
is to **migrate it to the same LanceDB store already planned for v2 RAG and
session memory**, rather than grow GossipBus into a bespoke, permanent
persistence layer of its own. See
[`43-gossipbus-mesh-transport.md`](../43-gossipbus-mesh-transport.md) for the
live-validated mesh-transport detail behind that decision.

**What this means concretely for onboarding, once that migration lands:**
the event *shapes* in this document (`task_enqueue`/`task_claim`/
`task_complete`/`status_update`, the `kind` field, the discipline of
announcing before pushing) are the durable part — expect them to carry
forward largely unchanged, since they're a coordination protocol, not a
storage detail. The *transport* (`GossipBus()` from
`orchestrator/gossip_bus.py`, PT-hosted SQLite) is the part that migrates.
A v2-native onboarding doc should describe reading/writing the LanceDB-backed
store directly (once it exists) rather than importing PT's `GossipBus` class
from a `Perpetua-Tools` checkout — that import path is itself a v1
dependency an eventually-pure-v2 agent shouldn't need. Until that migration
actually lands, this document's PT-hosted instructions remain the accurate,
literal how-to; don't preemptively code against a LanceDB interface that
doesn't exist yet.
