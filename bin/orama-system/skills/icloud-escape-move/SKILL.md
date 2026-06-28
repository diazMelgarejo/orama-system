---
name: icloud-escape-move
description: >
  Canonical, fail-closed procedure for relocating a git working tree — or a whole
  tree of repos and worktrees — OUT of an iCloud-synced location to a plain local
  path on macOS, without losing data or breaking worktrees. Invoke when: "move
  repos out of iCloud", "escape iCloud eviction", "relocate git tree from Documents
  to code/", "iCloud is making ' 2' duplicate / conflict copies", "files got
  evicted / dataless", "iCloud sync is breaking git", "mv the tree and repair the
  worktrees", "leave a compatibility symlink after a repo move", or "repos keep
  re-duplicating in ~/Documents".
---

# iCloud-Escape Move

iCloud "Desktop & Documents" stores `~/Documents` inside the CloudDocs container,
where it is actively hostile to git working trees: it spawns `* 2.*` / `* 3.*`
conflict copies, evicts file **content** under "Optimize Mac Storage" (leaving
dataless stubs that `du` reports as ~0 bytes), and refuses atomic renames out of
the container. The fix is structural — move the tree to a plain local path
(`~/code/…`) once, then leave a compatibility symlink behind. This same move was
already applied to the OpenClaw tree; this skill canonicalizes it. See
[[openclaw-skills]] for the precedent and [[git-history-surgery]] for repairing
refs if a move ever leaves a repo looking orphaned.

The worked example throughout is `~/Documents/oramasys` → `~/code/oramasys`
(`SRC=~/Documents/oramasys`, `DST=~/code/oramasys`).

## When to use this skill

Use it when a git repo (or a directory of repos/worktrees/venvs) lives under an
iCloud-managed path (`~/Documents`, `~/Desktop`, or any CloudDocs subtree) and
you want it on a plain local path. Do **not** use it for a normal in-volume repo
move with no sync layer — a plain `git`-aware `mv` is enough there. The
distinguishing signals are: recurring `* 2.*` conflict copies, dataless/evicted
files, or `du` size that is far smaller than the real on-disk size.

## Preconditions (hard asserts — any failure ABORTS before step 1)

- **`DST` must not exist at all.** A partial `DST` from a prior failed run means
  a later copy could merge/overwrite into a split state. `[ -e "$DST" ] && abort`.
- **Every repo and every worktree is clean and on a real branch.**
  `git -C <repo> status --porcelain` is empty, HEAD is not detached, and the
  branch is not `[gone]`/unmerged. Uncommitted work can be silently orphaned by
  a move + `worktree repair`.
- **No venv holds un-tracked work.** Before dropping a `.venv`, confirm it
  contains nothing but regenerable artifacts (`pip freeze` is recoverable; a
  stray script edited only inside `.venv/` is not).
- **All content is materialized — `du` is not trusted.** Dataless iCloud files
  read as 0 bytes, so `du` under-reports (e.g. 32M reported vs 289M real). Force
  download and verify true size before moving:
  `brctl download "$SRC"` then size via
  `find "$SRC" -type f -exec stat -f %z {} + | awk '{s+=$1} END{print s}'`
  (not `du`). Confirm zero dataless stubs.
- **A restore path exists** (Time Machine snapshot or equivalent) for the tree.

## Procedure

```bash
SRC="$HOME/Documents/oramasys"      # iCloud-managed source
DST="$HOME/code/oramasys"           # plain local destination
```

**0 — Audit.**
- Same volume? `df "$SRC"` vs `df "$(dirname "$DST")"` — equal `Filesystem`
  means an in-volume copy; different means a cross-volume copy (see step 2b).
- Enumerate what moves: real repos (`find "$SRC" -name .git -type d`), **worktrees**
  (`find "$SRC" -name .git -type f` — each is a gitdir pointer), and venvs
  (`find "$SRC" -type d -name .venv`).
- Collision guard + materialization + clean-state checks from Preconditions.

**1 — Drop regenerable venvs.** Virtualenvs hardcode absolute paths in
`bin/activate`, `pyvenv.cfg`, and console-script shebangs, so they break on move.
Remove and recreate after:
```bash
find "$SRC"/*/.venv -depth -delete 2>/dev/null
```

**2a — Move (same volume / out of CloudDocs).** `mv` is correct, but note: even
on the same APFS volume macOS **cannot atomically rename out of the CloudDocs
container**, so `mv` silently falls back to copy-then-delete with per-file iCloud
coordination — slow, and it materializes any remaining evicted content (desired).
```bash
mv "$SRC" "$DST"
```

