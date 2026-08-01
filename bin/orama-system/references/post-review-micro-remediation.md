# Post-Review Micro-Remediation Pattern

> **Role:** single reusable pattern for addressing CodeRabbit / human review
> findings after a PR is opened, without accumulating history churn or
> losing mechanical attribution. Do not duplicate this logic into individual
> skills — link here.
> **Origin:** evolved through trial and error during PT PR #205/#206 —
> multiple review rounds, a rogue-commit incident on `main`, a branch reset,
> and a follow-up review — formalized 2026-07-13.
> **Underlying principle:** minimize history churn after review; make every
> remediation mechanically attributable to the finding that caused it.

---

## The 6 phases

### Phase 0 — Freeze

- Do not continue developing on `main`.
- Treat the reviewed PR branch as the only write target until review is complete.
- **Mechanically enforced (added 2026-07-13):** `.githooks/pre-push` blocks
  direct pushes to `refs/heads/main`/`master` by default (escape hatch:
  `ALLOW_MAIN_PUSH=1`), synchronized identically across `Perpetua-Tools` and
  `orama-system`. `.github/workflows/main-push-guard.yml` is the visibility
  backstop for pushes that bypass the local hook (`--no-verify`) — it flags,
  it cannot block after the fact. Neither substitutes for GitHub branch
  protection on `main`, which requires `administration` scope not available
  to this project's tokens; that must be configured manually in repo
  Settings for durable, unbypassable enforcement. This closes the loop from
  the incident that motivated the doctrine: the doctrine's own authoring
  commit was briefly pushed straight to `main` before this guard existed.

### Phase 1 — Root-cause clustering

- Group review comments by underlying invariant (encoding, persistence,
  concurrency, lifecycle, security, etc.) — not by file or by comment order.
- Fix the abstraction once instead of applying isolated per-comment patches.
- Example: 3 independent copies of an undefined-heartbeat-handler bug across
  `agent_coordination.py`, `agent_coordination_legacy.py`, and
  `agent_coordination_core.py` cluster under "duplicated dispatch logic" —
  the durable fix is a shared facade, not 3 separate patches.
