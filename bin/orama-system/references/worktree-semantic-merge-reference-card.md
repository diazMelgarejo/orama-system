# Worktree-Based Semantic Merge Resolution — Reference Card

> **This is the default.** Use this card for the ordinary case: one branch,
> one agent, merging into `main`, with no other agent concurrently editing
> the same repo. That covers nearly all everyday merges. It is deliberately
> simple enough to follow literally, mechanically, without first reading
> anything else.
>
> **Escalate to
> [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md)'s
> Nested-Branch Merge Protocol instead** only when either is true:
>
> - **two or more agents are actively editing the same repo at the same
>   time** (concurrent branches, topological merge ordering, the
>   10-minute-buffer-between-merges discipline — none of that applies to a
>   single branch merging alone), or
> - **the merge itself is the advanced case**: reconciling a long-diverged
>   fork or upstream source (months of separation, large structural drift)
>   rather than an ordinary feature branch a few days or weeks old.
>
> If neither applies — and for most merges neither does — this card is the
> whole procedure. Don't read the other one first "just in case"; that's
> exactly the wrong-sized tool for the common case, and the reason this card
> exists at all.

## Purpose

Merging a branch into `main` is not "run `git merge`, resolve however git's
markers suggest, commit." Two independent, legitimate edits to the same
region happen even on ordinary branches, and the wrong failure mode is
silent data loss dressed up as a successful merge — picking one side,
discarding the other, and reporting "merged cleanly." This card is the
mechanical procedure for telling apart conflicts a script can resolve
safely from conflicts that need a human's judgment, and for never guessing
on the latter.

## The procedure, step by step

### 1. Create a fresh worktree from the actual remote tip, not local `main`

```bash
git fetch origin main <branch> --quiet
git worktree add /tmp/<repo>-worktree-main origin/main --detach
cd /tmp/<repo>-worktree-main
git checkout -b <branch>-merge-check --quiet
```

A stale local `main` produces a merge based on state that's already
wrong — fetch first, every time, no exceptions.

### 2. Dry-run the merge before committing to anything

```bash
git merge origin/<branch> --no-commit --no-ff
```

This either succeeds cleanly (no conflicts — skip to step 6) or leaves real
conflict markers in the working tree without having committed anything.
Either way, nothing is lost yet, and nothing has been decided yet.

### 3. Enumerate every conflicted file and region before touching any of them

```bash
git status --short | grep '^UU\|^AA\|^DD'
grep -rn '^<<<<<<<\|^=======$\|^>>>>>>>' <each conflicted file>
```

Know the full scope before resolving anything. Resolving file 1 while
file 2 is still unexamined risks a resolution style that doesn't generalize
once file 2's actual shape is known.

### 4. Classify each conflict region — this is the core of the procedure

For each conflicted region, read the actual diff (not a summary of it) and
classify:

