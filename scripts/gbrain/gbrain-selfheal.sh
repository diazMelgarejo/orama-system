#!/usr/bin/env bash
# gbrain-selfheal.sh — idempotent gbrain health guard (orama-owned, durable).
#
# WHY THIS EXISTS (read bin/orama-system/gstack/SKILL.md §GBrain Ops):
# We kept re-fixing the same gbrain sync rot by hand. Root causes that regenerate:
#   1. Autopilot (`gbrain autopilot --repo .`) jams on unacked parse failures and
#      silently lets sources go stale; it's launchd KeepAlive, so a kill won't stop
#      it — only `launchctl unload -w`.
#   2. Every repo path move (iCloud-escape, →~/code) spawns a NEW per-path source
#      and leaves the OLD-path source as a stale duplicate ("pending removal" that
#      never gets removed).
#   3. A bare `gbrain sync` from a non-git cwd only acks failures and refuses
#      ("Not a git repository"); per-source sync MUST run with --repo + --source.
#
# This script makes the SAFE remediations automatic and SURFACES the rest:
#   - acks transient failures (--skip-failed) per LIVE canonical source (with --repo+--source)
#   - refreshes the live sources
#   - REPORTS orphan sources (local_path missing) and autopilot misconfig
#   - never auto-archives/purges (that stays a human decision — see the skill)
#
# Safe to run repeatedly. Non-fatal. Honors the "don't call gbrain if not ok" rule.
set -uo pipefail

log() { printf '[gbrain-selfheal] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# gbrain CLI may live under ~/.bun/bin (not on a non-interactive PATH).
export PATH="$HOME/.bun/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
have gbrain || { log "gbrain not on PATH — skipping"; exit 0; }

# DB URL lives in ~/.gbrain/.env, not the shell env (skill §0).
set -a; source "$HOME/.gbrain/.env" 2>/dev/null || true; set +a

# Honor the hard rule: if local status isn't ok, do NOT call gbrain further.
DETECT="$HOME/.claude/skills/gstack/bin/gstack-gbrain-detect"
if [ -x "$DETECT" ]; then
  STATUS=$("$DETECT" 2>/dev/null | grep -o '"gbrain_local_status":[^,}]*' | sed 's/.*://; s/[ "]//g')
  if [ -n "${STATUS:-}" ] && [ "$STATUS" != "ok" ]; then
    log "gbrain_local_status=$STATUS (not ok) — skipping per safety rule"; exit 0
  fi
fi

# Autopilot misconfig guard (skill §6): a `--repo .` autopilot with cwd=/ jams sync.
AP_PID=$(pgrep -f 'gbrain autopilot' | head -1 || true)
if [ -n "${AP_PID:-}" ]; then
  AP_CWD=$(lsof -a -p "$AP_PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
  if [ "${AP_CWD:-/}" = "/" ]; then
    log "WARN autopilot pid $AP_PID cwd=/ (misconfig, skill §6) — it will jam sync."
    log "     Fix: launchctl unload -w ~/Library/LaunchAgents/com.gbrain.autopilot.plist"
  fi
fi

# LIVE canonical sources: pin id -> repo path. Edit when repos move (and archive the old source).
# Resolve repo roots portably; skip any that don't exist on this machine.
declare -a PAIRS=(
  "gstack-code-2159b4b9-595bce|${ORAMA_ROOT:-$HOME/code/OpenClaw/orama-system}"
  "gstack-code-078b0b90-f6179f|${PT_ROOT:-$HOME/code/OpenClaw/perplexity-api/Perpetua-Tools}"
  "gstack-code-alphaclaw-875d5b82|${ALPHACLAW_ROOT:-$HOME/code/OpenClaw/AlphaClaw}"
)

for pair in "${PAIRS[@]}"; do
  src="${pair%%|*}"; repo="${pair##*|}"
  if [ ! -d "$repo/.git" ]; then
    log "skip $src — repo not present: $repo"; continue
  fi
  log "sync $src  <-  $repo"
  ( cd "$repo" && timeout 600 gbrain sync --repo "$repo" --source "$src" --skip-failed 2>&1 | tail -3 ) || \
    log "WARN sync failed/timed out for $src (non-fatal)"
done

# Report orphan sources (registered local_path missing) — surface, do not delete.
if have jq; then
  log "orphan-source scan (path missing → quarantine candidate, see skill):"
  gbrain sources list --json 2>/dev/null | jq -r '.sources[]
    | select((.local_path // "") != "")
    | "\(.id)\t\(.local_path)"' 2>/dev/null | while IFS=$'\t' read -r id path; do
      [ -e "$path" ] || log "  ORPHAN $id -> $path (missing)"
    done
fi

# One-line health verdict.
have jq && gbrain doctor --fast --json 2>/dev/null \
  | jq -r '"[gbrain-selfheal] doctor: status=\(.status) score=\(.health_score)"' 2>/dev/null || true

log "done"
