# Expunge Contaminated History

A naive scrub leaves the bad string discoverable in reflog, packed objects, and
stale remote-tracking refs. Use this only when prevention failed and the
contaminated object already landed.

## When to invoke

Invoke when:

- A forbidden identity, secret, token, or workstation path landed in commit
  messages, authored-by lines, or file contents.
- A coordinated force-push window is acceptable.
- All collaborators can be notified to re-clone within about 24 hours.

Do not invoke when:

- A shared long-lived branch has many collaborators or release consumers.
- Rotation plus a forward fix is sufficient.
- You cannot coordinate a force-push window.

Warning: rewriting history does not un-leak a secret. Rotate any secret that ever
touched a public remote.

## Pre-flight

0. On Windows, run the runtime bootstrap in
   `../using-git-worktrees/SKILL.md#windows-powershell-runtime-bootstrap`.

1. **Disable hooks for the surgery window** (mandatory — restore after publish):

   ```bash
   export HISTORY_SURGERY_ACTIVE=1
   # All rewrite/push git commands in this session use hooks off, e.g.:
   git -c core.hooksPath=/dev/null ...
   # or: bash scripts/git/history-surgery-git.sh ...
   ```

   Hooks prevent bad *new* commits; during an active rewrite they false-block,
   stall multi-branch force-push, and make expunge look hung. Re-enable immediately
   after the last force-push + verification:

   ```bash
   unset HISTORY_SURGERY_ACTIVE
   bash scripts/git/install-local-hooks.sh
   ```

   See [`history-surgery-hooks-safeguard-reference-card.md`](history-surgery-hooks-safeguard-reference-card.md).

2. Disable live Cursor co-author injection before writing new commits:

   ```bash
   bash scripts/git/apply-attribution-guard-all-repos.sh
   # or hook-free commits:
   bash scripts/git/commit-clean.sh -m "type(scope): summary"
   ```

3. Identify every contaminated commit and SHA:

   ```bash
   git log --all --format="%H %s%n%b" | grep -i "<token>"
   git log --all --format="%H %an <%ae>" | grep -i "<token>"
   git rev-list --all --objects | git cat-file --batch-check --batch-all-objects \
     | awk '$2=="blob"{print $1}' \
     | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -q "<token>" && echo {}'
   ```

   If the real patterns are private identity literals or secrets, do not paste
   them into shell history. Read them from a local-only ignored pattern file and
   print only labels/counts in reports.

4. Choose a strategy:

   | Scenario | Strategy |
   |---|---|
   | Short contiguous range, about 10 commits or fewer | Anchor + cherry-pick |
   | Many commits, scattered, or all-history scrub | `git filter-repo` |
   | Secret in a single blob, message clean | `git filter-repo --replace-text` |
   | Final PR tree is correct, but intermediate PR commits contain contaminated blobs or conflict noise | Clean replacement PR from current `origin/main` |

5. Ensure no in-flight work and tag the pre-scrub tip:

   ```bash
   git fetch --all --prune
   git tag pre-expunge-backup-$(date +%Y%m%d-%H%M%S) <current-tip-sha>
   ```

## Scrub sequence

Use placeholders throughout. Never paste the real forbidden string into PR
titles, bodies, commit messages, or shell history.

01. Re-confirm contaminated commits:

    ```bash
    git log --all --format="%H %s%n%b" | grep -i "<token>"
    ```

02. Create a clean branch and replay safe commits:

    ```bash
    git checkout -b <clean-branch> <last-known-good-sha>
    git cherry-pick <good-sha-1> <good-sha-2>
    # Or, for broad scrubs:
    # git filter-repo --message-callback 'return message.replace(b"<token>", b"")'
    ```

03. Push with a lease (hooks still off for the surgery window):

    ```bash
    git -c core.hooksPath=/dev/null push --force-with-lease origin <clean-branch>
    ```

04. Open the PR with sanitized language only.

05. After merge, move `main` to the clean tip:

    ```bash
    git checkout main
    git reset --hard <merged-clean-tip-sha>
    git -c core.hooksPath=/dev/null push --force-with-lease origin main
    ```

06. Delete contaminated remote branches:

    ```bash
    gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>
    ```

07. Prune local remote-tracking refs:

    ```bash
    git remote prune origin
    ```

08. Delete local refs still pointing at contaminated objects:

    ```bash
    git for-each-ref --format='%(refname) %(objectname)' | grep "<bad-sha>"
    git update-ref -d <ref>
    ```

