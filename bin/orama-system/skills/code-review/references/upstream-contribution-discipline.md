# Upstream Contribution Discipline

When a fix found during review or a blend pass is portable to a vendored
upstream repo (not just the fork/downstream copy), these practices — proven
across a real multi-PR contribution arc (agentic-stack PRs #60–#65) — turn
"I found a bug" into a fix a maintainer can actually merge:

1. **Check the project's own stated design intent before flagging a
   behavior as a bug.** A downstream fork's version of a function may
   differ from upstream by *deliberate* design choice, not by mistake —
   e.g. one file's fail-open error handling vs. another's fail-closed
   hardening can both be correct for their own contexts. Read the target
   function's docstring and any linked spec/design doc for the *upstream*
   repo specifically before porting a downstream "fix" — a fix that's
   right for your fork can be wrong for upstream's own documented contract.
   Caught live during the #65 contribution: a test rewrite that was
   correct for a downstream fail-closed variant would have asserted the
   *opposite* of upstream's own explicitly documented fail-open design.
2. **Verify every fix in both directions before opening the PR.** Stash
   (or worktree-diff) just the fix, confirm the new/extended test *fails*
   against the pre-fix code with the expected error, then restore the fix
   and confirm it passes. A test that only ever ran against the fixed code
   proves the test runs, not that it catches the bug.
3. **One fresh worktree per upstream branch, not stash gymnastics on a
   shared scratch checkout.** `git worktree add -b <branch> <path>
   upstream/<default-branch>` gives a clean, isolated checkout per
   contribution; if a branch's history needs correcting before it's ever
   pushed, delete the ref (`git update-ref -d refs/heads/<branch>` — plain
   `git branch -D` is blocked by this stack's dangerous-command hook) and
   redo it in a fresh worktree rather than accumulating stash-based fixups.
   See [`../../using-git-worktrees/SKILL.md`](../../using-git-worktrees/SKILL.md).
4. **Ground the PR body in the project's own design docs, not just "this
   looks wrong."** Quote the upstream repo's own spec/README/docstring
   language that the bug violates — a security- or design-intent framing
   grounded in the maintainer's own stated goals is far more persuasive
   and reviewable than an unsupported claim of severity.
5. **Cross-reference sibling PRs with one trailing comment each**, not a
   body edit — check first that no prior mention exists, then link every
   PR in the same contribution batch to every other one, mentioning the
   maintainer once if not already tagged. See
   [`../../git-history-surgery/SKILL.md`](../../git-history-surgery/SKILL.md) for
   the broader multi-agent / multi-branch merge discipline this composes
   with, and [`../../cursor-agent/SKILL.md` § Fan-out Safety](../../cursor-agent/SKILL.md)
   for verifying a dispatched fan-out agent's self-reported "done" against
   the actual diff before trusting it — the same verify-before-trust
   principle applies whether the claim comes from a subagent or from your
   own pre-verification assumption about a fork's design.

Full narrative + the 7 generalized lessons this arc produced: Perpetua-Tools
`.agent/memory/working/2026-08-07-vendor-blend-and-upstream-contribution-retrospective.md`
and `.agent/skills/perpetua-memory/SKILL.md` § Resolving a live merge conflict
(the PT-side, memory-file-specific companion to this doc).