- **Check CI failures against review findings before treating them as
  separate tasks.** A CI failure and a review comment that point at the
  same file are often the same bug. Confirm by running the actual failing
  CI command locally (matching CI's own invocation — same tool, same
  config, same identity/env setup — not an approximation), not by
  assuming they're unrelated.
  Example (PT PR #306): a `repo_hygiene.py` CI failure blocking a
  temporary absolute path leaked into a tracked memory doc, and a
  CodeRabbit review finding on the same lines asking for local paths to
  be removed, were the identical bug — fixing the review finding closed
  the CI failure, verified by re-running `repo_hygiene.py` locally
  rather than assumed.
- **When the same claim is duplicated across multiple tracked copies**
  (a source-of-truth file plus its rendered output, a cached/graduated
  snapshot, and prose elsewhere restating it), the fix differs by
  document type — check which kind you're touching before editing:
  - **Append-only historical records** (lessons, audits, vulnerability
    memory, review ledgers, and anything else whose value depends on
    an intact chain of what was actually claimed and when) must never
    be rewritten in place. A direct edit destroys the original entry —
    there is no queryable trace within the data itself of what it used
    to say, which is exactly the auditability the record exists to
    provide. Instead: **append a superseding correction that
    references the original entry** (e.g. a new record with
    `supersedes: <original-id>`, or an explicit "superseded by"
    back-reference on the original), then regenerate derived copies
    (a rendered markdown file, a cache) from the corrected append-only
    source rather than hand-patching them.
  - **Non-historical documents** (working docs, this doctrine file
    itself, prose that merely restates a claim rather than being the
    system of record for it) can and should be fixed once at the
    source and propagated identically to every copy in the same
    commit — never edited independently per copy, which drifts.
  Example (PT PR #306): the same corrected claim (cherry-pick
  completion must check the git index, not just grep for conflict
  markers) lived in a lessons.jsonl entry, its rendered LESSONS.md
  bullet, a graduated candidate JSON snapshot, and a working-doc's
  prose restating it. lessons.jsonl and the graduated candidate are
  append-only historical records — the actual remediation there should
  have appended a new, superseding entry referencing the original
  rather than mutating the original claim field in place, which is
  what happened; that specific commit is a worked example of the
  mistake this guidance now exists to prevent, not a model to repeat.
  LESSONS.md (machine-rendered from lessons.jsonl) and the working
  doc's restating prose are the two copies that were correctly in
  scope for direct, in-place correction.

### Phase 2 — Branch discipline

- Work only on the open PR branch.
- Keep commits cohesive by failure class (one commit per root-cause cluster
  from Phase 1, not one commit per file or per review comment).
- Preserve the original PR scope and description; append updates rather
  than replacing them.

#### PR body updates (mandatory — never skip)

Open PR descriptions are **append-only historical records** during remediation.
Delta-only writes clobber the original Summary — documented 5+ times
(see [`pr-body-anti-clobber-incident-ledger.md`](pr-body-anti-clobber-incident-ledger.md)).

```text
READ → BACKUP → MERGE (append-only) → WRITE (full merged body)
```

| Step | Action |
| --- | --- |
| READ | `gh pr view <N> --json body` |
| BACKUP | `.git/pr-body-backups/<slug>-pr<N>-<ts>.md` |
| MERGE | Keep `## Summary`; append `## Follow-up:` chronologically |
| WRITE | `scripts/cursor/append-pr-body.sh` — **preferred** |

**Forbidden:**

- `ManagePullRequest update_pr` with `body=` containing only the latest remediation delta
- Skipping backup on "small" follow-ups
- Rewriting or deleting the original Summary

**Mechanical gates (use them):**

- After commit, before push: `scripts/git/remind-pr-body-append-only.sh`
- Audited publish: `publish-clean-branch.sh` (strict mode by default)
- CI Layer 6: `scripts/git/verify-pr-body-not-clobbered.sh`

**Canonical skill:** [`cursor-pr-body`](../skills/cursor-pr-body/SKILL.md)  
**Execution frugality:** [`agent-execution-frugality-reference-card.md`](agent-execution-frugality-reference-card.md)

#### Guard script sync (before cross-repo propagation)

Edit orama `scripts/git/` canonical only. Before
`sync-attribution-guard-scripts.sh`, ensure **neither canonical nor target**
has uncommitted changes to guard-sync paths — sync aborts otherwise to prevent
dropping local harmonization work.

### Phase 3 — Integration

- Merge the reviewed PR.
- If post-merge problems are discovered, move `main` back to the last
  common ancestor with the remediation branch (when project policy allows),
  rather than accumulating revert commits that complicate later
  reconciliation. Revert chains make history harder to reason about with
  every additional revert; a clean ancestry reset is a single, auditable
  operation.
- **Before any reset, create a safety ref** (tag or branch) pointing at the
  commit about to be discarded. Never discard unique work — verify the
  content is preserved elsewhere (another branch, a safety ref) before
  resetting.
- Re-evaluate whether the remediation branch actually requires a rebase.
  If it already descends cleanly from the restored base
  (`merge-base(main, branch) == restored_base`), do not rebase. Rebase is a
  means, not a cleanliness ritual — don't rewrite an already-reviewable
  branch merely to remove an old merge commit when there's no missing base
  work.

### Phase 4 — Verification

- Run the full regression suite.
- For every review finding, confirm it is either:
  - **fixed** — with a regression test proving the fix (and, where
    practical, proving the test fails on the pre-fix code),
  - **intentionally superseded** by a deeper abstraction fix (state which
    fix supersedes it and why the original finding no longer applies), or
  - **documented as not applicable** — with a one-line reason, not silence.

### Phase 5 — Closure

- Leave the branch open for human review if requested.
- Merge only after review approval.

---

## Enforcement — reference this doc, don't duplicate it

Each consuming skill imports only the phases it needs, per the modular
Skillify pattern:

| Skill | Phases it needs |
| --- | --- |
| [`agent-methodology`](../skills/agent-methodology/SKILL.md) | All 6 — this is the doctrine's home methodology |
| [`code-review`](../skills/code-review/SKILL.md) | Phase 1 (root-cause clustering), Phase 4 (verification gates) |
| [`git-history-surgery`](../skills/git-history-surgery/SKILL.md) | Phase 3 (integration — safety refs, reset-vs-rebase decision) |
| [`gstack`](../gstack/SKILL.md) | Phase 0 (freeze), Phase 5 (closure) — AutoPlan review gating |
| [`cursor-pr-body`](../skills/cursor-pr-body/SKILL.md) | Phase 2 (PR body append-only workflow) |
| [`skillify`](../skills/skillify/SKILL.md) | Phase 2 (branch discipline) — modular-skill-authoring pattern |
| [`ecc-sync`](../skills/ecc-sync/SKILL.md) | Phase 5 (closure) — post-merge instinct import |
| [`hermes-harness`](../skills/hermes-harness/SKILL.md) | Phase 0 (freeze), Phase 2 (branch discipline) — multi-agent dispatch must not write to `main` mid-review |
| [`mcp-orchestration`](../skills/mcp-orchestration/SKILL.md) | Phase 1 (root-cause clustering) — routing bugs across providers cluster the same way as coordination-dispatch bugs did |

---

## Related

- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md) —
  the nested-branch merge protocol this pattern complements (that doc covers merging
  concurrent branches; this one covers remediating a single branch after review)
- [`integrative-merge.md`](../skills/oramasys-method/references/integrative-merge.md) —
  synthesize, never amputate; six resolution modes referenced by Phase 3's
  reset-vs-rebase decision
- [`pr-body-anti-clobber-incident-ledger.md`](pr-body-anti-clobber-incident-ledger.md) —
  incident record + enforcement ladder for PR body updates
- [`learn-eval-ecc-ritual-reference-card.md`](learn-eval-ecc-ritual-reference-card.md) —
  lesson → instinct → `/ecc-sync` pipeline after remediation closes
- [`agent-execution-frugality-reference-card.md`](agent-execution-frugality-reference-card.md) —
  tool use, git discipline, and elegance heuristics for multi-repo sessions
- PT `.agent/AGENTS.md` § Multi-agent merge conflict protocol — portable-brain
  summary of the sister pattern for concurrent branches
