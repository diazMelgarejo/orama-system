#!/usr/bin/env bash
# Rebuild dependabot PRs #1–#3 against `merged` (build branch), not `main`.
#
# Branch model (diazMelgarejo/periscope):
#   agentsview — grandmother (latest upstream agentsview lineage)
#   main       — tracks latentsignal-org/periscope (upstream Periscope)
#   merged     — combines agentsview + main + fork-specific work (USE FOR BUILDS)
#
# Old PRs #1–#3 merged into main by mistake. This script:
#   1) Resets origin/main to latentsignal-org/periscope (upstream Periscope)
#   2) Cherry-picks the three dependabot commits onto branches from `merged`
#   3) Opens new PRs base=merged (run interactively; requires push access)
#
# Identity: cyre <diazMelgarejo@gmail.com> or Lawrence@cyre.me — no Co-authored-by trailers.
set -euo pipefail

REPO="${PERISCOPE_REPO:-$HOME/code/oramasys/tools/periscope}"
UPSTREAM="${PERISCOPE_UPSTREAM:-https://github.com/latentsignal-org/periscope.git}"
ORIGIN="${PERISCOPE_ORIGIN:-https://github.com/diazMelgarejo/periscope.git}"

# Dependabot commit SHAs from former main (PR #1 go, #2 npm, #3 cargo)
COMMIT_GO=a558443
COMMIT_NPM=499d659
COMMIT_CARGO=e6f09db

log() { printf '>>> %s\n' "$*"; }

if [[ ! -d "$REPO/.git" ]]; then
  log "clone -> $REPO"
  mkdir -p "$(dirname "$REPO")"
  git clone "$ORIGIN" "$REPO"
fi

cd "$REPO"
git config user.name "${GIT_AUTHOR_NAME:-cyre}"
git config user.email "${GIT_AUTHOR_EMAIL:-diazMelgarejo@gmail.com}"

git remote add upstream "$UPSTREAM" 2>/dev/null || true
# Two remotes, two fetches. (`git fetch origin upstream` asks origin for a *branch*
# named "upstream" and never fetches the upstream remote, which left upstream/main
# stale or missing, and the target of the re-point below is upstream/main.)
git fetch origin --prune
git fetch upstream --prune

# main is a mirror of upstream Periscope; the dependabot commits above were merged
# into it by mistake and are being re-homed onto `merged`. Those are the ONLY commits
# this step may drop. Anything else on local or remote main (or uncommitted work) is
# refused, and a backup ref is made before the remote is rewritten.
# shellcheck source=../cursor/lib-mirror-sync.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../cursor/lib-mirror-sync.sh"

log "Reset main -> upstream Periscope (latentsignal-org/periscope main)"
rc=0
mirror_repoint_to_upstream "$REPO" main upstream/main origin \
  "$COMMIT_GO" "$COMMIT_NPM" "$COMMIT_CARGO" || rc=$?
case "$rc" in
  0) ;;
  "$MIRROR_SYNC_DIRTY") log "ERROR: $REPO has uncommitted changes; refusing to re-point main"; exit 1 ;;
  "$MIRROR_SYNC_UNIQUE") log "ERROR: main holds commits that were not declared above (listed); refusing"; exit 1 ;;
  "$MIRROR_SYNC_UNKNOWN") log "ERROR: cannot verify that re-pointing main is safe"; exit 1 ;;
  *) log "ERROR: re-pointing main failed (git status $rc)"; exit "$rc" ;;
esac

log "Base branches from merged"
git fetch origin merged
BASE_SHA="$(git rev-parse origin/merged)"

create_dep_pr() {
  local num="$1" slug="$2" commit="$3" title="$4"
  local branch="deps/${num}-${slug}-onto-merged"
  log "branch $branch <= cherry-pick $commit"
  git checkout -B "$branch" "$BASE_SHA"
  git cherry-pick "$commit"
  git push -u origin "$branch" --force-with-lease
  gh pr create \
    --repo diazMelgarejo/periscope \
    --base merged \
    --head "$branch" \
    --title "[deps ${num}/3] ${title} (→ merged)" \
    --body "$(cat <<EOF
Rebuild of former PR #${num} (was incorrectly merged to \`main\`).

**Base:** \`merged\` (build branch — combines \`agentsview\` grandmother + \`main\` upstream Periscope + fork work).

**Merge order:** 1 (go) → 2 (npm) → 3 (cargo) → then docs PR #4.

Do not merge to \`main\`; \`main\` tracks upstream Periscope only.
EOF
)" \
    || log "PR may already exist for $branch"
}

create_dep_pr 1 "go-pgx" "$COMMIT_GO" "build(deps): bump pgx in go_modules group"
create_dep_pr 2 "npm-frontend" "$COMMIT_NPM" "build(deps): bump npm_and_yarn frontend group"
create_dep_pr 3 "cargo-tauri" "$COMMIT_CARGO" "build(deps): bump cargo tauri group"

log "Done. Close or note superseded merged PRs #1–#3 on main in GitHub UI."
log "Rename PR #4 title if needed: [4-docs] ... (merge after deps 1–3)"
