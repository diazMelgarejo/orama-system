#!/usr/bin/env bash
# Gated moves of a branch to another ref (mirror sync, fork-main re-point).
#
# Qualified-use gate for a hard-reset-style move (see
# bin/orama-system/references/hard-reset-qualified-uses.md): the tree must be clean
# and the move must leave no commit unreferenced that the caller did not declare,
# checked and not assumed. The target is an exact SHA captured once after the fetch.
#
# "At risk" is precise: a commit is lost only if no ref other than the ones being
# moved still reaches it. A commit that another branch, tag or remote-tracking ref
# holds survives the move and is not counted, so an integration branch that is
# legitimately ahead of main is not a reason to refuse.
#
# No hard reset is needed once the gate holds: on a clean tree, checking the branch
# out at the target SHA moves it and updates the files, and git itself refuses if
# that would overwrite anything.
#
# Return codes (callers decide policy; these functions never discard work):
#   0   moved (or already current)
#   10  refused: working tree has tracked or untracked changes
#   11  refused: the move would leave undeclared commits unreferenced
#   12  refused: could not establish whether commits are at risk (fail closed)
#   *   a git command failed (fetch, rev-parse, checkout, push); its status is returned

MIRROR_SYNC_DIRTY=10
MIRROR_SYNC_UNIQUE=11
MIRROR_SYNC_UNKNOWN=12

# Print the commits that moving the given refs to <target> would leave unreferenced
# and that have no patch-equivalent in <target>. The refs are the ones being moved
# (full names, or HEAD for a detached head); everything else keeps commits alive.
# Returns non-zero when git cannot answer.
mirror_at_risk_commits() {
  local dest="$1" target="$2"
  shift 2
  local ref reachable candidates=""
  reachable="$({
    for ref in "$@"; do
      git -C "$dest" rev-parse --verify --quiet "${ref}^{commit}" >/dev/null && printf '%s\n' "$ref"
    done
    printf '^%s\n' "$target"
    # Every other ref that points at a commit (or at a tag of one) keeps history alive.
    # A symbolic ref (origin/HEAD) is only an alias of a ref that may be the one being
    # moved, so it is not an independent holder and must not count.
    git -C "$dest" for-each-ref --format='%(objecttype)|%(*objecttype)|%(symref)|%(refname)' |
      awk -F'|' '$3 == "" && ($1 == "commit" || ($1 == "tag" && $2 == "commit")) { print "^" $4 }' |
      grep -vxF -f <(printf '^%s\n' "$@") || true
  } | git -C "$dest" rev-list --stdin)" || return 1
  [[ -n "$reachable" ]] || return 0

  for ref in "$@"; do
    git -C "$dest" rev-parse --verify --quiet "${ref}^{commit}" >/dev/null || continue
    candidates+="$(git -C "$dest" cherry "$target" "$ref")"$'\n' || return 1
  done
  candidates="$(printf '%s' "$candidates" | awk '/^\+/ { print $2 }')"
  [[ -n "$candidates" ]] || return 0
  printf '%s\n' "$reachable" | grep -xF -f <(printf '%s\n' "$candidates") || true
}

# Succeeds when the working tree has no tracked or untracked changes.
mirror_tree_is_clean() {
  local status
  status="$(git -C "$1" status --porcelain --untracked-files=all)" || return 1
  [[ -z "$status" ]]
}

# mirror_sync_checkout <dest> <branch>
# Move <branch> in <dest> to the exact SHA of origin/<branch> (checked out).
mirror_sync_checkout() {
  local dest="$1" branch="$2" target at_risk
  local moved=()
  git -C "$dest" fetch --prune origin || return $?
  target="$(git -C "$dest" rev-parse --verify "origin/${branch}^{commit}")" || return $?

  mirror_tree_is_clean "$dest" || return "$MIRROR_SYNC_DIRTY"

  # Only a detached HEAD holds commits that no branch name keeps alive.
  git -C "$dest" rev-parse --verify --quiet "refs/heads/${branch}" >/dev/null &&
    moved+=("refs/heads/${branch}")
  git -C "$dest" symbolic-ref --quiet HEAD >/dev/null || moved+=(HEAD)

  at_risk="$(mirror_at_risk_commits "$dest" "$target" ${moved[@]+"${moved[@]}"})" ||
    return "$MIRROR_SYNC_UNKNOWN"
  if [[ -n "$at_risk" ]]; then
    printf 'mirror-sync: refusing, would leave unreferenced:\n%s\n' "$at_risk" >&2
    return "$MIRROR_SYNC_UNIQUE"
  fi

  git -C "$dest" checkout --quiet -B "$branch" "$target"
}

# mirror_repoint_to_upstream <dest> <branch> <upstream-ref> <remote> [declared-commit]...
# Re-point <branch> locally AND on <remote> to <upstream-ref> (a fork whose main is
# defined as the upstream mirror). The only commits allowed to be dropped are the
# declared ones; anything else on the local or remote branch is refused. A backup
# ref is created first, and the remote is updated with an expected-head lease, so a
# concurrent push is not overwritten.
mirror_repoint_to_upstream() {
  local dest="$1" branch="$2" upstream_ref="$3" remote="$4"
  shift 4
  local target remote_sha local_sha at_risk sha declared full stamp
  local moved=() allowed=()

  target="$(git -C "$dest" rev-parse --verify "${upstream_ref}^{commit}")" || return $?
  remote_sha="$(git -C "$dest" rev-parse --verify --quiet "refs/remotes/${remote}/${branch}^{commit}")" ||
    remote_sha=""
  local_sha="$(git -C "$dest" rev-parse --verify --quiet "refs/heads/${branch}^{commit}")" || local_sha=""

  mirror_tree_is_clean "$dest" || return "$MIRROR_SYNC_DIRTY"

  [[ -n "$local_sha" ]] && moved+=("refs/heads/${branch}")
  [[ -n "$remote_sha" ]] && moved+=("refs/remotes/${remote}/${branch}")
  git -C "$dest" symbolic-ref --quiet HEAD >/dev/null || moved+=(HEAD)

  at_risk="$(mirror_at_risk_commits "$dest" "$target" ${moved[@]+"${moved[@]}"})" ||
    return "$MIRROR_SYNC_UNKNOWN"
  for declared in "$@"; do
    full="$(git -C "$dest" rev-parse --verify --quiet "${declared}^{commit}")" || continue
    allowed+=("$full")
  done
  while IFS= read -r sha; do
    [[ -n "$sha" ]] || continue
    if ! printf '%s\n' ${allowed[@]+"${allowed[@]}"} | grep -qxF "$sha"; then
      printf 'repoint: refusing, undeclared commit would be dropped: %s\n' \
        "$(git -C "$dest" log -1 --format='%h %s' "$sha")" >&2
      return "$MIRROR_SYNC_UNIQUE"
    fi
  done <<<"$at_risk"

  # A recovery ref for everything about to be rewritten, before anything moves.
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  for sha in $remote_sha $local_sha; do
    [[ "$sha" == "$target" ]] && continue
    git -C "$dest" branch --force "backup/${branch}-before-repoint-${stamp}-${sha:0:7}" "$sha" || return $?
  done

  git -C "$dest" checkout --quiet -B "$branch" "$target" || return $?
  [[ "$remote_sha" == "$target" ]] && return 0
  if [[ -n "$remote_sha" ]]; then
    git -C "$dest" push --force-with-lease="${branch}:${remote_sha}" "$remote" "${branch}:${branch}"
  else
    git -C "$dest" push "$remote" "${branch}:${branch}"
  fi
}
