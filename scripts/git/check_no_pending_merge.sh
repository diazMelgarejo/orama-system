#!/usr/bin/env bash
# Block push while a --no-commit merge/cherry-pick/revert is still uncommitted.
#
# Exit codes (KB-indexed — see
# bin/orama-system/skills/git-history-surgery/references/pending-operation-push-guard-reference-card.md):
#   0 = GIT_PUSH_OK
#   1 = GIT_PUSH_E_PENDING_MERGE_CLEAN    (MERGE_HEAD, no unmerged paths)
#   2 = GIT_PUSH_E_PENDING_MERGE_CONFLICT (MERGE_HEAD + unmerged paths)
#   3 = GIT_PUSH_E_PENDING_CHERRY_PICK    (CHERRY_PICK_HEAD)
#   4 = GIT_PUSH_E_PENDING_REVERT         (REVERT_HEAD)
#
# A --no-commit operation leaves MERGE_HEAD / CHERRY_PICK_HEAD / REVERT_HEAD
# set until finalized. Pushing before that silently ships the PRE-operation tip.
#
# Caught 2026-07-30 on periscope PR #39: a fully-conflict-resolved
# `git merge origin/merged --no-commit --no-ff` was never followed by
# `git commit`. The branch was pushed and a PR opened describing the merge,
# but the pushed tip was still the pre-merge commit — the PR was empty
# relative to its own description.
set -euo pipefail

ROOT="${1:-$(git rev-parse --show-toplevel)}"
cd "$ROOT"

pending=()
has_merge=false
has_cherry=false
has_revert=false
merge_conflicted=false

for head in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD; do
  if git rev-parse -q --verify "$head" >/dev/null 2>&1; then
    pending+=("$head")
    case "$head" in
      MERGE_HEAD) has_merge=true ;;
      CHERRY_PICK_HEAD) has_cherry=true ;;
      REVERT_HEAD) has_revert=true ;;
    esac
  fi
done

if [[ ${#pending[@]} -eq 0 ]]; then
  exit 0
fi

if [[ "$has_merge" == true ]]; then
  if git diff --name-only --diff-filter=U | grep -q .; then
    merge_conflicted=true
  fi
fi

exit_code=0
symbol=""
if [[ "$merge_conflicted" == true ]]; then
  exit_code=2
  symbol="GIT_PUSH_E_PENDING_MERGE_CONFLICT"
elif [[ "$has_merge" == true ]]; then
  exit_code=1
  symbol="GIT_PUSH_E_PENDING_MERGE_CLEAN"
elif [[ "$has_cherry" == true ]]; then
  exit_code=3
  symbol="GIT_PUSH_E_PENDING_CHERRY_PICK"
elif [[ "$has_revert" == true ]]; then
  exit_code=4
  symbol="GIT_PUSH_E_PENDING_REVERT"
fi

hex_code=$(printf "0x%08X" "$exit_code")

echo "pre-push: blocked [$symbol] (exit $exit_code, $hex_code) — uncommitted in-progress operation(s): ${pending[*]}" >&2

for head in "${pending[@]}"; do
  case "$head" in
    MERGE_HEAD)
      if [[ "$merge_conflicted" == true ]]; then
        echo "  MERGE_HEAD: resolve and stage conflicts, then run 'git commit' to finalize the merge, or 'git merge --abort'." >&2
      else
        echo "  MERGE_HEAD: staged merge ready — run 'git commit' to finalize, or 'git merge --abort'." >&2
      fi
      ;;
    CHERRY_PICK_HEAD)
      echo "  CHERRY_PICK_HEAD: run 'git cherry-pick --continue' after resolving, or 'git cherry-pick --abort'." >&2
      ;;
    REVERT_HEAD)
      echo "  REVERT_HEAD: run 'git revert --continue' after resolving, or 'git revert --abort'." >&2
      ;;
  esac
done

echo "  The branch tip you're about to push is still the PRE-operation commit." >&2
echo "  Finalize or abort the operation above, then push again." >&2
echo "  KB: bin/orama-system/skills/git-history-surgery/references/pending-operation-push-guard-reference-card.md" >&2

exit "$exit_code"
