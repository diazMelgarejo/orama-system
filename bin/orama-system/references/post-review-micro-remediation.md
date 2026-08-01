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

## The 7 phases

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
- **Run the actual authoritative tool, not a description of it.** "This
  should lint clean" is not verification; running `markdownlint-cli2` (or
  the equivalent for the finding's domain) and reading its real output is.
  The same applies to re-running a fixed script directly, not just
  re-reading the diff.

**Verification gotchas** (each cost real time this doctrine's own
worked examples were built from — check these explicitly, don't assume
a status field or a first glance is accurate):

- A PR-list API endpoint's `merged` field is unreliable — it has been
  observed `null` for PRs that were, in fact, merged. Always confirm via
  the single-PR endpoint (`GET /pulls/{number}`), which reports `merged`
  accurately.
- A squash-merged branch will never show as a git ancestor of the branch
  it merged into (`git merge-base --is-ancestor` returns false) — that
  is expected, not a sign the merge failed. Verify squash-merged content
  by checking that the specific IDs/content actually exist in the target
  branch, not by ancestry.
- A diff-scoped CI lint step (one that only lints files a PR *changed*)
  still lints the **whole file**, not just the changed hunk, once any
  line in that file is touched. Expect pre-existing violations elsewhere
  in a touched file to surface for the first time. Fix them properly if
  the file is genuine hand-authored prose; exclude the file from the
  lint scope only if it is machine-rendered/append-only data (e.g. a
  lessons log) where line-length rules don't meaningfully apply.
- `git stash` used mid-merge, even for an unrelated, seemingly read-only
  purpose, can silently overwrite files already resolved and re-saved
  after the stash was created when popped — with no warning and no
  conflict marker. Avoid stashing during an unresolved merge; if
  unavoidable, re-verify every file the stash touches against its
  expected post-resolution state immediately after popping.
- Before rebasing, resetting, or re-merging a branch already pushed
  earlier in the same session, fetch the actual remote tip first. A
  local checkout that's fallen behind a push made moments earlier
  diverges silently and produces a merge/rebase based on stale state.
- A test that duplicates production logic as a hardcoded literal (a
  regex, a constant, a list of values) rather than reading it from the
  production source will pass or fail against a stale copy forever once
  the two diverge — the test keeps "passing" while the thing it exists
  to catch a regression in has already regressed. Extract the actual
  value from the production source at test time instead. Verify the
  fix is real, not just plausible: deliberately break the production
  value, confirm the test now fails loudly (not silently passes), then
  restore it and confirm the real suite passes normally.
- A fix applied to a recovery/fallback path doesn't mean the primary
  ("happy") path got the same fix — they're separate code, reviewed
  and touched independently, and a finding on one doesn't retroactively
  audit the other. Check every path a review's finding is adjacent to,
  not only the one line it cited.

### Phase 5 — Closure

- Leave the branch open for human review if requested.
- Merge only after review approval.

### Phase 6 — Cross-repo synchronization

Applies whenever the file(s) a review finding touches are shared between
repos under an established sync policy (e.g. orama-system's canonical
`scripts/git/*` mirrored into Perpetua-Tools) — not every remediation,
only ones touching files with a sibling copy elsewhere.

- **A finding on one repo's copy of a shared file is a signal to check
  the sibling repo's copy, not just fix the one you were told about.**
  Diff the sibling's current content against the pre-fix content on the
  side you were reviewing — if it matches, the same bug is almost
  certainly present there too, whether or not a review caught it on
  that side.
- **Verify before assuming identical content means an identical fix
  applies.** Confirm the sibling's pre-fix state actually matches (or
  is close enough that the same patch is correct) before copying a fix
  over — don't assume synchronization from the sync policy's existence
  alone.
- **After fixing both sides, verify full parity with a real diff**
  across every file the shared change touched — not a description of
  what should now match, an actual `diff`/`diff -q` confirming it does.
- **Fix both locally, push once per repo, to the existing open PR
  branch on each side.** Do not close one PR and open a new one to
  represent the same synchronized edit, and do not push incrementally
  in several small rounds when the fix is already fully known on both
  sides. Two PRs that represent one logical, bidirectionally-synchronized
  change should open, update, and close in tandem — never fragmented
  into a chain of superseding PRs, which makes the actual change harder
  to review and the sync history harder to reconstruct later.
- **Check for gaps running the *other* direction too.** A sync pass
  triggered by one repo's review can still surface content the *other*
  repo has that the first one is missing (e.g. a test file covering a
  script that exists on both sides but was only tested on one) — the
  direction the fix is flowing in this specific finding doesn't mean
  every gap between the two repos flows the same way.

---

## Enforcement — reference this doc, don't duplicate it

Each consuming skill imports only the phases it needs, per the modular
Skillify pattern:

| Skill | Phases it needs |
| --- | --- |
| [`agent-methodology`](../skills/agent-methodology/SKILL.md) | All 7 — this is the doctrine's home methodology |
| [`code-review`](../skills/code-review/SKILL.md) | Phase 1 (root-cause clustering), Phase 4 (verification gates) |
| [`git-history-surgery`](../skills/git-history-surgery/SKILL.md) | Phase 3 (integration — safety refs, reset-vs-rebase decision), Phase 6 (cross-repo sync — same discipline as this skill's own cross-host sync card, applied to review remediation specifically) |
| [`gstack`](../gstack/SKILL.md) | Phase 0 (freeze), Phase 5 (closure) — AutoPlan review gating |
| [`cursor-pr-body`](../skills/cursor-pr-body/SKILL.md) | Phase 2 (PR body append-only workflow) |
| [`skillify`](../skills/skillify/SKILL.md) | Phase 2 (branch discipline) — matches the modular-skill-authoring pattern this doc itself follows |
| [`ecc-sync`](../skills/ecc-sync/SKILL.md) | Phase 5 (closure) — post-merge instinct import |
| [`hermes-harness`](../skills/hermes-harness/SKILL.md) | Phase 0 (freeze), Phase 2 (branch discipline), Phase 6 (cross-repo sync — this is where PT ↔ orama harness integration actually lives; `pt-orama-harness-integration` is a redirect stub to this skill) — multi-agent dispatch must not write to `main` mid-review |
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
