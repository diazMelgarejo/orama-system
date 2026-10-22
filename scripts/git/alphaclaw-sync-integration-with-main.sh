#!/usr/bin/env bash
# Ensure AlphaClaw integration branch contains upstream mirror (origin/main).
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
AC_ROOT="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
UPSTREAM_BRANCH="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
INTEGRATION_BRANCH="${ALPHACLAW_INTEGRATION_BRANCH:-feature/MacOS-post-install}"

if [[ ! -d "$AC_ROOT/.git" ]]; then
  echo "ERROR: AlphaClaw not cloned at $AC_ROOT" >&2
  exit 1
fi

cd "$AC_ROOT"
git fetch origin --prune

main_sha="$(git rev-parse "origin/${UPSTREAM_BRANCH}")"

echo ">>> sync local ${UPSTREAM_BRANCH} to origin/${UPSTREAM_BRANCH}"
# Both moves below discard whatever the branch holds beyond its remote, so they run
# through the gated move: clean tree, and nothing left unreferenced that was not
# already pushed. A refusal stops the script; it never erases local work.
# shellcheck source=../cursor/lib-mirror-sync.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../cursor/lib-mirror-sync.sh"

gated_move() {
  local branch="$1" rc=0
  mirror_sync_checkout "$AC_ROOT" "$branch" || rc=$?
  case "$rc" in
    0) return 0 ;;
    "$MIRROR_SYNC_DIRTY") echo "ERROR: ${AC_ROOT} has uncommitted changes; refusing to move ${branch}" >&2 ;;
    "$MIRROR_SYNC_UNIQUE") echo "ERROR: ${branch} holds unpushed commits (listed above); push or branch them first" >&2 ;;
    "$MIRROR_SYNC_UNKNOWN") echo "ERROR: cannot verify that moving ${branch} is safe" >&2 ;;
    *) echo "ERROR: could not move ${branch} (git status ${rc})" >&2 ;;
  esac
  return 1
}

# main is the upstream line: it moves forward to origin/main (fast-forward in effect).
gated_move "$UPSTREAM_BRANCH" || exit 1
main_sha="$(git rev-parse "origin/${UPSTREAM_BRANCH}")"

if git show-ref --verify --quiet "refs/remotes/origin/${INTEGRATION_BRANCH}"; then
  gated_move "$INTEGRATION_BRANCH" || exit 1
elif git show-ref --verify --quiet "refs/heads/${INTEGRATION_BRANCH}"; then
  git checkout "$INTEGRATION_BRANCH"
else
  git checkout -B "$INTEGRATION_BRANCH" "$main_sha"
fi

if git merge-base --is-ancestor "$main_sha" HEAD 2>/dev/null; then
  mb="$(git merge-base "$main_sha" HEAD)"
  if [[ "$mb" == "$main_sha" ]]; then
    echo "OK: ${INTEGRATION_BRANCH} already contains origin/${UPSTREAM_BRANCH} (merge-base=${main_sha:0:7})"
    exit 0
  fi
fi

echo ">>> merge origin/${UPSTREAM_BRANCH} into ${INTEGRATION_BRANCH}"
if ! git merge "$main_sha" -m "merge(upstream): sync origin/${UPSTREAM_BRANCH} into ${INTEGRATION_BRANCH}"; then
  echo "ERROR: merge failed — resolve conflicts, then commit" >&2
  exit 1
fi

mb="$(git merge-base "$main_sha" HEAD)"
if [[ "$mb" != "$main_sha" ]]; then
  echo "ERROR: merge-base(${UPSTREAM_BRANCH}, ${INTEGRATION_BRANCH}) is not origin/${UPSTREAM_BRANCH}" >&2
  exit 1
fi

echo "OK: ${INTEGRATION_BRANCH} merge-base with origin/${UPSTREAM_BRANCH} is $(git log -1 --oneline "$mb")"
