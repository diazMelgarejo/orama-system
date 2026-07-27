#!/usr/bin/env bash
# sync_openclaw_overlay_from_staging.sh
# Integrative merge: refresh ## Oramasys role overlay sections from bin/agents/*/SOUL.md
# without replacing OpenClaw Core Truths template prose.
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_SRC="$REPO_ROOT/bin/agents"
REGISTRY="$AGENTS_SRC/REGISTRY.yml"
OVERLAY_MARKER="## Oramasys role overlay"

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 required"
  exit 1
fi

if [[ ! -f "$REGISTRY" ]]; then
  fail "missing REGISTRY.yml at $REGISTRY"
  exit 1
fi

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

if [[ "${ORAMA_TRUST_HERMES_SYNC:-}" == "1" ]]; then
  : # explicit operator override after reviewing bin/agents
elif [[ ! -f "$REPO_ROOT/scripts/review/verify_trusted_install.py" ]]; then
  fail "overlay sync blocked — verify_trusted_install.py missing (git pull --ff-only or ORAMA_TRUST_HERMES_SYNC=1)"
  exit 1
elif ! python3 "$REPO_ROOT/scripts/review/verify_trusted_install.py" --quiet; then
  fail "overlay sync blocked — untrusted checkout (set ORAMA_TRUST_HERMES_SYNC=1 after review)"
  exit 1
fi

updated=0
skipped=0

while IFS='|' read -r openclaw_id workspace staging_soul; do
  [[ -z "$openclaw_id" ]] && continue
  target_soul="$workspace/SOUL.md"
  if [[ ! -f "$target_soul" ]]; then
    warn "skip $openclaw_id — no SOUL at $target_soul"
    ((skipped++)) || true
    continue
  fi
  overlay_body="$(sed '1d' "$staging_soul")"
  overlay_section="${OVERLAY_MARKER} (MERGE-10 + EDITED-03)

${overlay_body}"

  if [[ $DRY_RUN -eq 1 ]]; then
    ok "would update overlay: $openclaw_id → $target_soul"
    ((updated++)) || true
    continue
  fi

  python3 - "$target_soul" "$OVERLAY_MARKER" "$overlay_section" <<'PY'
import sys
from pathlib import Path

target = Path(sys.argv[1])
marker = sys.argv[2]
overlay = sys.argv[3]
home = Path.home()
allowed_roots = [
    (home / ".openclaw" / "agents").resolve(),
    (home / ".alphaclaw" / ".openclaw" / "workspace").resolve(),
]

def allowed_workspace(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in allowed_roots:
        if resolved == root or root in resolved.parents:
            return True
    return False

if not allowed_workspace(target.parent):
    raise SystemExit(
        f"refusing overlay write outside OpenClaw workspace allowlist: {target}"
    )

text = target.read_text(encoding="utf-8")
if marker in text:
    head, _, _ = text.partition(marker)
    new_text = head.rstrip() + "\n\n---\n\n" + overlay + "\n"
else:
    new_text = text.rstrip() + "\n\n---\n\n" + overlay + "\n"
target.write_text(new_text, encoding="utf-8")
PY
  ok "$openclaw_id overlay synced from $(basename "$(dirname "$staging_soul")")/SOUL.md"
  ((updated++)) || true
done < <(REPO_ROOT="$REPO_ROOT" python3 - <<'PY'
import os
import sys
from pathlib import Path

import yaml

repo = Path(os.environ["REPO_ROOT"])
data = yaml.safe_load((repo / "bin/agents/REGISTRY.yml").read_text(encoding="utf-8"))
home = Path.home()
allowed_roots = [
    (home / ".openclaw" / "agents").resolve(),
    (home / ".alphaclaw" / ".openclaw" / "workspace").resolve(),
]


def expand(value: str) -> str:
    return value.replace("${HOME}", str(home))


def allowed_workspace(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in allowed_roots:
        if resolved == root or root in resolved.parents:
            return True
    return False


for entry in data.get("roles", []):
    ws = entry.get("openclaw_workspace")
    if not ws:
        continue
    workspace = Path(expand(ws))
    if not allowed_workspace(workspace):
        print(f"refusing REGISTRY openclaw_workspace outside allowlist: {workspace}", file=sys.stderr)
        continue
    folder = entry["staging_folder"]
    soul = repo / "bin/agents" / folder / "SOUL.md"
    if not soul.is_file():
        continue
    print(f"{entry['openclaw_id']}|{workspace}|{soul}")

life = repo / "bin/agents/lifecycle/SOUL.md"
main_ws = Path(expand("${HOME}/.alphaclaw/.openclaw/workspace"))
if life.is_file() and allowed_workspace(main_ws):
    print(f"main|{main_ws}|{life}")
PY
)

echo ""
echo "OpenClaw overlay sync: updated=$updated skipped=$skipped dry_run=$DRY_RUN"
echo "Registry: $REGISTRY"
