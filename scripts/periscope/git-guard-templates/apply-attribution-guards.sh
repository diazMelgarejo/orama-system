#!/usr/bin/env bash
# Apply Cursor commit-attribution guards for this periscope clone only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISABLE="$SCRIPT_DIR/disable-cursor-commit-attribution.sh"

if [[ -x "$DISABLE" ]]; then
  bash "$DISABLE" "$REPO_ROOT"
  echo "OK: periscope attribution guards applied"
else
  echo "apply-attribution-guards: missing $DISABLE (run install-cursor-rules.sh from orama-system)" >&2
  exit 1
fi
