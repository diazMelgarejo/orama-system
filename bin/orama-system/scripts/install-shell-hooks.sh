#!/usr/bin/env bash
# install-shell-hooks.sh — provision and re-create the Claude Code shell-safety hooks.
#
# The canonical hooks live in bin/orama-system/skills/shell-hygiene/hooks/ (shell-gotchas.py guards
# the Bash tool against zsh/macOS traps; no-workstation-paths.py guards Write/Edit). This script
# copies them into ~/.claude/hooks/ and registers them under hooks.PreToolUse in settings.json, so a
# fresh machine, or one whose hooks drifted, is brought back to the canonical state.
#
# Usage:
#   bash install-shell-hooks.sh                 # same as --check: read-only, exits 1 on drift
#   bash install-shell-hooks.sh --check
#   bash install-shell-hooks.sh --apply         # idempotent: copy, register, back up, self-test
#   bash install-shell-hooks.sh --apply --claude-home DIR   # DIR instead of $CLAUDE_HOME or ~/.claude
#   bash install-shell-hooks.sh --apply --mode enforce      # promote from the default warn rollout
#
# shell-gotchas.py is registered in warn mode by default (findings are reported, nothing is blocked)
# while the rules are tuned: review them with `python3 ~/.claude/hooks/shell-gotchas.py --report`,
# then promote with --mode enforce. --mode only changes how shell-gotchas.py is registered.
#
# --apply never replaces settings.json wholesale: it merges, keeps every other key and hook, writes a
# timestamped settings.json.bak-* first, and retires the superseded zsh-reserved-vars.py registration
# (its file is left in place). Bash 3.2 compatible; the JSON work is done by python3.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../skills/shell-hygiene/hooks"
MODE="check"
HOOK_MODE=""
CLAUDE_HOME_DIR="${CLAUDE_HOME:-$HOME/.claude}"

usage() {
  # The leading comment block only: stops at the first non-comment line, so editing the header never leaks code.
  awk 'NR > 1 { if (!/^#/) exit; sub(/^# ?/, ""); print }' "$0"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE="check" ;;
    --apply) MODE="apply" ;;
    --claude-home) CLAUDE_HOME_DIR="${2:?--claude-home needs a directory}"; shift ;;
    --mode) HOOK_MODE="${2:?--mode needs warn or enforce}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

[ -d "$SRC_DIR" ] || { echo "install-shell-hooks: canonical hooks not found at $SRC_DIR" >&2; exit 2; }

case "$HOOK_MODE" in ""|warn|enforce) ;; *) echo "install-shell-hooks: --mode must be warn or enforce" >&2; exit 2 ;; esac

exec python3 - "$MODE" "$SRC_DIR" "$CLAUDE_HOME_DIR" "$HOOK_MODE" <<'PY'
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

mode, src, home, hook_mode = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
apply = mode == "apply"
HOOKS = (("shell-gotchas.py", "Bash"), ("no-workstation-paths.py", "Write|Edit"))
LEGACY = (("zsh-reserved-vars.py", "Bash"),)  # superseded by the zsh-reserved-var rule
issues, actions = [], []


def command_for(name: str, want: str = "warn") -> str:
    """The registered command: $HOME-relative for the default home, absolute otherwise."""
    base = "$HOME/.claude" if home.resolve() == (Path.home() / ".claude").resolve() else str(home)
    prefix = "SHELL_GOTCHAS_MODE=warn " if name == "shell-gotchas.py" and want == "warn" else ""
    return f'{prefix}python3 "{base}/hooks/{name}"'


def atomic_write(path: Path, data: bytes, mode_bits: int) -> None:
    """Write via a temp file beside the real target, then rename over it; a symlinked path keeps its link."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.chmod(tmp, mode_bits)
    os.replace(tmp, path)


# Validate settings.json before touching anything, so a bad file never leaves a half-applied install.
settings_path = home / "settings.json"
original = settings_path.read_text(encoding="utf-8") if settings_path.is_file() else ""
try:
    settings = json.loads(original) if original.strip() else {}
except ValueError as exc:
    sys.exit(f"install-shell-hooks: {settings_path} is not valid JSON ({exc}); fix it first, nothing was changed")
groups = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])

for name, _ in HOOKS:
    wanted, dest = (src / name).read_bytes(), home / "hooks" / name
    if not dest.is_file() or dest.read_bytes() != wanted:
        issues.append(f"hooks/{name} is missing or differs from the canonical copy")
        if apply:
            atomic_write(dest, wanted, 0o644)
            actions.append(f"installed hooks/{name}")



def registered(name: str, matcher: str) -> bool:
    return any(g.get("matcher") == matcher and any(name in h.get("command", "") for h in g.get("hooks", [])) for g in groups)


for name, matcher in HOOKS:
    current = [h for g in groups if g.get("matcher") == matcher for h in g.get("hooks", []) if name in h.get("command", "")]
    in_mode = "warn" if current and "SHELL_GOTCHAS_MODE=warn" in current[0]["command"] else "enforce"
    want = hook_mode or (in_mode if current else "warn")  # no --mode: keep the current mode, new installs start in warn
    if current and name == "shell-gotchas.py" and in_mode != want:
        issues.append(f"{name} is registered in {in_mode} mode, not --mode {want}")
        if apply:
            current[0]["command"] = command_for(name, want)
            actions.append(f"registered {name} in {want} mode")
    elif not registered(name, matcher):
        issues.append(f"{name} is not registered for {matcher}")
        if apply:
            groups.append({"matcher": matcher, "hooks": [{"type": "command", "command": command_for(name, want), "timeout": 10}]})
            actions.append(f"registered {name} for {matcher}")

for name, matcher in LEGACY:
    if registered(name, matcher):
        issues.append(f"{name} is registered but superseded by shell-gotchas.py")
        if apply:
            for g in groups:
                if g.get("matcher") == matcher:
                    g["hooks"] = [h for h in g.get("hooks", []) if name not in h.get("command", "")]
            groups[:] = [g for g in groups if g.get("hooks")]
            actions.append(f"retired the {name} registration")

merged = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
if apply and (merged != original) and any(a.startswith(("registered", "retired")) for a in actions):
    if settings_path.is_file():
        backup = settings_path.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(settings_path, backup)
        actions.append(f"backed up settings to {backup.name}")
    atomic_write(settings_path, merged.encode("utf-8"), settings_path.stat().st_mode & 0o777 if settings_path.is_file() else 0o644)
    json.loads(settings_path.read_text(encoding="utf-8"))  # must still parse

installed = home / "hooks" / "shell-gotchas.py"
if installed.is_file():
    done = subprocess.run([sys.executable, str(installed), "--self-test"], capture_output=True, text=True)
    if done.returncode:
        issues.append("shell-gotchas.py --self-test failed: " + (done.stderr.strip().splitlines() or ["?"])[0])

if apply:
    print("\n".join(actions) if actions else "already up to date: nothing changed")
    sys.exit(1 if any("self-test" in i for i in issues) else 0)
if issues:
    print("\n".join(f"DRIFT: {i}" for i in issues))
    sys.exit(1)
print(f"OK: shell hooks installed and registered under {home}")
PY
