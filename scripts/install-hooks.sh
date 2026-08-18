#!/usr/bin/env bash
# Install orama-system git hooks (idempotent — safe to run multiple times)
# Usage: bash scripts/install-hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "❌ .git/hooks not found at: $HOOKS_DIR"
  exit 1
fi

echo "🔧 Installing orama-system git hooks..."

cp "$SCRIPT_DIR/pre-commit-wrong-repo-build" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"
echo "  ✅ pre-commit → Wrong-Repo-Build guard (OS-D3)"

echo ""
echo "✅ Done. Run 'git commit' on any file to verify."
echo "   Uninstall: rm .git/hooks/pre-commit"
