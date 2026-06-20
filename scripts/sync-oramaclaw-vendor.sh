#!/usr/bin/env bash
# sync-oramaclaw-vendor.sh — sync src/oramaclaw/ into Perpetua-Tools vendor mirror
#
# Resolves PT root from (in order):
#   1. $PERPETUA_TOOLS_ROOT
#   2. $PERPETUA_TOOLS_PATH
#   3. Aborts with an error message
#
# Usage:
#   bash scripts/sync-oramaclaw-vendor.sh
#
# Must be run from the orama-system repo root (where src/oramaclaw/ lives).

set -euo pipefail

# ── Resolve PT root ───────────────────────────────────────────────────────────

PT_ROOT=""

if [[ -n "${PERPETUA_TOOLS_ROOT:-}" ]]; then
    PT_ROOT="$PERPETUA_TOOLS_ROOT"
elif [[ -n "${PERPETUA_TOOLS_PATH:-}" ]]; then
    PT_ROOT="$PERPETUA_TOOLS_PATH"
else
    echo "ERROR: Neither PERPETUA_TOOLS_ROOT nor PERPETUA_TOOLS_PATH is set." >&2
    echo "  Export one of them to point at the Perpetua-Tools repo root." >&2
    exit 1
fi

if [[ ! -d "$PT_ROOT" ]]; then
    echo "ERROR: PT root does not exist as a directory: $PT_ROOT" >&2
    exit 1
fi

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$REPO_ROOT/src/oramaclaw/"
DEST="$PT_ROOT/vendor/oramaclaw/"

if [[ ! -d "$SRC" ]]; then
    echo "ERROR: Source directory not found: $SRC" >&2
    echo "  Run this script from the orama-system repo root." >&2
    exit 1
fi

# ── Sync ─────────────────────────────────────────────────────────────────────

rsync -a --delete "$SRC" "$DEST"

# ── Verify ───────────────────────────────────────────────────────────────────

if [[ ! -d "$DEST" ]]; then
    echo "ERROR: Destination directory was not created: $DEST" >&2
    exit 1
fi

echo "OK — oramaclaw vendor synced to $DEST"
