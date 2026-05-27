#!/usr/bin/env bash
# Rebuild AlphaClaw contrib branches on top of origin/main (upstream mirror).
# Each branch is recreated from origin/main; unique commits are cherry-picked in order.
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
AC_ROOT="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
UPSTREAM_BRANCH="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
CONTRIB_BRANCHES="${ALPHACLAW_CONTRIB_BRANCHES:-cursor/sync-attribution-guards-6421}"

if [[ ! -d "$AC_ROOT/.git" ]]; then
  echo "ERROR: AlphaClaw not cloned at $AC_ROOT" >&2
  exit 1
fi

cd "$AC_ROOT"
git fetch origin --prune

echo ">>> sync local ${UPSTREAM_BRANCH} to origin/${UPSTREAM_BRANCH}"
git checkout "$UPSTREAM_BRANCH" 2>/dev/null || git checkout -b "$UPSTREAM_BRANCH"
git reset --hard "origin/${UPSTREAM_BRANCH}"

IFS=',' read -r -a branches <<<"$CONTRIB_BRANCHES"
for branch in "${branches[@]}"; do
  branch="${branch#"${branch%%[![:space:]]*}"}"
  branch="${branch%"${branch##*[![:space:]]}"}"
  [[ -n "$branch" ]] || continue

  if ! git show-ref --verify --quiet "refs/heads/${branch}"; then
    echo "skip: no local branch ${branch}"
    continue
  fi

  echo ">>> realign ${branch} onto origin/${UPSTREAM_BRANCH}"
  main_sha="$(git rev-parse "origin/${UPSTREAM_BRANCH}")"
  if [[ "$(git merge-base "${main_sha}" "${branch}")" == "${main_sha}" ]]     && [[ -z "$(git log "${main_sha}..${branch}" --format=%H 2>/dev/null | head -1)" ]]; then
    echo "    already aligned with origin/${UPSTREAM_BRANCH}"
    continue
  fi
  if [[ "$(git merge-base "${main_sha}" "${branch}")" == "${main_sha}" ]]     && [[ -n "$(git log "${main_sha}..${branch}" --format=%H 2>/dev/null | head -1)" ]]; then
    echo "    already based on origin/${UPSTREAM_BRANCH} ($(git log --oneline "${main_sha}..${branch}" | wc -l) commit(s))"
    continue
  fi
  mapfile -t commits < <(
    git log "origin/${UPSTREAM_BRANCH}..${branch}" --reverse --format='%H' --no-merges --       scripts/git .githooks .cursor AGENTS.md 2>/dev/null || true
  )
  if [[ "${#commits[@]}" -eq 0 ]]; then
    mapfile -t commits < <(
      git log "origin/${UPSTREAM_BRANCH}..${branch}" --reverse --format='%H' --no-merges
    )
  fi

  if [[ "${#commits[@]}" -eq 0 ]]; then
    echo "    already aligned (no unique commits)"
    continue
  fi

  git branch -f "${branch}" "origin/${UPSTREAM_BRANCH}"
  git checkout "$branch"

  for sha in "${commits[@]}"; do
    if git merge-base --is-ancestor "$sha" "origin/${UPSTREAM_BRANCH}" 2>/dev/null; then
      continue
    fi
    echo "    cherry-pick $(git log -1 --oneline "$sha")"
    if ! git cherry-pick "$sha"; then
      echo "ERROR: cherry-pick failed for $sha on ${branch}" >&2
      git cherry-pick --abort 2>/dev/null || true
      exit 1
    fi
  done

  mb="$(git merge-base "origin/${UPSTREAM_BRANCH}" HEAD)"
  if [[ "$mb" != "$(git rev-parse "origin/${UPSTREAM_BRANCH}")" ]]; then
    echo "ERROR: ${branch} merge-base is not origin/${UPSTREAM_BRANCH}" >&2
    exit 1
  fi
  echo "    OK: $(git log --oneline "origin/${UPSTREAM_BRANCH}..HEAD" | wc -l) commit(s) on ${branch}"
done

echo "OK: AlphaClaw contrib branches realigned to origin/${UPSTREAM_BRANCH}"
