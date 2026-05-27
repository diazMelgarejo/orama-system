#!/usr/bin/env bash
# Install git guard tooling under ~/.cursor/openclaw (outside any repo clone).
# Idempotent — safe on every cloud-install and manual re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOME="${HOME:-/home/ubuntu}"
export HOME

OPENCLAW_DIR="${HOME}/.cursor/openclaw"
GUARD_DIR="${OPENCLAW_DIR}/git-guards"
HOOK_DIR="${OPENCLAW_DIR}/hooks"
CURSOR_HOOKS_JSON="${HOME}/.cursor/hooks.json"
log() { printf '>>> [install-user-git-environment] %s\n' "$*"; }

mkdir -p "$GUARD_DIR" "$HOOK_DIR"

install -m 0755 "${REPO_ROOT}/scripts/git/cursor-hooks-id.sh" "${GUARD_DIR}/cursor-hooks-id.sh"
install -m 0755 "${REPO_ROOT}/scripts/git/disable-cursor-commit-attribution.sh" "${GUARD_DIR}/disable-cursor-commit-attribution.sh"
install -m 0755 "${REPO_ROOT}/scripts/git/hooks/commit-msg.strip-coauthor" "${GUARD_DIR}/commit-msg.strip-coauthor"
install -m 0755 "${REPO_ROOT}/scripts/cursor/hooks/session-apply-git-guards.sh" "${HOOK_DIR}/session-apply-git-guards.sh"

cat >"${GUARD_DIR}/apply-all-repos.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HOME="${HOME:-/home/ubuntu}"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
ORAMA="${ORAMA_SYSTEM_PATH:-${REPO_ROOT:-}}"
for candidate in "$ORAMA" "/workspace" "$HOME/workspace"; do
  if [[ -x "$candidate/scripts/git/apply-attribution-guard-all-repos.sh" ]]; then
    export ORAMA_SYSTEM_PATH="$candidate"
    export PERPETUA_TOOLS_PATH="${PERPETUA_TOOLS_PATH:-$OPENCLAW_HOME/Perpetua-Tools}"
    export ALPHACLAW_INSTALL_DIR="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
    exec bash "$candidate/scripts/git/apply-attribution-guard-all-repos.sh"
  fi
done
echo "ERROR: orama-system apply-attribution-guard-all-repos.sh not found" >&2
exit 1
EOF
chmod +x "${GUARD_DIR}/apply-all-repos.sh"

# Merge sessionStart into ~/.cursor/hooks.json (do not clobber unrelated hooks).
python3 - "$CURSOR_HOOKS_JSON" "$HOOK_DIR/session-apply-git-guards.sh" <<'PY'
import json
import sys
from pathlib import Path

dest = Path(sys.argv[1])
hook_script = sys.argv[2]
entry = {"command": hook_script, "timeout": 120}

if dest.is_file():
    cfg = json.loads(dest.read_text(encoding="utf-8"))
else:
    cfg = {"version": 1, "hooks": {}}

cfg.setdefault("version", 1)
hooks = cfg.setdefault("hooks", {})
existing = [
    h
    for h in (hooks.get("sessionStart") or [])
    if not (
        isinstance(h, dict)
        and h.get("command") in {"HOOK_SCRIPT_PATH_PLACEHOLDER", hook_script}
    )
]
existing.append(entry)
hooks["sessionStart"] = existing

dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
print(f"OK: {dest}")
PY

log "user guards installed under ${OPENCLAW_DIR}"

if [[ -x "${REPO_ROOT}/scripts/git/apply-attribution-guard-all-repos.sh" ]]; then
  log "apply repo guards (orama + siblings)"
  bash "${REPO_ROOT}/scripts/git/apply-attribution-guard-all-repos.sh"
fi

log "complete"
