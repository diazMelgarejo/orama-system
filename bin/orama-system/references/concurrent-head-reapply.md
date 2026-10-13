# Concurrent Head Reapply — when a PR branch advances under you

> **Role:** the single canonical rule for "someone (or some agent) pushed to
> the PR branch while I was working." Link here; do not restate it in
> individual skills.
> **Origin:** Perpetua-Tools (PT) memory re-learned this rule eight separate
> times between 2026-06-22 and 2026-10-13 UTC (2026-10-14 PHT — the latest
> entry was accepted 20:00 UTC, which is already the next day in the
> Philippines; ledger below). Each time it was
> inscribed as a local lesson and each time the next session had to rediscover
> it. This card is the end of that loop: orama-system is canonical, PT mirrors.
> **Underlying principle:** a PR branch is a shared linear record. Catching up
> to it is a *delta* problem, not a *history* problem.

---

## The rule

When the head of an open PR branch advances while you hold local work for it:

1. **Re-read the new head.** Fetch, then read what actually landed.
2. **Reapply your verified delta directly onto that head.** Your delta is the
   set of changes you verified (tests green, gates passed) against the *old*
   head; re-derive it as a patch or cherry-pick and apply it to the new one.
3. **Re-verify on the new head** (the tests and gates that cover the delta),
   then push as a plain fast-forward.
4. **Do not create a merge or reconciliation commit merely to catch up.** A
   catch-up merge adds a node to the PR history that carries no change of its
   own, and a catch-up rebase rewrites commits other agents already hold.

A merge commit is justified by a *real dependency* or by *independent
histories that must be combined* — never by the fact that the branch moved.

---

## Non-destructive method

Never reset the shared branch to make room. Work beside it:

```bash
# 1. Learn what advanced (read-only)
git fetch origin "$BRANCH"
git log --oneline "$MY_BASE..origin/$BRANCH"
git diff --stat "$MY_BASE" "origin/$BRANCH"

# 2. Fresh worktree AT the new head (absolute path — see shell-hygiene)
git worktree add "$HUB/reapply-$STAMP" "origin/$BRANCH"

# 3. Reapply only your commits, oldest first, onto that head
git -C "$HUB/reapply-$STAMP" cherry-pick "$MY_BASE..$MY_TIP"
#    (or: git format-patch / git am for a path-scoped delta)

# 4. Re-verify in the fresh worktree, then publish against the SHA from step 1
#    (compare-and-set; a plain push would not catch a rewound branch — see below)
EXPECTED="$(git rev-parse "origin/$BRANCH")"
git -C "$HUB/reapply-$STAMP" push --force-with-lease="$BRANCH:$EXPECTED" origin HEAD:"$BRANCH"
```

If a cherry-pick conflicts, the other side *changed the same lines you did*:
resolve additively (orama-way — union both intents, never drop theirs), then
continue. That conflict is information about the concurrent change, not a
reason to abandon the linear approach.

Why a fresh worktree rather than rewinding the existing one: a hard reset or
branch-pointer move discards uncommitted and unpushed work and is blocked as a
destructive command by the autoresearch hook. The old checkout stays intact as
the recovery reference until the push lands. A hard reset is not banned
outright — it has qualified uses (orphan recovery, mirrors, ruled rewrites)
with an explicit gate: [`hard-reset-qualified-uses.md`](hard-reset-qualified-uses.md).
Catching up a shared PR branch is none of them.

---

## Compare-and-set the publication

The reapply is only safe if the head you re-read is still the head when you
push. A plain `git push` is not enough: it rejects only non-fast-forward
updates, so if the remote branch was rewound to an ancestor your reapplied tip
is still a descendant of it and the push would silently replace the moved head.
Compare against the SHA you fetched in step 1:

```bash
EXPECTED="$(git rev-parse "origin/$BRANCH")"   # captured at step 1, reused here
git push --force-with-lease="$BRANCH:$EXPECTED" origin HEAD:"$BRANCH"
```

The explicit `branch:sha` form is a compare-and-set, not a force: it succeeds
only when the remote is exactly `EXPECTED`, and your tip descends from it, so
the update is a fast-forward. When publishing through a connector API instead
of git, use that API's expected-head update and confirm the remote blob SHA
equals `git hash-object` of the local bytes. If the compare fails the head
moved again: loop to step 1, do not merge to "make it go through." See [`llm-provider-failure-modes.md`](llm-provider-failure-modes.md)
for the connector-specific truncation and chunking failures.

---

## When a merge commit IS right

| Situation | Why a merge is correct | Model |
| --- | --- | --- |
| Two independent histories that must both survive (dual-pedigree / fork integration) | Preserving original SHAs of **both** lines is the requirement; a replay would forge history | `lesson_d8ef5aaa6bf8` (periscope two-parent merge; with `lesson_566891328e34`, `lesson_c31d8c306b55`) |
| Real dependency: your PR needs content from another unmerged PR | The merge *is* the dependency edge | integrative-merge doctrine |
| Branch protection requires "up to date with base" and the operator has said to satisfy it | Policy, not preference | operator ruling |
| Landing a `CONFLICTING`/`DIRTY` PR on GitHub | Local merge of base, resolve additively, then squash | `lesson_001158f408c1` |