09. Expire all reflogs:

    ```bash
    git reflog expire --expire=now --all
    ```

10. Remove unreachable objects:

    ```bash
    git repack -Ad --unpack-unreachable=now
    git prune --expire=now
    ```

11. Verify commit messages:

    ```bash
    git log --all --format="%B" | grep -i "<token>"
    ```

12. Verify blobs:

    ```bash
    git rev-list --all --objects \
      | git cat-file --batch-check --batch-all-objects \
      | awk '$2=="blob"{print $1}' \
      | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -l "<token>"'
    ```

    Prefer a local-only pattern-file scanner for real incidents. It should:

    - load forbidden literals from ignored local config;
    - scan reachable blobs from `git rev-list --objects --all`;
    - report only labels, object ids, paths, and counts;
    - never print matched literal values or matched lines;
    - distinguish current-tree clean from all-ref blob clean.

    Don't invent a new pattern-file format per incident. Reuse the abstraction
    PT already ships for current-tree scanning
    (`scripts/review/repo_hygiene.py`'s `private_literal_values(root, key)`,
    backed by a git-ignored `.verboten-literals.local` at the OpenClaw workspace
    root — `key=value` lines, `#` comments, resolvable via `OPENCLAW_VERBOTEN_LITERALS`
    env override). The all-ref scanner below is that same loader pointed at
    every reachable blob instead of the working tree:

    ```python
    #!/usr/bin/env python3
    """All-ref blob scan for forbidden literals. Prints labels/counts/paths only
    -- never a matched literal or matched line. Run from the repo root.

    Scope matters: scan HEAD, origin/main, and the PR-unique range
    (origin/main..HEAD) separately. Inherited origin/main hits are pre-existing
    repository-wide debt, not evidence the PR-scoped scrub failed -- but do not
    round PR-unique hits down to zero without checking them explicitly.
    """
    import subprocess
    import sys
    from collections import Counter
    from pathlib import Path

    # Path.cwd(), not __file__ -- this snippet is meant to be saved and run
    # standalone from the repo root (see the __main__ block below, which
    # already assumes root = Path.cwd()); __file__-relative pathing breaks
    # once it's copied out of this exact reference card's own location.
    sys.path.insert(0, str(Path.cwd() / "scripts" / "review"))
    from repo_hygiene import private_literal_values, openclaw_workspace_root  # noqa: E402

    KEYS = ("owner_gmail", "owner_name", "forbidden_attribution")


    def load_tokens(root: Path) -> list[str]:
        return [
            tok.casefold()
            for key in KEYS
            for tok in private_literal_values(root, key)
        ]


    def scan_refs(root: Path, *revs: str) -> Counter:
        """revs: any git revision args, e.g. ('HEAD',) or ('origin/main..HEAD',)."""
        tokens = load_tokens(root)
        if not tokens:
            print("no local pattern file found -- nothing to scan", file=sys.stderr)
            return Counter()
        objects = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--objects", *revs],
            check=True, text=True, capture_output=True,
        ).stdout.splitlines()
        hits: Counter = Counter()
        for line in objects:
            parts = line.split(maxsplit=1)
            if not parts:
                continue
            oid = parts[0]
            kind = subprocess.run(
                ["git", "-C", str(root), "cat-file", "-t", oid],
                check=False, text=True, capture_output=True,
            ).stdout.strip()
            if kind != "blob":
                continue
            blob = subprocess.run(
                ["git", "-C", str(root), "cat-file", "-p", oid],
                check=False, text=True, capture_output=True, errors="replace",
            ).stdout
            blob_lc = blob.casefold()
            for tok in tokens:
                if tok in blob_lc:
                    hits[oid[:12]] += 1
        return hits


    if __name__ == "__main__":
        root = Path.cwd()
        for label, revs in (
            ("HEAD", ("HEAD",)),
            ("origin/main", ("origin/main",)),
            ("origin/main..HEAD (PR-unique)", ("origin/main..HEAD",)),
        ):
            hits = scan_refs(root, *revs)
            print(f"{label}: {sum(hits.values())} hits across {len(hits)} blobs")
    ```

    Output looks like `HEAD: 219 hits across 187 blobs` -- a count and a scope,
    never a literal or a matched line. Treat a nonzero PR-unique count as a real
    blocker; treat a nonzero `origin/main`-only count as tracked, separate,
    repository-wide debt (see "Do not confuse re-anchor with scrub completion" in
    `reanchor-after-rewrite.md`).

    If this scan times out or returns hits, the operation is not history-wide
    complete. Record the gap and either continue the scrub or explicitly defer it.

