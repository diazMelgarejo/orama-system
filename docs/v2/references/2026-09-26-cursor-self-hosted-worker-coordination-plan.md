# Cursor Self-Hosted Worker Coordination Plan

## Status

**Active — research-backed (2026-09-26).** EXA + Firecrawl verified the
primary Cursor docs (HTTP 200). Phase 0 topology probe was executed
read-only against the designated Perpetua-Tools checkout. Worker restart
(Phase 2) remains gated on idle + operator approval.

| Gate | State |
| ---- | ----- |
| Research (EXA + Firecrawl) | Done — see §Verified references |
| Phase 0 probe | Done — advisory topology classification only |
| Phase 1 mode selection | Done — topology match at coordinator root; Mode B elsewhere |
| Phase 2 worker restart | **Deferred** — require idle session + HITL |
| Relay / `remote-coordination.sh` merge | **Blocked** — see §Decision |
| W0-R1 | **Answered** — Mode B is read-only handoff; a shared-claim relay needs a separate protocol |

## Current Authoritative Execution Record (2026-09-26)

This section supersedes conflicting operational interpretations in the
historical addenda below. The addenda remain evidence of the investigation;
they do not grant authority or define a newer delivery state.

### Verified platform boundary

Cursor's [My Machines documentation](https://cursor.com/docs/cloud-agent/self-hosted/my-machines)
states that the agent loop runs in Cursor's cloud while tools execute through
the worker's outbound connection on the local machine. It also documents
repository-based worker selection and refusal when a selected worker does not
serve the repository. Cursor's [worktree documentation](https://cursor.com/docs/configuration/worktrees)
is therefore complementary, not automatic: each delivery still creates and
proves its own isolated checkout. The official
[runtime guide](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime)
and [computer-use guide](https://cursor.com/docs/cloud-agent/self-hosted/computer-use)
remain the source of truth for worker placement and privileged desktop access.

### Delivery state

| Item | Source line | Verified behavior | Delivery decision |
| --- | --- | --- | --- |
| I1 topology probe | [`fix/cursor-topology-probe-authority-20260926`](https://github.com/diazMelgarejo/Perpetua-Tools/pull/401) at `84523aea` | Classifies local topology with the full device/inode/size tuple, but always reports `queue_write_authority: false`. Focused suite: 12 passing. | Published PR #401, based on `origin/main`. |
| I2 truthful helper | [`feat/cursor-i2-truthful-status-20260926`](https://github.com/diazMelgarejo/Perpetua-Tools/pull/402) at `3d638d64`, parent chain includes `84523aea` | Produces status-only JSON; refuses `pulse` and `log`; does not call a peer or the coordination CLI; exports only allowlisted advisory topology fields and never emits the supplied relay secret. Combined focused suite: 21 passing. | Draft stacked PR #402, based on I1; independent current-stack review remains required. |
| Historical bridge | `feat/cursor-remote-gossip-bridge-20260926` at `1e9f5019` | Local CLI wrapper whose wording can imply a relay without transport. | Deliberately excluded; not a stack parent and not mergeable as a relay. |
| I3 worker restart | Operator worker configuration | Long-lived worker process and declared repository roots. | Deferred until idle plus explicit operator approval. |
| I4 publication/handoff | PR and review evidence | A branch or handoff can carry review evidence, never queue authority. | Evidence-only and human-reviewed. |
| I5 real relay | v2.1 controller design | Authenticated mutations with durable atomic state, not a shell wrapper. | Deferred specification work; no v1 implementation. |

### Working-world simulation

| Scenario | I1/I2 result now | I5 controller result later | Required proof |
| --- | --- | --- | --- |
| Cloud worker opens an isolated checkout | I1 reports advisory Mode B; I2 prints status only. | Worker submits a versioned request to the controller. | Fresh worktree and matching `source_ref` / `expected_base_sha`. |
| Two workers try to claim one task | Neither helper can claim it. | One SQLite transaction creates one lease; the other receives a deterministic conflict. | Controller transaction and conflict tests. |
| Client retries after timeout | No helper infers success or retries a claim. | Same principal, operation, and idempotency key receive the original receipt; changed content is rejected. | Request-digest and crash/replay tests. |
| Worker loses connectivity after dispatch | No local queue mutation or relay fallback. | Lease remains durable until explicit completion, expiry, or controller recovery. | Lease-expiry and recovery tests. |
| Gossip event is replayed | It remains observational status evidence. | Outbox consumers cannot mutate a task or extend a lease. | Egress-redaction and replay tests. |
| Source branch has moved | I1/I2 do not authorize editing from topology. | Controller rejects a mismatched source line before a lease is issued. | Stale-base and fresh-worktree tests. |

### Required method for each delivery instance

Every I1/I2 follow-up and any I5 implementation must use an isolated worktree
created from an explicit source line, follow
[Orama TDD](../../TDD.md), and keep an
implementer/reviewer ledger under subagent-driven development. Review starts
from the [agent methodology](../../../.agents/skills/agent-methodology/SKILL.md) and
the [code-review entrypoint](../../../.agents/skills/code-review/SKILL.md). Existing
commits are not exempt: before merge, the PR description records the actual
RED/GREEN evidence, focused tests, review result, and any remaining manual
gate.

### I5: Phase 2 real relay is a deferred v2.1 plan

I5 is not a peer-to-peer shell transport. It is the proposed
[Orchestrator Controller satellite](../68-orchestrator-controller-satellite.md):

1. A controller-owned SQLite store is the sole writer for tasks, leases,
   idempotency records, audit records, and an event outbox.
2. Telos supplies the narrow secure transport; Phylax verifies a scoped
   principal capability before task lookup. A self-declared worker name or a
   topology match is never authentication.
3. Each versioned mutation includes an opaque idempotency key, expected task
   version, `source_ref`, and `expected_base_sha`. A transaction grants at
   most one lease and writes its redacted outbox event atomically.
4. Renew, complete, release, fail, and recovery require the authorized
   principal plus the active lease token. Uncertain post-dispatch outcomes
   retain the lease conservatively.
5. GossipBus/GossipMesh receive only redacted post-commit outbox events. They
   cannot create, replay, renew, or resolve claims.

Before code begins, the owner must pass the repository-admission gate in the
v2 document and create a contract-migration ledger spanning persistence,
contract, callers, transport, lifecycle, operations, and tests. The minimum
test matrix covers concurrent claims, idempotent retries, changed-payload key
reuse, stale base rejection, lease recovery, outbox replay, disconnected
clients, and redaction.

### Publication receipt

- I1: [PR #401](https://github.com/diazMelgarejo/Perpetua-Tools/pull/401),
  base `main`, published after the isolated-worktree test and review pass.
- I2: [draft PR #402](https://github.com/diazMelgarejo/Perpetua-Tools/pull/402),
  base I1 branch, published only as a stack for review. It must remain draft
  until an independent review of the final parented diff is attached.
- I5: no branch, no PR, and no implied v1 implementation.

## Mandatory process (every instance)

For **every** work item under this plan (probe tooling, status helper,
future relay, W0-R1 review, worker config change):

1. **Worktree** — fresh `git worktree` from a declared `source_ref` /
   `expected_base_sha`. Never edit the primary dirty checkout for plan
   deliverables. See [Cursor worktrees](https://cursor.com/docs/configuration/worktrees)
   (Agents Window / CLI create isolated checkouts; My Machines does **not**
   auto-isolate).
2. **TDD** — RED → GREEN → refactor. Tests land before implementation.
   Follow [Orama TDD](../../TDD.md) and the ECC
   `tdd-workflow` (unit + integration; no ship without a passing focused
   suite).
3. **Subagent-driven development** — split independent angles into
   parallel subagents (explore / implement / review). Parent agent
   synthesizes; no single-agent “edit everything in place.” Apply the
   [agent methodology](../../../.agents/skills/agent-methodology/SKILL.md) and
   [code-review entrypoint](../../../.agents/skills/code-review/SKILL.md) before
   implementation and before approval.

Skipping any of the three is a process defect for this plan.

## Corrected execution model

The running Cursor worker is a self-hosted **My Machines** worker:

- Cursor hosts the **agent loop** in the cloud.
- Terminal commands, file edits, browser/tool calls execute on the **local
  machine** through the worker’s **outbound** connection.
- It is **not** automatically a cloud checkout, a LAN GossipBus peer, or an
  isolated git worktree.

Cross-ref: [My Machines](https://cursor.com/docs/cloud-agent/self-hosted/my-machines)
(“A worker on your machine opens an outbound connection… The agent loop runs
in Cursor's cloud, but terminal commands, file edits… execute on your
machine”). Same split in
[Choose where Cloud Agents run](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime).

Separate **worktrees** are an Agents Window / CLI feature
([Worktrees](https://cursor.com/docs/configuration/worktrees)), not the default
My Machines assignment model. A task must therefore **prove** its checkout and
coordination-state location before it claims or completes a local board task.

## Verified references (HTTP 200, 2026-09-26)

| Topic | URL | What we verified |
| ----- | --- | ---------------- |
| My Machines | <https://cursor.com/docs/cloud-agent/self-hosted/my-machines> | Outbound worker; `--worker-dir` multi-root; `--name`; personal credential; `--computer-use` optional |
| Team Pools | <https://cursor.com/docs/cloud-agent/self-hosted/pool> | First `--worker-dir` = primary identity; verbose logs = source of truth; up to 20 roots |
| Choose runtime | <https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime> | My Machines vs Pools vs managed cloud; agent loop still in Cursor cloud |
| Worktrees | <https://cursor.com/docs/configuration/worktrees> | Isolated checkouts for Agents Window / CLI; `.cursor/worktrees.json` setup |
| Computer use | <https://cursor.com/docs/cloud-agent/self-hosted/computer-use> | Privileged desktop drive; **off** for coordination |
| CLI using / worktrees | <https://cursor.com/docs/cli/using> | CLI `-w` / worktree invocation |

Research artifacts (local): `/tmp/cursor-worker-research/` (EXA answer +
Firecrawl scrapes). Do not treat scrapes as canonical after doc updates —
re-check the live URLs above.

## Decision

**Do not merge or enable** the draft
`scripts/cursor/remote-coordination.sh` as an “event relay.”

Measured behavior (bridge worktree, 2026-09-26):

- Validates `GOSSIP_PEERS` (must be `<https://…`>) and `GOSSIP_SHARED_SECRET`.
- Then `exec`s local `scripts/agent_coordination.py` (pulse / log).
- **Zero** `curl` / outbound peer POSTs.

That is only correct under **Mode A** (proven shared board). Setting relay
env vars on Mode B to “look configured” is forbidden.

Board cross-ref: W0-R1 is **Answered** — Mode B read-only handoff; a shared-claim
relay needs a separate authenticated protocol (see §Resolution). Superseded
earlier status: held pending a published PT `source_ref` + `expected_base_sha`
(`lesson_a17856504b2a`); empty `depends_on` still ≠ claimable.

## Working World Simulation

The following state machine is the implementation contract. It separates
local execution from authoritative coordination rather than inferring one
from the other.

| State | Inputs proved | Permitted action | Forbidden action | Exit |
| ----- | ------------- | ---------------- | ---------------- | ---- |
| `UNKNOWN` | None | Read-only probe | Any board mutation | `PROBED` |
| `PROBED` | Root, git status, board existence, board device + inode + size | Classify Mode A or B | Treat a board filename or topology match as authority | `MODE_A` or `MODE_B` |
| `MODE_A` | Exact coordinator root plus matching device + inode + size | Read current board state | Infer queue-write authority from the probe | Coordinator-side authorization only |
| `SOURCE_VERIFIED` | Fetchable `source_ref`, matching `expected_base_sha`, fresh worktree | TDD RED, then implementation | Edit a primary/dirty checkout | `READY_TO_CLAIM` |
| `READY_TO_CLAIM` | Fresh board read immediately before claim and coordinator-side authorization | Canonical local claim and execution | Relay emulation | `IMPLEMENTING` |
| `MODE_B` | Root/identity mismatch, missing board, or non-git navigator | Read-only review and PR/handoff evidence | Queue claim, complete, fail, pulse, or log | Local coordinator verification |
| `RESTART_PENDING` | No active session plus operator approval | Restart with explicit roots | Restart during active work | New `UNKNOWN` probe |

`MODE_A` is only an observed topology match. It never authorizes a queue
mutation: source-line, fresh-worktree, and coordinator-side authorization gates
remain mandatory. A worker created in the required fresh worktree is Mode B and
uses a read-only handoff. `MODE_B` never becomes write-capable by setting relay
environment variables.

## Phase 0: Read-only topology probe

### Commands (no board writes)

```bash
pwd
git rev-parse --show-toplevel
git rev-parse --git-common-dir
test -f .state/perpetua_core.db && echo shared-board-present
# identity of the board file (topology matching requires all three values)
python3 -c "import os; s=os.stat('.state/perpetua_core.db'); print(f'dev={s.st_dev} ino={s.st_ino} size={s.st_size}')"
```

Do **not** claim, release, complete, fail, pulse, or log a board row during
this probe.

### Executed result (2026-09-26, designated PT root)

| Check | Result |
| ----- | ------ |
| `pwd` / toplevel | `$PERPETUA_TOOLS_ROOT` |
| `git-common-dir` | `.git` |
| Board file | `shared-board-present` |
| DB identity | Captured device + inode baseline; re-stat before every write-capable run |

**Verdict:** Mode A is an advisory topology match only for tasks whose
toplevel is this exact root and whose board **device, inode, and size** match
the coordinator baseline. It grants no queue authority. This OpenClaw
meta-workspace and disposable worktrees are **Mode B** and use handoff only.

## Phase 1: Operating modes

### Mode A — Proven shared local board

Use only when the probe’s toplevel and board **device, inode, and size** match
the coordinator baseline. This classification does not authorize a write.

- The canonical coordinator, not the worker probe, makes any direct
  `scripts/agent_coordination.py` mutation decision.
- Before write work: declared `source_ref` + `expected_base_sha`, a fresh
  **worktree** at that source line, and a re-read immediately before claim and
  completion.
- TDD + subagent split remain required for new probe/helper code.

### Mode B — Isolated worktree or checkout

Use when the root differs, the board DB differs/missing, or inode mismatches.

- Cursor task stays **read-only** on the local queue.
- Report via task branch, PR, or handoff artifact
  (`~/.openclaw/state/agent_coordination_handoff.json` pattern).
- Local coordinator performs authoritative queue transitions after verifying
  ref + evidence.
- Do **not** set `GOSSIP_PEERS` / `GOSSIP_SHARED_SECRET` to cosmetics.

## Phase 2: Worker scope (HITL / idle only)

Restart only when active agent work is idle. Prefer `agent worker` (docs) —
`cursor-agent` is a local alias for the agent CLI.

```bash
agent worker \
  --name "condor-openclaw" \
  --worker-dir "$PERPETUA_TOOLS_ROOT" \
  --worker-dir "$REPO_ROOT" \
  start --verbose
```

Cross-ref: [pool multi-repo](https://cursor.com/docs/cloud-agent/self-hosted/pool#register-multiple-repo-roots)
— first `--worker-dir` is primary routing identity; confirm
`workspacePaths` / `x-repository-urls` in verbose logs (dashboard can look
single-repo).

**Do not** enable for coordination unless separately approved:

- `--computer-use` / desktop sharing
  ([Computer use](https://cursor.com/docs/cloud-agent/self-hosted/computer-use))
- Credential minting / dashboard secret sync beyond existing personal auth

## Deferred: Real relay design

Only if Mode B is required **operationally**. A real relay must:

1. Send authenticated HTTPS to a designated coordinator (not local `exec`).
2. Use event IDs + idempotent ingestion.
3. Narrow auth scope (liveness / status).
4. Redact payloads; never log secrets.
5. Keep distributed queue claims out of scope until an atomic shared-claim
   protocol exists (board: W0-R1).
6. Integration tests against a real or test peer — not only argv validation.
7. **Worktree + TDD + subagent-driven** implementation (mandatory).

## Implementation instances (checklist)

Each row is one “instance” and must satisfy §Mandatory process.

| Instance | Mode | Deliverable | Status |
| -------- | ---- | ----------- | ------ |
| I0 Research | — | EXA + Firecrawl → this doc | Done |
| I1 Topology probe script + tests | advisory tooling | `scripts/cursor/topology_probe.py` + pytest | **Dual-branch reviewed (Addendum C)** — prefer authority tip `84523aea` (12/12, advisory); chore/identity superseded; push still HITL |
| I2 Status-only helper (truthful) | advisory / Mode B safe | Reduce or replace wrapper; no fake peer POST | **WIP stacked** — `feat/cursor-i2-truthful-status-20260926` @ `66c2aaa8` on authority `84523aea`; 8+12 tests green; not pushed; not a relay |
| I3 Worker restart | A | `condor-openclaw` with two `--worker-dir`s | HITL / idle |
| I4 Publish bridge `source_ref` | evidence only | Commit/push PT branch for review; does not create shared-claim authority | HITL |
| I5 Real relay (optional) | B only | Spec + tests per Deferred | Not started |

## Acceptance criteria

- [x] Topology probe identifies exact root and board-state mode (device + inode + size).
- [x] Probe reports that it cannot grant queue-write authority.
- [x] No isolated Cursor task writes authoritative local queue transitions
      during Phase 0.
- [ ] Worker registers only intended repositories (after Phase 2 restart).
- [x] Current wrapper remains unmerged as a relay.
- [x] Every code instance used worktree + TDD + subagent-driven development (I1).
- [ ] Future relay passes auth, replay, redaction, disconnected-peer tests.

## Review answers (Cursor agent, 2026-09-26)

1. **Checkout vs worktree:** My Machines preserves the registered
   `--worker-dir` checkout; it does **not** auto-create a git worktree.
   Worktrees are separate (Agents Window / CLI). Always prove `pwd` +
   toplevel + board inode.
2. **Board mutation safety:** The probe never decides this. A topology match
   is advisory; only the canonical coordinator may authorize a mutation.
   Otherwise Mode B is read-only on the queue.
3. **Mode by root:** PT designated root → Mode A when inode matches.
   OpenClaw navigator, ephemeral scratch worktrees, orama-only checkouts →
   Mode B for queue authority.
4. **Flags:** Two `--worker-dir`s + `--name` + `start --verbose` are
   sufficient and least-privileged. Keep `--computer-use` off.
5. **Relay:** Unnecessary after Mode A probe. Fake wrapper must not ship.

## Board / PR cross-references

| Item | Location |
| ---- | -------- |
| W0-R1 status | **Answered** — Mode B read-only handoff; a shared-claim relay needs a separate authenticated protocol. GossipBus task `…W0-R1…5304bd0f` |
| PT#399 gate lessons | Merged — comment-only pointers |
| PT#400 follow-up lessons | [Open PR #400](https://github.com/diazMelgarejo/Perpetua-Tools/pull/400); published head re-measured 2026-09-26 as [`39e8ad4b`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/39e8ad4ba13c8c221104f14e5be243810269903e) — the earlier `6620a15f` is now an ancestor, see the Addendum |
| OSSF on orama | Main via #360; no redundant refresh push |
| Handoff snapshot | `~/.openclaw/state/agent_coordination_handoff.json` |

## Execution log

| When (UTC) | Instance | Evidence |
| ---------- | -------- | -------- |
| 2026-09-26 | I0 | EXA + Firecrawl; URLs HTTP 200 |
| 2026-09-26 | Phase 0 | PT root Mode A; board device + inode captured locally and re-probed per run |
| 2026-09-26 | I1 | Isolated worktree; TDD RED→GREEN produced 7 expected failures before the correction and 11 green focused tests after; local `fe475c62`, **not pushed**, independent review requested on GossipBus |
| 2026-09-26 | Wrapper review | Subagent confirmed `remote-coordination.sh` has no curl; execs local coordination CLI |
| 2026-09-26 | I1 independent review | Cursor agent `cursor-composer-review-20260926`: **approve_with_nits**; 11/11 pass; GossipBus `CURSOR_TOPOLOGY_PROBE_REVIEW_VERDICT`; see §Addendum |
| 2026-09-26 | Addendum C dual-branch review | `cursor-composer-review-20260926`: chore `c67d2610` (10/10, do-not-ship) + identity `fe475c62` (11/11, superseded) + authority `84523aea` (12/12, candidate); GossipBus `CURSOR_TOPOLOGY_DUAL_BRANCH_REVIEW` + snapshots refreshed |
| 2026-09-26 | I2 truthful WIP (stacked) | Fresh worktree on `84523aea`; branch `feat/cursor-i2-truthful-status-20260926` @ `66c2aaa8`; status-only JSON helper; pulse/log refused; GOSSIP_* cosmetics ignored; 20 focused tests; **no push** |

## Addendum — Independent review (2026-09-26)

**Reviewer:** `cursor-composer-review-20260926` (Cursor, read-only)
**Scope:** this plan + local commit `fe475c62` on
`fix/cursor-topology-probe-identity-20260926` (base `c67d2610`)
**Gossip:** `topic=CURSOR_TOPOLOGY_PROBE_REVIEW_VERDICT;status=approve_with_nits`
**Verdict:** Approve with nits. Device-plus-inode identity and inspected-root
`cwd` fix the prior inode-only alias and process-cwd bugs. Plan gates
(Mode A, Phase 2 HITL, wrapper hold, W0-R1) are consistent. Push remains HITL.

### Confirmed

- Mode A requires matching `coordinator_dev` **and** `coordinator_ino` plus
  same resolved toplevel; incomplete identity → Mode B.
- Probe `cwd` reports the inspected root (`root_resolved`), not `Path.cwd()`.
- Focused suite: 11/11 green in worktree
  `wt-probe-identity`.
- Board path is `toplevel/.state/perpetua_core.db` (not git-common-dir). PT
  worktrees without a local `.state/` correctly stay Mode B even though
  GossipBus itself resolves the shared DB via git-common-dir — intentional
  and aligned with “Mode A only at the designated coordinator root.”

### Nits (non-blocking; fold into next I1 polish or publish prep)

| # | Item | Suggestion |
| - | ---- | ---------- |
| N1 | `inode_ok` in `topology_probe.py` | Rename to `identity_ok` (now checks device + inode). |
| N2 | CLI `--coordinator-ino` help text | State that **both** `--coordinator-dev` and `--coordinator-ino` are required for Mode A. |
| N3 | Stale Gossip `WORKER_GUIDANCE_PROBE_TOOL` | Still documents ino-only CLI; refresh the note on publish so agents do not omit `--coordinator-dev`. |
| N4 | `test_mode_b_without_complete_coordinator_identity_…` | Avoid double `_write_board(repo)` when building the incomplete-identity case; one write + partial kwargs is enough. |

### Suggestions (optional follow-ups, not blockers)

| # | Item | Suggestion |
| - | ---- | ---------- |
| S1 | Operator docs / probe JSON | When `board_present=false` in a PT worktree, call out that GossipBus may still share the main checkout DB via git-common-dir — Mode B is about **queue write authority**, not “bus unreachable.” |
| S2 | I2 status helper | Consume the full `(dev, ino)` pair from Phase 0 baseline; refuse Mode A cosmetics if either flag is missing. |
| S3 | Publish path | After optional N1–N4 polish: HITL decide push/PR for topology-probe lineage (`c67d2610` + `fe475c62`); do not unblock W0-R1 until a published `source_ref` + `expected_base_sha` exist. |

### Out of scope for this review

- Phase 2 worker restart (still idle + HITL).
- Merging `scripts/cursor/remote-coordination.sh` as a relay (still forbidden).
- Claiming W0-R1 (still held).

## Addendum B — independent review (cline-session-20260907, 2026-09-26)

**Relationship to Addendum A:** this is a **second, independent** review by a
different agent for the same artifact; it **confirms Addendum A's
`approve_with_nits` verdict** and adds two request-changes items plus a
W0-R1 closure recommendation. Where the two overlap (Addendum A nit N1, rename
`inode_ok` → `identity_ok`) this review agrees. One refinement: Addendum A's
"Confirmed" bullet noting that the probe reports the *inspected* root rather
than `Path.cwd()` is exactly the evidence for C1 below.

**Requested by:** codex-reviewer (`WORKER_GUIDANCE_CORRECTION`, review=requested_no_push).
**Scope reviewed:** this plan plus the I1 artifact
`scripts/cursor/topology_probe.py` at `fe475c62` on
`fix/cursor-topology-probe-identity-20260926`.
**Verdict:** **APPROVE the I1 device-plus-inode correction** for its stated
classification purpose. **REQUEST CHANGES** on C1 and C2 below before any
write-capable use. No push, no edits to implementation code by the reviewer.

### Confirmed independently (measured, not taken on trust)

| Claim in this plan | How it was verified |
| ------------------ | ------------------- |
| Device+inode requirement is implemented **and tested** | Reviewer ran the suite in the I1 worktree: **11 passed**. Test names cover the correction: mode A only on a full match, mode B on device mismatch, on incomplete identity even with the board present, on a symlinked toplevel, and on a non-git root |
| Phase 0 board identity figures are accurate | Measured directly: `dev=16777233 ino=190548900`, matching the recorded `ModeA_PT_ino_190548900` |
| Worktrees are Mode B by construction | Verified rather than assumed: a worktree has no `.state/perpetua_core.db` at all, because `.state` is gitignored, so no worktree can present the board file |
| The relay wrapper has no outbound traffic | Read the 79-line script: it only `exec`s the local `agent_coordination.py` for pulse/log. **Zero** curl, wget, or outbound POST, so the decision to keep it unmerged is sound |
| Process hygiene held for I1 | Both I1 branches are unpublished (`ls-remote` empty) and the I1 worktree is clean |

### Requested changes (before any write-capable use)

**C1 — Mode A is self-attested, not authorization.** `probe()` accepts the
coordinator `dev`/`ino` as caller-supplied arguments and computes the mode for
the root the caller *names* (`repo_root`), not for the process working
directory. A task can therefore pass the values it just observed, or name the
coordinator root while executing elsewhere, and obtain Mode A. Suggested change:
derive the mode from the actual `cwd` (or assert `repo_root == cwd`), and make
the coordinator identity unforgeable — a coordinator-published marker or a
challenge value. As written, Mode A proves internal consistency only.

**C2 — Device plus inode is not a stable identity.** Inode numbers are reused
after delete and recreate on the same device, and `board_size` is captured but
never compared. Suggested change: compare size (already collected, no extra
cost) and ideally a content marker such as the SQLite `user_version` or a known
coordinator row, before granting Mode A.

### Nits and suggestions

- **N1 — State the consequence of the mandatory-worktree rule.** Every instance
  must use a fresh worktree, and every worktree is provably Mode B, so under this
  design a Cursor worker can never legitimately claim queue rows. That is the
  safe outcome and it is also the substantive answer to W0-R1; see below.
- **N2 — I4 hygiene risk.** The bridge worktree
  `pt-cursor-remote-gossip-bridge-20260926` is dirty (4 paths) while holding the
  unmerged relay. Publishing I4 from it would violate this plan's own worktree
  rule and the queue source-line invariant. Clean or recreate it before I4.
- **N3 — Phase 2 acceptance is still unverified.** The
  register-only-intended-repositories criterion depends on inspecting verbose
  `workspacePaths` / `x-repository-urls` output; the single-repo-vs-multi-root
  risk this plan flags remains untested.
- **N4 — Research artifacts live in scratch.** The EXA/Firecrawl material under
  the scratch directory is ephemeral; this environment cleaned three unrelated
  worktrees mid-session without warning. Persist anything the plan relies on, or
  cite only the live URLs (as the doc already correctly prefers).
- **N5 — Reviewer hygiene note.** One reviewer pass this cycle reported a
  "duplicate lesson id" from a raw text grep. Parsed properly the id occurs once
  and the second match was a *citation* from another row. Worth a standing rule:
  verify by parsing structures, not by grepping serialized text.
- **N6 — Pre-existing duplicate ids on the branch.** The PT#400 branch carries
  five lesson ids that each map to two distinct payloads
  (`…55a1907f1dd4`, `…92096134dfee`, `…28698cd86a94`, `…e8b235e08c40`,
  `…c3a0687d366c`). They predate the 2026-09-26 commit set, so they are not
  introduced here, but an id that maps to two payloads makes id-keyed lookups
  ambiguous and deserves a dedupe pass.

### Recommended status change for W0-R1

W0-R1 asks whether a secure shared-claim transport exists. On the evidence in
this plan the answer is **no, and not by accident**: Mode A requires the primary
coordinator root, while the mandatory-process rule requires a worktree for every
instance, and every worktree is Mode B. Recommend closing W0-R1 as *answered —
Mode B read-only handoff only*, with I4 (publish the bridge `source_ref`) recorded
as the sole HITL path to Mode A, rather than leaving the row held indefinitely.
Empty `depends_on` still does not make a row claimable.

### Housekeeping applied by the reviewer (disclosed)

- Corrected the stale PT#400 published-head SHA in the cross-reference table
  (`6620a15f` → `39e8ad4b`, the former now an ancestor) — the only substantive
  edit made outside this addendum.
- Fixed 7 MD034 bare-URL violations in the Verified references table and 1
  MD012 duplicate blank line near the cross-reference table. `markdownlint-cli2`
  with the repository config now reports **0 issues** for this file. These were
  pre-existing; recorded here because the reviewer touched lines outside its own
  addendum.
- W0-R1 status reconciled with the plan's own header: the two body references
  that still said "held" (`§Decision` cross-ref and the cross-reference table)
  now read **Answered**, matching line 17 and §Resolution. Addendum A's
  out-of-scope line "Claiming W0-R1 (still held)" is left untouched deliberately
  — it is a historical review record from before the disposition was decided.
- Reviewer error corrected in flight: an earlier note claimed a duplicate
  `lesson_0c7355deb939`. Parsed properly that id occurs **once**; the second text
  match was a citation from another row. The real duplicate finding is N6.

### Correction to this plan's cross-reference table

The PT#400 row cites the published head as `6620a15f`. Re-measured 2026-09-26:
the published branch head is now **`39e8ad4b`**, and `6620a15f` is an ancestor of
it. The superseded row is corrected in place above; the branch has continued to
advance, so re-read the ref rather than trusting a recorded SHA.

## Resolution — topology probe authority boundary (2026-09-26)

This resolution incorporates the valid C1/C2 review findings without turning a
local observation into a security credential.

1. **C1 resolved:** `topology_probe.py` is an advisory classifier. Its output
   now states `queue_write_authority: false` for every result. A matching root
   and identity tuple is useful evidence for the canonical coordinator, but no
   Cursor worker may infer mutation authority from it. Coordinator-side command
   policy remains the only authority boundary.
2. **C2 resolved:** a topology match now requires the complete observed
   `(device, inode, size)` tuple. This makes a stale delete/recreate baseline
   less likely to be mistaken for the current board, but is intentionally not
   presented as cryptographic or authorization evidence.
3. **W0-R1 closed as answered:** mandatory fresh worktrees are Mode B because
   their local state directory is absent. They submit a branch/PR/handoff; the
   coordinator verifies evidence and performs any authoritative transition.
   A future distributed claim relay requires its own authenticated, atomic
   protocol and is not implied by I4 publication.
4. **I4 remains HITL and non-authoritative:** recreate or clean its dirty
   bridge worktree before any publication. Publishing a `source_ref` is review
   evidence only, never a path around the coordinator boundary.

Validation for the corrected I1 implementation: the focused probe suite is
12/12 green in a fresh worktree. The corrected commit is local and unpublished
pending independent review; do not treat any commit identifier recorded in
earlier addenda as the final candidate.

## Addendum C — Dual-branch thorough review (cursor-composer-review-20260926, 2026-09-26)

**Relationship:** Third review pass after Addendum A (`approve_with_nits` on
`fe475c62`), Addendum B (Cline C1/C2 REQUEST CHANGES), and the plan
§Resolution (advisory + `(dev,ino,size)` + W0-R1 answered). This addendum
re-reads GossipBus, then thoroughly reviews **both** original I1 branches
plus the post-Resolution **authority** successor that is now the publish
candidate.

**Reviewer:** `cursor-composer-review-20260926` (Cursor, read-only on code;
wrote this addendum + GossipBus sync only).
**Gossip:** `topic=CURSOR_TOPOLOGY_DUAL_BRANCH_REVIEW` /
`WORKER_PLAN_ADDENDUM_C`.
**Headline verdict:** Prefer
`fix/cursor-topology-probe-authority-20260926` @ `84523aea` for any
HITL push/PR. Treat `chore/…` and `fix/…-identity…` as superseded local
history. Approve authority tip **as advisory tooling only** after confirming
no consumer treats Mode A as a write grant.

### Board digest (newest first, measured this pass)

| Agent | Topic | State |
| ----- | ----- | ----- |
| `codex-migration-orchestrator` | `REBASE_AND_OSSF_STATUS` | Authority branch rebased clean; focused probe tests **12/12**; not pushed |
| same | `CURSOR_TOPOLOGY_PROBE_CORRECTION` | C1/C2 accepted via advisory classifier + `(dev,ino,size)` + `queue_write_authority=false` |
| same | `CURSOR_WORKER_DOCS_RECONCILED` | Plan updated; W0-R1 → Mode B handoff; dirty I4 bridge must be cleaned/recreated |
| `cline-session-20260907` | Addendum B / `PLAN ADDENDUM SAVED` | Approve I1 identity fix; **REQUEST CHANGES** on C1/C2 before write-capable use |
| `cursor-composer-review-20260926` | Addendum A / prior board sync | `approve_with_nits` on `fe475c62`; N1–N4 + S1–S3 |
| `codex-reviewer` | `CURSOR_TOPOLOGY_PROBE_REVIEW` / `_REQUEST` | Original inode-only + process-cwd findings; requested independent review of `fe475c62` |
| `cursor-composer-mig-20260925` | `WORKER_GUIDANCE_*` wave | Initial plan publish; I1 at chore tip 10/10; wrapper/Phase2/W0-R1 holds |

### Branch map

| Branch | Worktree | HEAD (this pass) | Focused tests | Role |
| ------ | -------- | ---------------- | ------------- | ---- |
| `chore/cursor-topology-probe-20260926` | `wt-probe-identity` (original) | `c67d2610` | **10/10** | Original I1 — **do not ship** |
| `fix/cursor-topology-probe-identity-20260926` | `wt-probe-identity` | `fe475c62` | **11/11** | Device+inode + inspected `cwd` — **intermediate / superseded** |
| `fix/cursor-topology-probe-authority-20260926` | `wt-probe-authority` | `84523aea` (rebased; earlier board note cited pre-rebase `e9156fb4`) | **12/12** | **Current publish candidate** — advisory + size |

**Remote presence:** all three branches `ls-remote` empty (unpublished).
**Lineage:** `c67d2610` ⊂ `fe475c62` (fast-forward identity on chore). Authority is a
**rebased rewrite** of the same four logical commits onto PR#400
(`a242bb24`), not a fast-forward of `fe475c62`. Do not treat older SHAs in
Addendum A/B as the final candidate (matches §Resolution).

```text
chore (c67d)  --fix-->  identity (fe475)  --rebase+authority-->  authority (84523)
   DO NOT SHIP              SUPERSEDED                              CANDIDATE
```

### Branch 1 — `chore/cursor-topology-probe-20260926` @ `c67d2610`

**What it got right**:

- Mode A/B skeleton with board path under `toplevel/.state/perpetua_core.db`
- Non-git roots → Mode B (commit `c67d2610`)
- No GossipBus / `agent_coordination` import (static test)
- TDD shape with focused pytest module

**Blockers (confirmed by later reviews and re-verified)**:

1. Mode A compared **inode only** → cross-filesystem alias risk.
2. `cwd` reported `Path.cwd()`, not the inspected root → misleading topology
   evidence (exact trigger for later C1 discussion).
3. Module docstring implied Mode A “may use” the shared board — authority
   leakage in wording.

**Diff vs `33186a1b` (then-main):** +2 files only
(`scripts/cursor/topology_probe.py`, `tests/test_cursor_topology_probe.py`).

**Verdict:** Historical only. Superseded. Do not push.

### Branch 2 — `fix/cursor-topology-probe-identity-20260926` @ `fe475c62`

**Fixes vs chore (two-file diff `c67d2610..fe475c62`)**

- Requires matching `coordinator_dev` **and** `coordinator_ino`
- `cwd` = inspected `root_resolved`
- Adds device-mismatch + incomplete-identity tests (11 total)
- Matches Addendum A confirmed bullets

**Still open relative to Addendum B C1/C2**:

1. **C1:** Mode A remains self-attested — caller supplies identity args and
   names `repo_root`. No cwd bind; no unforgeable marker. Addendum A
   `approve_with_nits` is correct *for classification*; insufficient *as a
   write gate*.
2. **C2:** `board_size` collected but **not compared**; inode reuse after
   delete/recreate still possible.
3. Residual nits from Addendum A: `inode_ok` name, CLI help still ino-centric,
   awkward double `_write_board` in incomplete-identity test.

**Live probe (this pass, identity tip):** designated PT root → Mode A;
OpenClaw navigator + probe worktrees → Mode B (`board_present=false`).

**Verdict:** Approve as identity correction; **not** the final publish tip.

### Branch 3 (successor) — `fix/cursor-topology-probe-authority-20260926` @ `84523aea`

Implements plan §Resolution relative to identity tip:

| Change | Detail |
| ------ | ------ |
| Soft C1 | Every result includes `queue_write_authority: false` (even Mode A) |
| Soft C2 | Match requires full `(dev, ino, size)` tuple |
| Naming | `inode_ok` → `identity_ok`; exposes `topology_match` |
| CLI | `--coordinator-size`; help states all identity values required for Mode A |
| Tests | 12th case: size mismatch → Mode B; Mode A asserts `qwa is False` |
| Docs string | Explicitly “advisory only; never grants queue-write authority” |

**Probe-only range** `a242bb24..84523aea`: 4 commits, **2 files**, +454 lines.
Diffing vs old `33186a1b` falsely looks like memory baggage because PR#400 sits
in between — publish from tip or cherry-pick the four probe commits only.

**Live probe (authority tip, coordinator baseline = live PT board stat)**:

| Root | mode | board_present | topology_match | queue_write_authority |
| ---- | ---- | ------------- | -------------- | --------------------- |
| Designated PT checkout | A | true | true | **false** |
| OpenClaw navigator (non-git meta) | B | false | false | false |
| Identity worktree | B | false | false | false |
| Authority worktree | B | false | false | false |
| Same PT root, `coordinator_size = live_size - 1` | B | true | false | false |
| Same PT root, size omitted (identity-era call) | B | true | false | false |

**Remaining findings on authority tip**:

| Severity | Finding |
| -------- | ------- |
| Important | C1 is **policy-labeled**, not enforced in-process. A worker can still compute Mode A for any named root with a caller-supplied tuple. Safe only if every consumer ignores Mode A for mutations — must be true of I2 / `agent_coordination.py`, not just this script. |
| Important | **Size is volatile.** Live board ~3.2 MB; size−1 flips Mode A→B. Correct for stale baselines, but operators must refresh `(dev,ino,size)` immediately before each probe or Mode A becomes flaky under gossip write load. |
| Suggestion | Still no content marker (`user_version` / known row) — §Resolution intentionally stops short of crypto; document size as a cheap ratchet, not proof. |
| Suggestion | Board path remains toplevel `.state`, not git-common-dir — correct for Mode B worktrees; keep Addendum A S1 wording (bus may still be shared via common-dir; probe is about write-authority framing). |
| Publish hygiene | Push from tip / cherry-pick probe-only commits; do not open a PR whose base makes PR#400 memory look like new delta. |
| Process | I4 bridge worktree still dirty (Addendum B N2) — still blocks “publish bridge `source_ref`” as a clean HITL path. Phase 2 + fake relay holds unchanged. |

**Verdict:** Best current tip. **Approve for HITL publish as advisory tooling
only**, contingent on confirming no caller treats `mode == "A"` as a write grant.

### Comparative recommendation

1. Prefer **`fix/cursor-topology-probe-authority-20260926` @ `84523aea`** for
   any push/PR of I1.
2. Leave chore/identity local or delete after authority lands; do not dual-publish.
3. Keep holds: Phase 2 idle+HITL; fake `remote-coordination.sh` relay unmerged;
   I4 clean/recreate before publish; W0-R1 answered as Mode B handoff per
   §Resolution (not “claim when `source_ref` appears”).
4. Before merge: grep consumers for `mode == "A"` / missing
   `queue_write_authority` checks.
5. On publish, refresh stale Gossip `WORKER_GUIDANCE_PROBE_TOOL` (still documents
   ino-only CLI from the chore era).

### Out of scope for this addendum

- Editing probe implementation (read-only review).
- Pushing any branch.
- Phase 2 worker restart.
- Cleaning the I4 bridge worktree (called out only).
- Orama OSSF residual branch (noted on board as separate; not push).

## Addendum D — branch review, PR scope and merge order (cline-session-20260907, 2026-09-26)

**Relationship:** fourth review pass, after Addendum A (`approve_with_nits`),
Addendum B (Cline C1/C2 REQUEST CHANGES) and Addendum C (Cursor dual-branch, same
publish preference), and after the §Resolution decision (advisory classification,
`(dev,ino,size)` identity, W0-R1 answered). Addendum D does not restate those; it
records what this pass **measured or changed**.

### Independently verified this pass (not restated from other reviews)

| Item | Measurement |
| ---- | ----------- |
| Authority suite | Ran the suite myself in `pt-cursor-topology-probe-authority-20260926`: **12 passed** |
| Lint / static checks | `ruff check` → **All checks passed**; worktree clean; authority branch **0 behind** main after rebase; identity branch **1 behind** (stale) |
| Live probe, PT root + live baseline | `mode=A`, `topology_match=True`, **`queue_write_authority=False`** |
| Live probe, same root, `size-1` | `mode=B`, `topology_match=False` (stale baseline is caught) |
| Live probe from the authority worktree | `mode=B`, `board_present=False` (no board file in any worktree) |
| Relay merged anywhere? | `remote-coordination.sh` **absent from `origin/main`** — unmerged, confirmed |
| Any consumer of probe results? | **Zero.** No file outside the probe's own tests references `topology_probe`, `queue_write_authority` or `topology_match` |

### Correction to Addendum B C2 (my own recommendation, improved by evidence)

Addendum B asked for `board_size` to be compared, and the authority branch now
does. That catches stale baselines (verified above). But **size is a moving
property of a live board that receives gossip writes**, so binding identity to it
makes Mode A sensitive to baseline freshness and can turn flaky under write load.
A 4-second sample showed no change, which does not refute the risk. Preferred
refinement: a **stable marker** that does not move on ordinary writes — a
coordinator-owned marker outside the database, or SQLite `user_version`, which
changes only on schema migration. Keep size at most as a cheap ratchet, and
document it as **not** proof.

### The write-grant question is currently moot, and that changes the PR story

§Resolution and Addendum C say the "Mode A is not a write grant" property "must
be true of I2 / `agent_coordination.py`, not just this script". Measured: **no
consumer exists yet** — nothing in the repository reads the probe outside its own
tests. So the risk is moot today, and equally the PR ships **advisory tooling that
nothing calls**; the real gate is the I2 wiring, not an existing consumer.

### I2 / I4 bridge worktree — cleaned by this pass

Addendum C recorded "Cleaning the I4 bridge worktree (called out only)". This pass
performed it without discarding work: the four previously untracked/modified paths
were committed locally on `feat/cursor-remote-gossip-bridge-20260926` as
**`1e9f5019` "WIP(cursor): I2 bridge scaffold - DO NOT MERGE AS A RELAY"** (all four
gates pass, not pushed, worktree now clean, files idle ~8.5 h with no open handles
before the commit). The commit message records that the wrapper validates relay env
vars and then execs the **local** CLI while its output claims a relay is
configured — misleading in Mode B, and precisely what I2 must replace with a
truthful status-only helper. The `cloud-bootstrap.sh` status call is already
truthful (no network, no misleading heartbeat).

### PR scope and merge order (definitive)

| Branch | Commits | PR-ready? | Order |
| ------ | ------- | --------- | ----- |
| `fix/cursor-topology-probe-authority-20260926` @ `84523aea` | 4 | **Yes** — rebased, reviewed twice, 12/12, ruff clean | **First, and the only I1 PR** |
| `feat/cursor-remote-gossip-bridge-20260926` @ `1e9f5019` | 1 (WIP) | **No** — relay must not ship as a relay; needs I2 rework first | **Not yet; I2 after I1** |
| `fix/cursor-topology-probe-identity-20260926` @ `fe475c62` | 3 | No — superseded, 1 behind main | Do not open; supersede |
| `chore/cursor-topology-probe-20260926` @ `c67d2610` | 2 | No — historical | Do not open; delete after I1 lands |

So there are **two branches that could eventually become PRs, but only one that
should now**: publish the authority branch; the bridge follows only after I2 makes
it truthful. Publish the authority branch **from its tip or by cherry-picking its
four probe commits**, so the diff cannot be misread as new PR#400 memory (a diff
against an old base such as `33186a1b` falsely shows memory baggage because PR#400
sits in between).

### Lint status of this document

Lint errors accumulated across the concurrently-written sections (three MD036
emphasis-as-heading lines in §Resolution, plus MD040 language-less fence and two
more MD036 lines in Addendum C) are **fixed** mechanically: the fence now declares
a language and the standalone bold lines carry a trailing colon so they are no
longer parsed as headings. `markdownlint-cli2` with the repository config now
reports **0 issues** for the whole file. Addendum D itself contributed no issues.
