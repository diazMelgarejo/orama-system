#!/usr/bin/env bash
# Scan, delete merged remotes, and cherry-reanchor open branches after a rewrite.
#
# Usage:
#   post-rewrite-reanchor.sh [repo_path]
#
# Env:
#   DELETE_ON_CHERRY_CONFLICT=1  delete conflicted branches (default 1 for automation)
#   DRY_RUN=1                    scan + print actions only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:-.}"
cd "$REPO"

DELETE_ON_CHERRY_CONFLICT="${DELETE_ON_CHERRY_CONFLICT:-1}"
DRY_RUN="${DRY_RUN:-0}"

scan="$(mktemp)"
actions="$(mktemp)"
trap 'rm -f "$scan" "$actions"' EXIT

bash "$SCRIPT_DIR/reanchor_scan.sh" "$PWD" origin/main remotes | tee "$scan"
python3 "$SCRIPT_DIR/parse-reanchor-scan.py" "$scan" >"$actions"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY_RUN: actions written to $actions"
  cat "$actions"
  exit 0
fi

bash "$SCRIPT_DIR/delete-merged-remote-branches.sh" "$PWD" --from-json "$actions"

cherry_args=(bash "$SCRIPT_DIR/cherry-reanchor-branches.sh" "$PWD" --from-json "$actions" --all-needs)
if [[ "$DELETE_ON_CHERRY_CONFLICT" == "1" ]]; then
  cherry_args+=(--delete-on-conflict)
fi
"${cherry_args[@]}"

echo ">>> verify open branches anchored on origin/main"
python3 - "$actions" <<'PY'
import json
import subprocess
import sys

actions = json.load(open(sys.argv[1]))
bad = []
for item in actions["needs"]:
    branch = item["branch"]
    ref = f"origin/{branch}"
    try:
        subprocess.run(
            ["git", "show-ref", "--verify", f"refs/remotes/{ref}"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        continue
    mb = subprocess.check_output(["git", "merge-base", "origin/main", ref], text=True).strip()
    main = subprocess.check_output(["git", "rev-parse", "origin/main"], text=True).strip()
    if mb != main:
        bad.append(branch)
if bad:
    print("WARN: branches not anchored on origin/main:", ", ".join(bad), file=sys.stderr)
    sys.exit(1)
print("OK: remaining NEEDS-REANCHOR branches have merge-base == origin/main")
PY

echo "OK: post-rewrite-reanchor complete"
