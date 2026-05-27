#!/usr/bin/env bash
# One-shot: sync integration with upstream main + realign contrib branch(es).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ALPHACLAW_CONTRIB_BRANCHES="${ALPHACLAW_CONTRIB_BRANCHES:-cursor/sync-attribution-guards-6421}"
bash "$SCRIPT_DIR/alphaclaw-realign-contrib-branches.sh"
