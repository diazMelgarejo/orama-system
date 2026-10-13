#!/usr/bin/env bash
# Gated sync of an existing sibling checkout to origin/<branch>.
#
# Qualified-use gate for moving a checkout to the remote branch (see
# bin/orama-system/references/hard-reset-qualified-uses.md, use case 2): the tree
# must be clean and the checkout must hold no commit the remote lacks, checked and
# not assumed, and the target is an exact SHA captured once after the fetch.
#
# No hard reset is needed once those hold: on a clean tree, checking the branch out
# at the target SHA moves it and updates the files, and git itself refuses if that
# would overwrite anything.
#
# Return codes (callers decide policy; this function never discards work):
#   0   synced (or already current)
#   10  refused: working tree has tracked or untracked changes
#   11  refused: HEAD or the local branch has commits the remote does not
#   12  refused: could not establish whether commits are unique (fail closed)
#   *   a git command failed (fetch, rev-parse, checkout); its status is returned

MIRROR_SYNC_DIRTY=10
MIRROR_SYNC_UNIQUE=11
MIRROR_SYNC_UNKNOWN=12

# Count commits on <ref> that have no patch-equivalent in <target>. Prints the count;
# returns non-zero when git cannot answer.
_mirror_unique_commits() {
  local dest="$1" target="$2" ref="$3" out
  out="$(git -C "$dest" cherry "$target" "$ref")" || return 1
  printf '%s\n' "$out" | grep -c '^+' || true
}

mirror_sync_checkout() {
  local dest="$1" branch="$2" target ref count status
  git -C "$dest" fetch --prune origin || return $?
  target="$(git -C "$dest" rev-parse --verify "origin/${branch}^{commit}")" || return $?

  status="$(git -C "$dest" status --porcelain --untracked-files=all)" || return $?
  if [[ -n "$status" ]]; then
    return "$MIRROR_SYNC_DIRTY"
  fi

  # HEAD may sit on another branch; the local branch may be ahead of where HEAD is.
  for ref in HEAD "refs/heads/${branch}"; do
    git -C "$dest" rev-parse --verify --quiet "$ref" >/dev/null || continue
    count="$(_mirror_unique_commits "$dest" "$target" "$ref")" || return "$MIRROR_SYNC_UNKNOWN"
    if [[ "$count" -gt 0 ]]; then
      return "$MIRROR_SYNC_UNIQUE"
    fi
  done

  git -C "$dest" checkout --quiet -B "$branch" "$target"
}
