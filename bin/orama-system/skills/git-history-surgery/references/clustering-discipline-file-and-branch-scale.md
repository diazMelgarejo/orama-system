# Clustering Discipline — the Same Pattern at File Scale and Branch Scale

> **Origin:** 2026-08-09, orama PR #298 + PT PR #343 CodeRabbit remediation
> arc. A user-articulated observation — "concentric circles of nested
> batching" — connecting how individual file edits get clustered into
> commits with how individual branches get clustered by conflict pattern
> during a reanchor. Same discipline, five zoom levels, one principle.

## The five levels

1. **File scale.** One coherent, reviewable diff per file — the unit CIDF's
   `decide()` operates on ([`../../../cidf/SKILL.md`](../../../cidf/SKILL.md)).
2. **Commit scale.** Group fixes into commits by *theme*, not by the order
   you happened to touch files. Nine CodeRabbit findings across seven files
   became five themed commits (worktree-cleanup, push-error-visibility,
   object-scanner-streaming, quoting/Bash-3.2-hardening, docs) — not one
   giant commit, not nine one-liners.
3. **Push scale.** Batch all logical commits locally, push once. Fewer CI
   triggers, fewer pre-push hook runs, no half-finished intermediate state
   visible on the remote between commits.
4. **PR/branch scale.** Stay on the one open PR/branch for a given thread of
   work rather than fragmenting across new ones. A second, third, and fourth
   CodeRabbit review all landed on the *same* `fix/mapfile-to-while-read`
   PR (#298) rather than each spawning its own branch — reuse the
   most-recently-active open PR; only open a new one if none exists yet.
5. **Repo scale (forward-looking, not yet executed).** Does a function or
   role earn its own top-level repo, or does it stay a `docs/v2/` subsection
   of a shared repo? Same "does this deserve its own container" judgment,
   at the largest radius. Relevant to the v2 `oramasys/*` split; deliberately
   deferred here, not answered.

## The same discipline, applied to branches instead of files

Reanchoring a batch of stale branches onto a rewritten `origin/main` is the
identical clustering problem one level up:

- **Group branches by conflict pattern**, not by branch name or discovery
  order. During the 2026-08-09 PT reanchor operation, 9 stuck branches split
  cleanly into two conflict clusters by the files/commits actually
  colliding (`resolve_orama_root.sh`/`cloud-bootstrap.sh` cluster vs.
  `alphaclaw-session`/`self-improve`/`codex-coder.md` cluster) — the same
  "cluster by theme, not by touch-order" move as grouping file fixes into
  commits.
- **A conflict resolution is the branch-scale analog of a file edit.**
  Resolving a `SKILL.md` add/add conflict by verifying which side's content
  is actually current (not by picking a side reflexively) is doing, at
  branch scale, exactly what CIDF's `decide()` does at file scale: don't
  apply the first plausible answer, verify against the actual current
  state before committing to a resolution.
- **A cherry-pick that resolves to empty is a valid, common, CORRECT
  outcome** — not a failed reconciliation — for a branch whose commits have
  all been independently superseded on `origin/main` since it diverged.
  Confirmed across 4 branches / 19 commits in the same 2026-08-09 operation,
  all verified via patch-id comparison rather than assumed. See
  [`reanchor-after-rewrite.md`](reanchor-after-rewrite.md) for the tree-twin
  theory this rests on.
- **One conflict-resolution decision should generalize across every branch
  sharing the same conflict tail**, the same way one commit theme covers
  every file touched by that theme — codex, dispatched against 5 branches
  sharing an identical 5-commit conflict cluster, resolved the shared
  portion consistently across all 5 rather than re-deriving the answer per
  branch, then handled each branch's additional unique commits on top. This
  only holds after verifying each branch has the same base, conflict blobs,
  surrounding context, and gitlink direction; if any of those checks differ,
  resolve that branch independently instead of assuming the cluster match is
  sufficient.

## Gold-nugget cross-references (quote these, don't re-derive them)

- **Reconciliation belongs to what's verified, not to which side looks more
  current.** The heuristic ("main is probably ahead," "the newer version
  number wins") and the verified answer usually agree — which is exactly
  why skipping verification feels safe. The one case in the 2026-08-09 arc
  where they would have diverged (a submodule gitlink pointer whose branch
  pin was actually *older* than main's current pin, not newer) would have
  silently regressed without the check. This is the single thread tying
  file-scale CIDF discipline, branch-scale reanchor discipline, and
  cross-repo guard-sync discipline together — verify before reconciling, at
  every scale, every time, even when confident.
- **A security redaction must survive reconciliation regardless of which
  side looks newer by any other measure.** A stale branch's real LAN IP vs.
  `origin/main`'s already-redacted placeholder resolves to the redacted
  side, full stop — recency is not the deciding signal once a redaction is
  in play.
- **Multi-agent dispatch should cluster by difficulty against demonstrated
  reliability, not just by count.** Split a batch of independent units
  (branches, findings, files) so a track-record-proven agent gets the
  harder/larger cluster and a less-proven one gets a smaller, well-bounded
  cluster — recalibrate mid-session on evidence (a 4/4 failure rate is a
  signal to stop retrying, not bad luck), not on a fixed a-priori split.

## Related

- [`../SKILL.md`](../SKILL.md) — parent skill; Non-Negotiables, Decision Flow
- [`reanchor-after-rewrite.md`](reanchor-after-rewrite.md) — tree-twin theory
- [`post-rewrite-automation-reference-card.md`](post-rewrite-automation-reference-card.md)
  — the branch-scale tooling this discipline governs
- [`../../../cidf/SKILL.md`](../../../cidf/SKILL.md) — the file-scale discipline this mirrors
- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md)
  — dispatch protocol this reference's difficulty-clustering nugget extends
