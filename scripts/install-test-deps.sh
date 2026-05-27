#!/usr/bin/env bash
# Install orama-system runtime + test dependencies for local PoC and pytest runs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

python_bin="${PYTHON:-python3}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "ERROR: Python not found: $python_bin" >&2
  echo "Set PYTHON=/path/to/python or install Python 3.10+." >&2
  exit 1
fi

"$python_bin" -m pip install --upgrade pip setuptools wheel
"$python_bin" -m pip install -e ".[test]"

echo "OK: installed orama-system runtime and test dependencies, including FastAPI."