| Class | Shape | Resolution |
| --- | --- | --- |
| **Trivial** | Both sides made the exact same edit | Auto-resolve; either side's text is correct |
| **Additive** | Both sides added *different, non-overlapping* content to the same structural location (new rows in a table, new list items, new sections) | Keep everything from both sides — never drop one side's real, distinct contribution to keep the merge "simple" |
| **Overlapping-additive** | Both sides edited the *same specific line/cell/entry* with *different, non-contradictory* detail (e.g. one side added scope A, the other added scope B, to the same row's description) | Merge the text of both edits into one — do not pick a side, synthesize |
| **Semantic** | Both sides made *mutually exclusive* edits to the same specific content (contradictory values, incompatible design decisions, one side removing what the other relies on) | **Stop. Do not resolve. Ask the human**, per step 5 |

Additive and overlapping-additive are the common case for doctrine/reference
docs (multiple independent sessions adding rows to the same routing table,
as in the worked example below) and are safe to resolve without asking —
*but still show the resolution to the human before pushing if the file is a
canonical doctrine/policy file*, not because the classification is
uncertain, but because policy files warrant a lighter-weight confirmation
regardless.

Semantic conflicts are never resolved by guessing which side is "more
correct," picking the side that seems more recent, or preferring
`HEAD`/`origin` by convention. There is no default. Ask.

**If, while working through this, the conflict surface turns out to be much
larger or more structurally tangled than a single branch's worth of
changes usually is — reconsider whether this is actually the advanced case
this card explicitly excludes, and escalate to the Nested-Branch Merge
Protocol instead of forcing this simpler procedure to fit.**

### 5. For semantic conflicts: ask with the real content, not a description of it

Use the clarification tool with:

- the **actual conflicting text** from both sides (not "there's a conflict
  in the config" — quote it),
- **what each side is trying to accomplish**, inferred from context, not
  assumed,
- a **concrete proposed resolution** as one of the offered options, so the
  human can confirm a specific plan rather than design one from scratch,
- and an explicit "something else" escape hatch, since your proposed
  resolution might be wrong in a way you can't see from inside the
  conflict.

Never proceed past a semantic conflict without an explicit answer. Never
re-interpret silence, a tangential reply, or a vague "sure" as a decision.

### 6. Resolve, re-verify, then complete the merge for real

```bash
# after resolving every marker:
grep -rn '^<<<<<<<\|^=======$\|^>>>>>>>' <every file that had conflicts>
# must be empty before proceeding

git add <resolved files>
python3 scripts/review/repo_hygiene.py .          # or repo's equivalent
markdownlint-cli2 <any touched .md files>          # or repo's equivalent
<run the repo's real test suite for anything touched>
git commit --no-edit   # or an explicit message describing the resolution
git log -1 --format="%H %P"   # confirm 2 real parents, not 1
```

A merge commit with only one parent (the classic mistake: a stash/reset
cycle silently converted what should have been a real merge into a plain
commit) is not a merge — verify parent count explicitly, don't assume the
commit you just made is what you intended.

### 7. Push once, clean up the worktree properly

```bash
git push origin HEAD:<branch>
git worktree remove /tmp/<repo>-worktree-main --force   # never rm -rf
```

`rm -rf`ing a worktree directory leaves a dangling entry in
`git worktree list` — always use `git worktree remove`.

## Worked example (this card's origin)

`post-review-micro-remediation.md`'s enforcement table had a real conflict:
main independently gained two new routing rows (`cursor-pr-body`,
`ecc-sync`) while a doctrine-extension branch was in progress, and both
sides had separately edited the *same* `hermes-harness` row — main added
Phase 0/Phase 2 framing text, the branch added a Phase 6 detail neither
side knew the other was writing.

This was the ordinary case this card is scoped for: one branch, one agent,
merging into `main`, no concurrent multi-agent editing, no long-diverged
fork to reconcile. Classified as **additive** (the two new rows) plus
**overlapping-additive** (the `hermes-harness` row — same row, different
non-contradictory detail). Confirmed the classification and proposed
resolution with the human before executing (showing the actual conflicting
diff, not a description) per this card's own step 5 discipline, even
though the classification itself was unambiguous — because the file is
exactly the kind of canonical doctrine document that warrants that
confirmation regardless. Resolved by keeping every row from both sides and
merging the `hermes-harness` row's two descriptions into one text.

## Why this card exists as its own thing, not folded into the mature protocol

The Nested-Branch Merge Protocol was built for a specific, infrequent, hard
problem: reconciling something like a soft fork with months of upstream
drift, or genuinely concurrent multi-agent edits to the same repo, where
topological merge ordering and a formal multi-strategy table earn their
complexity. Pointing an agent doing an ordinary same-day branch merge at
that protocol as the *first* thing to read is the wrong-sized tool for the
job — it's more process than the situation calls for, and the risk isn't
just wasted tokens, it's an agent skimming a heavyweight doc it doesn't
fully need and missing the one or two things that actually matter for its
much simpler case. This card is deliberately the smaller, literal,
default path; the mature protocol remains exactly as heavyweight as its
own harder problem requires, unchanged, for when that problem is the one
actually in front of an agent.

## Related

- [`post-review-micro-remediation.md`](post-review-micro-remediation.md)
  Phase 6 — the cross-repo synchronization doctrine this card's dry-run/ask
  discipline generalizes from.
- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md)
  § Nested-Branch Merge Protocol — the advanced-case sibling to this card;
  see the escalation criteria at the top of this document.
- [`../skills/using-git-worktrees/SKILL.md`](../skills/using-git-worktrees/SKILL.md)
  — the general worktree lifecycle (bootstrap, hygiene gate, cleanup) this
  card assumes as a prerequisite; this card covers the merge-resolution step
  specifically, not worktree mechanics broadly.
- [[fable5-git-rebase-safety]] — verifying a branch's real relationship to
  `main` (ahead/behind counts alone are not the same as knowing what's
  actually different) before deciding a merge is even the right move.
