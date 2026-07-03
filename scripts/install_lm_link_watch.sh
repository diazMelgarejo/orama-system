#!/usr/bin/env bash
# install_lm_link_watch.sh — idempotent launchd installer for the Mac LM Link watcher.
# Installs com.orama.lm-link-watch running scripts/lm_link_watch.py with KeepAlive,
# so the Mac↔Win inference link (gossip + inbox) survives reboots and gateway
# restarts. Safe to re-run. Windows counterpart: scripts/lm_link_watch.ps1.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.orama.lm-link-watch"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$HOME/Library/Logs/openclaw"
PYTHON_BIN="$(command -v python3)"

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${REPO_ROOT}/scripts/lm_link_watch.py</string>
  </array>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>${LOG_DIR}/lm-link-watch.log</string>
  <key>StandardErrorPath</key><string>${LOG_DIR}/lm-link-watch.err.log</string>
</dict>
</plist>
PLIST

# Reload cleanly whether or not it was already loaded.
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "installed: ${LABEL}"
launchctl print "gui/$(id -u)/${LABEL}" 2>/dev/null | grep -E "state|pid" | head -3 || true
echo "state file: \$HOME/.openclaw/state/lm_link.json"