**2b — Move (cross-volume, OR to preserve all metadata).** A cross-volume `mv`
copies via `cp`, which strips xattrs, ACLs, and the quarantine flag. Prefer a
metadata-preserving copy, verify parity, then remove the source:
```bash
ditto "$SRC" "$DST"                       # preserves xattrs/ACLs/resource forks
# or: rsync -aHAX --remove-source-files "$SRC"/ "$DST"/
diff -qr "$SRC" "$DST"                     # MUST be empty before removing source
```
Strip Gatekeeper quarantine afterward if scripts/binaries moved:
`xattr -r -d com.apple.quarantine "$DST" 2>/dev/null || true`.

**3 — Repair worktrees.** For every moved worktree, fix the parent repository's
stored gitdir back-pointer (the parent may live OUTSIDE this tree):
```bash
git -C "$DST/worktrees/<name>" worktree repair
```
Nested worktrees are not fixed recursively — run `worktree repair` for each, then
confirm with `git -C <repo> worktree list --porcelain`.

**4 — Compatibility symlink at the old path.** Keeps every stale reference
resolving during the transition. iCloud stores the symlink itself and does not
re-upload the now-external target (mirrors the OpenClaw precedent):
```bash
ln -s "$DST" "$SRC"
```
Validate the direction: the OLD path must point to the NEW path
(`readlink "$SRC"` == `$DST`), never the reverse, and `$SRC` must not already be
a symlink pointing back into CloudDocs.

**5 — Verify.** Each repo resolves and is clean; each worktree status resolves:
```bash
for r in <repo dirs and worktrees>; do
  git -C "$DST/$r" status -sb | head -1
done
```

**6 — Follow-up.**
- Recreate venvs deterministically (from a committed `requirements.txt` /
  lockfile, not a fresh resolve).
- Update tracked path references to the new path using **portable forms**
  (`~`, `$VAR`, relative) — never a literal `/Users/<name>/…` (doxing; LINT-006).
- Re-pin any `gbrain` sources registered with `--path` to the old location;
  rebuild the `code-review-graph` cache if it stored absolute paths.
- Audit submodules: `git submodule absorbgitdirs` before moving, then
  `git submodule sync` after, and check `.git/modules/*/config` for stale
  absolute paths.

## Non-negotiables

- **Never delete the source before parity is proven.** On a cross-volume copy,
  `diff -qr "$SRC" "$DST"` (or a byte-sum check) must pass before any `rm`.
- **Never trust `du` for iCloud size** — materialize first, then `stat`-sum.
- **Never leave a worktree unrepaired** — an unrepaired back-pointer makes the
  worktree silently unresolvable.
- **Never write a workstation path into a tracked file** — `~`/`$VAR`/relative
  only (enforced by `scripts/review/repo_hygiene.py` and the write-time
  `no-workstation-paths.py` PreToolUse hook; see [[cidf]] LINT-006).
- **Quiesce the tree first** — no editor, pytest, or `gbrain autopilot` holding
  files open in `$SRC` during the move (`lsof +D "$SRC"`); an open descriptor
  can leave a split-brain state.

## Failure modes and guards

| Failure | Guard |
| --------- | ------- |
| `mv` (copy-fallback) SIGKILLed mid-copy → split `SRC`/`DST` | Use copy → verify → remove; require `DST` absent first |
| `du` under-reports → `DST` runs out of space mid-move | Size via `stat -f %z`-sum after `brctl download`, not `du` |
| Worktree had uncommitted work → orphaned after repair | `git status --porcelain` clean in every repo AND worktree first |
| `.venv` deleted with un-tracked edits inside | Confirm venv holds only regenerable artifacts before delete |
| Symlink wrong direction / loop into CloudDocs | `readlink "$SRC"` == `$DST`; `$SRC` not already a CloudDocs symlink |
| iCloud re-materializes source after delete → split-brain | Zero dataless stubs + materialized before removing source |
| Cross-volume `cp` strips xattrs/quarantine | `ditto` or `rsync -aHAX`; strip quarantine on `$DST` |

## Related skills

This skill is cross-linked with every git skill in orama-system:

- [[git-history-surgery]] — re-anchor / tree-twin verification if a moved repo looks orphaned after the move; shared fail-closed posture. Cross-host `main` sync (non-destructive): [`git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md).
- [[using-git-worktrees]] — the worktree doctrine. This move relocates where worktrees physically live, and step 3 repairs them; it is the **permanent fix** for the "`* 2/` duplicate dirs" symptom listed in that skill's pre-flight table.
- [[oramasys-method]] / `references/tdd-gate.md` — after a move, re-run `bash scripts/git/install-local-hooks.sh`; hook scripts must avoid bash 4+ features (`mapfile`). See [`git-history-surgery/references/bash-32-git-script-portability.md`](../git-history-surgery/references/bash-32-git-script-portability.md).
- [[cidf]] — LINT-006 portable-path rule (`scripts/review/repo_hygiene.py` + `no-workstation-paths.py` hook) that step 6 must satisfy.
- [[openclaw-skills]] — the OpenClaw tree was moved out of iCloud the same way (prior art).