**Not** exceptions: "the branch is behind," "GitHub shows an update-branch
button," "CI will be happier." PR checks run on GitHub's synthetic merge ref
(`lesson_73bcc8484082`), so a catch-up merge in the branch adds no CI signal.

---

## Reconciling the lessons that appear to disagree

PT memory holds accepted lessons that read as opposites. They are not; they
answer different questions:

| Lesson | Question it answers | Relationship to this rule |
| --- | --- | --- |
| `lesson_f11f751d7446` — merge commits for normal integration; squash/rewrite only with human approval | *How do independent lines of work combine?* | Compatible: it is about combining, not about catching a branch up |
| `lesson_001158f408c1` — local merge of base then squash for `CONFLICTING` PRs at landing | *How do I land a conflicted PR?* | Compatible: a landing-time act, after review, by the merger |
| `lesson_66b917484d5e` — when told no merges, no merges | operator constraint | Overrides everything: reapply is the *only* option under it |
| `lesson_3060e4382900` — reapply onto new head, but via a hard reset | the destructive means | **Superseded in method** by the fresh-worktree procedure above (its intent stands); the hard reset itself survives only under [`hard-reset-qualified-uses.md`](hard-reset-qualified-uses.md) |

Proposed PT follow-up (not applied here — PT memory graduates through its own
`learn.py` pipeline): supersede the *method* of `lesson_3060e4382900` and
narrow `lesson_001158f408c1` to "at landing time."

---

## Provenance ledger — eight formulations, one rule

| # | PT lesson | Accepted (`accepted_at`, UTC date) | What it says | State |
| --- | --- | --- | --- | --- |
| 1 | `lesson_859e6589c55f` | 2026-06-22 | push rejected: recover with a fresh-from-main branch plus cherry-pick, never merge | accepted |
| 2 | `lesson_30de39cf9ada` | 2026-06-28 | rebase/cherry-pick post-merge orphan PRs onto current main before closing or merging | accepted |
| 3 | `lesson_5222ac71c9ef` | 2026-06-28 | draft-PR triage: compare two-dot at tip vs main, cherry-pick only net-new commits | accepted |
| 4 | `lesson_3060e4382900` | 2026-07-01 | diverged from origin with concurrent commits: hard-reset to origin tip, reapply only your own deltas | accepted — *method* superseded here |
| 5 | `lesson_4b650ec5b970` | 2026-07-17 | replaying fixes onto an existing PR branch: verify the live branch, reapply only the missing behavioural delta | accepted |
| 6 | `lesson_9a91e4244de6` | 2026-07-27 | sideline branches must be cherry-picked onto the active PR branch before push | accepted |
| 7 | `lesson_c4e8f12a9b3d` | 2026-07-28 | periscope PR #12: reset to fresh `origin/merged`, replay only the harmonized path delta | provisional |
| 8 | `lesson_24b4facd84d9` | 2026-10-13 (20:00 UTC = 2026-10-14 04:00 PHT) | PR head advanced: re-read it, reapply the verified delta, no catch-up merge or rebase | accepted — **PT PR #441 @ b63891c6, pending merge** |

Dates are the lessons' own `accepted_at`, shown as UTC dates; PHT (UTC+8) is
the operator's local zone and differs by a calendar day for any entry accepted
after 16:00 UTC.

**Audit time.** This ledger was checked against PT `lessons.jsonl` (ids,
status, `accepted_at`, claim text) at **2026-10-13 22:10 UTC / 2026-10-14
06:10 PHT**. Re-run that check before quoting a state; `provisional` and
`pending-merge` rows move.

Rows 4 and 7 reach the
right outcome by a hard reset; both are covered by the qualification gate in
[`hard-reset-qualified-uses.md`](hard-reset-qualified-uses.md), and the
fresh-worktree method above is preferred.

The count is the point. Each entry is a session that did the work, paid for
the lesson, and wrote it where only the next PT session would see it. A rule
that lives only in PT memory is re-learned; a rule that lives in the skill the
agent loads *before* acting is followed.

---

## See also

- [`post-review-micro-remediation.md`](post-review-micro-remediation.md) —
  Phase 2 branch discipline links here; Phase 3 treats rebase as a means, not
  a ritual.
- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md)
  — conflict-recovery playbook and concurrent-agent invariants.
- [`../skills/using-git-worktrees/SKILL.md`](../skills/using-git-worktrees/SKILL.md)
  — absolute-path worktree creation (the zsh relative-path trap).
- [`../skills/oramasys-method/references/integrative-merge.md`](../skills/oramasys-method/references/integrative-merge.md)
  — when a merge *is* the work.
- [`llm-provider-failure-modes.md`](llm-provider-failure-modes.md) — provider
  traps that interact with publishing a reapplied delta.
