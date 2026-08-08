#!/usr/bin/env bash
# End-to-end post-rewrite finish: publish main (+ optional all branches), reanchor, verify.
#
# Usage:
#   post-rewrite-finish.sh <repo_path>
#
# Typical workspace run after expunge-all-workspace-repos:
#   for repo in orama-system Perpetua-Tools AlphaClaw; do
#     bash orama-system/scripts/git/post-rewrite-finish.sh "/agent/repos/$repo"
#   done
#
# Env: see post-rewrite-publish.sh and post-rewrite-reanchor.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:?usage: post-rewrite-finish.sh <repo_path>}"
cd "$REPO"

echo "=== post-rewrite-finish: $(basename "$PWD") ==="
bash "$SCRIPT_DIR/post-rewrite-publish.sh" "$PWD"
bash "$SCRIPT_DIR/post-rewrite-reanchor.sh" "$PWD"

if [[ -f scripts/git/scan-tracked-banned-tokens.sh ]]; then
  bash scripts/git/scan-tracked-banned-tokens.sh
fi

if [[ -f "$HOME/.cursor/openclaw/banned-attribution-patterns" ]]; then
  python3 - <<'PY'
import subprocess
import sys
from pathlib import Path

patterns = [
    p.strip().casefold()
    for p in Path.home().joinpath(".cursor/openclaw/banned-attribution-patterns").read_text().splitlines()
    if p.strip() and not p.strip().startswith("#")
]
meta = blob = 0
for line in subprocess.check_output(["git", "rev-list", "--objects", "origin/main"], text=True).splitlines():
    oid = line.split()[0]
    kind = subprocess.run(["git", "cat-file", "-t", oid], capture_output=True, text=True).stdout.strip()
    if kind == "blob":
        body = subprocess.run(
            ["git", "cat-file", "-p", oid], capture_output=True, text=True, errors="replace"
        ).stdout.casefold()
        if any(p in body for p in patterns):
            blob += 1
    elif kind == "commit":
        show = subprocess.run(
            ["git", "log", "-1", "--format=%B %an %ae %cn %ce", oid],
            capture_output=True,
            text=True,
        ).stdout.casefold()
        if any(p in show for p in patterns):
            meta += 1
if meta or blob:
    print(f"FAIL: origin/main meta_hits={meta} blob_hits={blob}", file=sys.stderr)
    sys.exit(1)
print("OK: origin/main forbidden-pattern scan clean (labels only)")
PY
fi

echo "OK: post-rewrite-finish complete for $(basename "$PWD")"
