#!/usr/bin/env bash
# Install OpenClaw Cursor rules into a periscope clone (.cursor/rules/).
# Idempotent. Source templates live in orama-system (this repo).
set -euo pipefail

ORAMA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_DIR="$ORAMA_ROOT/scripts/periscope/cursor-rules-templates"
PERISCOPE_REPO="${PERISCOPE_REPO:-$HOME/Documents/oramasys/tools/periscope}"

if [[ ! -d "$TEMPLATE_DIR" ]]; then
  echo "install-cursor-rules: missing $TEMPLATE_DIR" >&2
  exit 1
fi

if [[ ! -d "$PERISCOPE_REPO/.git" ]]; then
  echo "install-cursor-rules: not a git repo: $PERISCOPE_REPO" >&2
  echo "  set PERISCOPE_REPO=/path/to/periscope" >&2
  exit 1
fi

mkdir -p "$PERISCOPE_REPO/.cursor/rules"
for f in "$TEMPLATE_DIR"/*.mdc; do
  [[ -f "$f" ]] || continue
  dest="$PERISCOPE_REPO/.cursor/rules/$(basename "$f")"
  if [[ -f "$dest" ]] && cmp -s "$f" "$dest"; then
    echo "  [·] $(basename "$f") unchanged"
  else
    cp "$f" "$dest"
    echo "  [+] $(basename "$f") -> $dest"
  fi
done

echo "OK: Cursor rules installed under $PERISCOPE_REPO/.cursor/rules/"
