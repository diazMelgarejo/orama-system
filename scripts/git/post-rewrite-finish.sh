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
import tempfile
from pathlib import Path

patterns = [
    p.strip().casefold()
    for p in Path.home().joinpath(".cursor/openclaw/banned-attribution-patterns").read_text().splitlines()
    if p.strip() and not p.strip().startswith("#")
]
meta = blob = 0

with tempfile.NamedTemporaryFile("wb+", suffix=".oids") as oid_file:
    rev_list = subprocess.run(
        ["git", "rev-list", "--objects", "origin/main"],
        stdout=subprocess.PIPE,
        check=True,
    )
    for line in rev_list.stdout.splitlines():
        oid = line.split()[:1]
        if oid:
            oid_file.write(oid[0] + b"\n")
    oid_file.flush()
    oid_file.seek(0)

    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        stdin=oid_file,
        stdout=subprocess.PIPE,
    )
    while True:
        header_line = proc.stdout.readline()
        if not header_line:
            break
        header = header_line.decode("ascii", errors="replace").rstrip("\n")
        parts = header.split()
        if len(parts) < 3:
            print(f"FAIL: malformed cat-file header: {header!r}", file=sys.stderr)
            proc.kill()
            sys.exit(1)
        oid, kind, size_s = parts[0], parts[1], parts[2]
        try:
            size = int(size_s)
        except ValueError:
            print(f"FAIL: malformed cat-file size in header: {header!r}", file=sys.stderr)
            proc.kill()
            sys.exit(1)
        body_bytes = proc.stdout.read(size + 1)
        if len(body_bytes) != size + 1:
            print(
                f"FAIL: truncated cat-file payload for {oid} "
                f"(expected {size} bytes, got {len(body_bytes) - 1})",
                file=sys.stderr,
            )
            proc.kill()
            sys.exit(1)
        body = body_bytes[:-1].decode("utf-8", errors="replace").casefold()
        if kind == "blob":
            if any(p in body for p in patterns):
                blob += 1
        elif kind == "commit":
            if any(p in body for p in patterns):
                meta += 1
    rc = proc.wait()
    if rc:
        print(f"FAIL: git cat-file exited {rc}", file=sys.stderr)
        sys.exit(rc)

if meta or blob:
    print(f"FAIL: origin/main meta_hits={meta} blob_hits={blob}", file=sys.stderr)
    sys.exit(1)
print("OK: origin/main forbidden-pattern scan clean (labels only)")
PY
fi

echo "OK: post-rewrite-finish complete for $(basename "$PWD")"