13. Verify reflog is drained:

    ```bash
    git reflog --all | wc -l
    ```

14. Notify collaborators: force-push complete, fresh clone required, do not
     `git pull`.

15. Confirm secret rotation, if applicable.

16. **Re-enable hooks** (if not already done):

    ```bash
    unset HISTORY_SURGERY_ACTIVE
    bash scripts/git/install-local-hooks.sh
    git config --local --get core.hooksPath   # must print: .githooks
    ```

17. **Publish and reanchor on GitHub** (mandatory when scrub touched all refs):

   ```bash
   ALLOW_MAIN_PUSH=1 bash scripts/git/post-rewrite-finish.sh .
   ```

   See [`post-rewrite-automation-reference-card.md`](post-rewrite-automation-reference-card.md).

## Clean Replacement PR

Use this when a PR branch has the right final content but the branch's
intervening commits are the problem: contaminated historical blobs, repeated
failed replay commits, synthetic conflict commits, or a review surface so noisy
that preserving the ancestry increases risk.

This is not a normal squash for convenience. It is a containment maneuver. Keep
the old branch/PR reachable as evidence until the replacement is verified, but
do not make reviewers or future agents reason through poisoned intermediate
history.

Procedure:

1. Fetch and record immutable anchors:

   ```bash
   git fetch origin --prune
   git rev-parse origin/main
   git ls-remote origin refs/heads/<old-pr-branch>
   git tag safety/<old-pr-branch>-before-clean-replacement-$(date +%Y%m%d) <old-tip>
   ```

2. Save a pristine content snapshot of the old PR before touching it:

   ```bash
   git diff --binary origin/main...origin/<old-pr-branch> > /tmp/<old-pr>.patch
   git diff --stat origin/main...origin/<old-pr-branch> > /tmp/<old-pr>.stat
   git diff --name-status origin/main...origin/<old-pr-branch> > /tmp/<old-pr>.name-status
   ```

3. Create a fresh branch from current `origin/main`:

   ```bash
   git worktree add -b <replacement-branch> /tmp/<replacement-worktree> origin/main
   cd /tmp/<replacement-worktree>
   ```

4. Replay the final reviewed tree, not the contaminated commits:

   ```bash
   git checkout safety/<old-pr-branch>-before-clean-replacement-YYYYMMDD -- .
   ```

5. Scrub the current tree using local-only pattern files. Report labels/counts,
   never literal values or matching lines.

6. Commit once, with a sanitized message explaining that this is a clean content
   replay after branch-scope expungement.

7. Prove equivalence and scope:

   ```bash
   git diff --quiet safety/<old-pr-branch>-before-clean-replacement-YYYYMMDD HEAD
   git diff --stat origin/main...HEAD
   git diff --name-status origin/main...HEAD
   ```

   The first command must be clean when the goal is to preserve the final tree.
   Any delta against the saved old PR snapshot must be explained, usually as
   intentional local memory or documentation added after the old remote snapshot.

8. Run hygiene, targeted tests, and a PR-unique blob scan:

   ```bash
   python3 scripts/review/repo_hygiene.py .
   python3 -m pytest -q <targeted-tests>
   # local-only scanner: compare origin/main, HEAD, and origin/main..HEAD
   ```

   The required proof is `origin/main..HEAD` has zero hits for the configured
   forbidden labels. Hits already inherited from `origin/main` are separate
   repository-wide cleanup, not a blocker for the replacement PR unless the user
   explicitly expands scope.

9. Push the replacement branch, open a new PR, and close the old PR with a short
   sanitized audit note that points reviewers to the replacement. Do not force
   update the old branch unless the user explicitly chooses that path.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Forgot to disable hooks during rewrite | Pre-push stalls or blocks every branch; `main` rejected under Phase 0 | `git -c core.hooksPath=/dev/null` for surgery window; restore hooks after |
| Forgot `git reflog expire --expire=now --all` | Reachable commits are clean but `git log -g` still shows bad SHAs | Expire reflogs, then prune |
| Forgot `git remote prune origin` | `git branch -ra` still lists contaminated refs | Prune remotes, then delete local refs |
| Used `git pull` after rewrite | Bad objects resurrect locally | Fresh clone |
| Skipped secret rotation | Secret remains valid outside git | Rotate immediately |
| Kept the old PR branch after deciding on replacement | Review still sees contaminated or noisy ancestry | Close the old PR and open a clean replacement after saving anchors |
