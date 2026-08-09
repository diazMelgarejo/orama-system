#!/usr/bin/env bash
# End-to-end post-rewrite finish: publish main (+ optional all branches), reanchor, verify.
#
# Usage:
#   post-rewrite-finish.sh <repo_path>
#
# Typical workspace run after expunge-all-workspace-repos (REPO_ROOT is each
# repo's own real path -- resolve at call time, never hardcode a workstation
# layout here):
#   for repo_root in "$ORAMA_SYSTEM_PATH" "$PERPETUA_TOOLS_PATH"; do
#     bash "$ORAMA_SYSTEM_PATH/scripts/git/post-rewrite-finish.sh" "$repo_root"
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
objects = subprocess.check_output(["git", "rev-list", "--objects", "origin/main"], text=True).splitlines()
oid_input = "".join(line.split()[0] + "\n" for line in objects if line.split())
proc = subprocess.Popen(
    ["git", "cat-file", "--batch"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)
stdout, _ = proc.communicate(oid_input.encode())
if proc.returncode:
    sys.exit(proc.returncode)
pos = 0
while pos < len(stdout):
    header_end = stdout.find(b"\n", pos)
    if header_end == -1:
        break
    header = stdout[pos:header_end].decode("ascii", errors="replace")
    pos = header_end + 1
    parts = header.split()
    if len(parts) < 3:
        break
    kind = parts[1]
    size = int(parts[2])
    body_bytes = stdout[pos:pos + size]
    pos += size + 1
    body = body_bytes.decode("utf-8", errors="replace").casefold()
    if kind == "blob":
        if any(p in body for p in patterns):
            blob += 1
    elif kind == "commit":
        if any(p in body for p in patterns):
            meta += 1
if meta or blob:
    print(f"FAIL: origin/main meta_hits={meta} blob_hits={blob}", file=sys.stderr)
    sys.exit(1)
print("OK: origin/main forbidden-pattern scan clean (labels only)")
PY
fi

echo "OK: post-rewrite-finish complete for $(basename "$PWD")"
