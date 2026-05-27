#!/usr/bin/env bash
# Rebuild AlphaClaw contrib branch(es) on integration tip; integration must contain origin/main.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
AC_ROOT="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
UPSTREAM_BRANCH="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
INTEGRATION_BRANCH="${ALPHACLAW_INTEGRATION_BRANCH:-feature/MacOS-post-install}"
CONTRIB_BRANCHES="${ALPHACLAW_CONTRIB_BRANCHES:-cursor/sync-attribution-guards-6421}"

if [[ ! -d "$AC_ROOT/.git" ]]; then
  echo "ERROR: AlphaClaw not cloned at $AC_ROOT" >&2
  exit 1
fi

bash "$SCRIPT_DIR/alphaclaw-sync-integration-with-main.sh"

cd "$AC_ROOT"
main_sha="$(git rev-parse "origin/${UPSTREAM_BRANCH}")"
integration_sha="$(git rev-parse "$INTEGRATION_BRANCH")"

mb_int="$(git merge-base "$main_sha" "$integration_sha")"
if [[ "$mb_int" != "$main_sha" ]]; then
  echo "ERROR: ${INTEGRATION_BRANCH} is not based on origin/${UPSTREAM_BRANCH}" >&2
  exit 1
fi
echo "OK: ${INTEGRATION_BRANCH} merge-base with origin/${UPSTREAM_BRANCH} is $(git log -1 --oneline "$mb_int")"

IFS=',' read -r -a branches <<<"$CONTRIB_BRANCHES"
for branch in "${branches[@]}"; do
  branch="${branch#"${branch%%[![:space:]]*}"}"
  branch="${branch%"${branch##*[![:space:]]}"}"
  [[ -n "$branch" ]] || continue

  if ! git show-ref --verify --quiet "refs/heads/${branch}"; then
    echo "skip: no local branch ${branch}"
    continue
  fi

  echo ">>> realign ${branch} onto ${INTEGRATION_BRANCH}"

  mapfile -t commits < <(
    git log "${integration_sha}..${branch}" --reverse --format='%H' --no-merges -- \
      scripts/git .githooks .cursor AGENTS.md 2>/dev/null || true
  )
  if [[ "${#commits[@]}" -eq 0 ]]; then
    mapfile -t commits < <(
      git log "${integration_sha}..${branch}" --reverse --format='%H' --no-merges
    )
  fi

  if [[ "${#commits[@]}" -eq 0 ]]; then
    if [[ "$(git rev-parse "$branch")" == "$integration_sha" ]]; then
      echo "    already aligned with ${INTEGRATION_BRANCH}"
      continue
    fi
  fi

  git branch -f "${branch}" "$integration_sha"
  git checkout "$branch"

  for sha in "${commits[@]}"; do
    if git merge-base --is-ancestor "$sha" "$integration_sha" 2>/dev/null; then
      continue
    fi
    echo "    cherry-pick $(git log -1 --oneline "$sha")"
    if ! git cherry-pick "$sha"; then
      echo "ERROR: cherry-pick failed for $sha on ${branch}" >&2
      git cherry-pick --abort 2>/dev/null || true
      exit 1
    fi
  done

  mb_main="$(git merge-base "$main_sha" HEAD)"
  mb_int_head="$(git merge-base "$integration_sha" HEAD)"
  if [[ "$mb_main" != "$main_sha" ]]; then
    echo "ERROR: ${branch} merge-base with origin/${UPSTREAM_BRANCH} is not main" >&2
    exit 1
  fi
  if [[ "$mb_int_head" != "$integration_sha" ]]; then
    echo "ERROR: ${branch} is not stacked on ${INTEGRATION_BRANCH}" >&2
    exit 1
  fi
  echo "    OK: $(git rev-list --count "${integration_sha}..HEAD") commit(s) on ${branch} above ${INTEGRATION_BRANCH}"
done

echo "OK: AlphaClaw contrib branches aligned (both share merge-base origin/${UPSTREAM_BRANCH})"
