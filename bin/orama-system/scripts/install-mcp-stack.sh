#!/usr/bin/env bash
# install-mcp-stack.sh — Idempotent MCP orchestration stack installer
# Installs: ai-cli-mcp + OpenClaw MCP registry entries.
# Gemini is DEPRECATED for unpaid tiers (cutoff 2026-06-18) and is only
# installed when explicitly requested via --include-gemini. Prefer AGY.
# Safe to run multiple times. Skips any step that is already complete.
# Platform bootstrap (Node, Ollama, CRG, gbrain): scripts/first-run-install.sh
#
# Core ai-cli-mcp readiness is shared with scripts/ensure_requirements.{sh,ps1}
# through scripts/ensure_ai_cli_mcp.py. Provider login/terms are never automated.
#
# Usage: bash install-mcp-stack.sh [--dry-run] [--force] [--include-gemini]
#                                  [--mirror-skills] [--core-only]
#                                  [--verify] [--non-interactive]
#
# --mirror-skills: copy SKILL.md files from bin/orama-system/*/SKILL.md to
#   ~/.claude/skills/<name>/SKILL.md, ~/.codex/skills/<name>/SKILL.md,
#   ~/.gemini/skills/<name>/SKILL.md (silently skipped if dir absent), and
#   openclaw skill registry (if openclaw CLI present). Idempotent (sha-compares).

set -euo pipefail

DRY_RUN=false
FORCE=false
INCLUDE_GEMINI=false
MIRROR_SKILLS=false
CORE_ONLY=false
VERIFY_ONLY=false
NON_INTERACTIVE=false

_usage() {
  cat <<'USAGE'
Usage: bash install-mcp-stack.sh [options]

Options:
  --dry-run          Preview optional integration commands without executing them.
  --force            Reinstall pinned core package and refresh registrations.
  --include-gemini   Include the optional/deprecated Gemini analyzer lane.
  --mirror-skills    Mirror canonical skills to installed harness directories.
  --core-only        Stop after ai-cli-mcp core readiness.
  --verify           Probe only; do not repair package/client registrations.
  --non-interactive  Compatibility flag; provider authorization is never automated.
  --help             Show this help.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --force) FORCE=true ;;
    --include-gemini) INCLUDE_GEMINI=true ;;
    --mirror-skills) MIRROR_SKILLS=true ;;
    --core-only) CORE_ONLY=true ;;
    --verify) VERIFY_ONLY=true ;;
    --non-interactive) NON_INTERACTIVE=true ;;
    --help|-h) _usage; exit 0 ;;
    *) echo "[mcp-install] unknown option: $arg" >&2; _usage >&2; exit 2 ;;
  esac
done

_log()  { echo "[mcp-install] $*"; }
_ok()   { echo "[mcp-install] ✓ $*"; }
_skip() { echo "[mcp-install] → skip: $*"; }
_warn() { echo "[mcp-install] ! $*" >&2; }
_fail() { echo "[mcp-install] ✗ FATAL: $*" >&2; exit 1; }
_run()  { $DRY_RUN && echo "[dry-run] $*" || eval "$*"; }

_safe_path() {
  local p="$1"
  case "$p" in
    -*) _fail "_safe_path: path may not start with dash: $p" ;;
    *[$'\t\n\$\`\;\&\|\<\>\(\)\{\}\*\?\[\]\\\'\"']*)
      _fail "_safe_path: path contains shell metacharacters: $p" ;;
  esac
}

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_REPO_ROOT="$(cd "$_SCRIPT_DIR/../../.." && pwd)"
_READINESS="$_REPO_ROOT/scripts/ensure_ai_cli_mcp.py"
[ -f "$_READINESS" ] || _fail "shared MCP readiness helper missing: $_READINESS"
AI_CLI_MCP_VERSION="$(python3 -c 'import runpy,sys; print(runpy.run_path(sys.argv[1])["AI_CLI_MCP_VERSION"])' "$_READINESS")"

_log "MCP orchestration stack installer"
_log "Dry-run: $DRY_RUN | Force: $FORCE | Verify: $VERIFY_ONLY"
echo ""

# ── Steps 1–3: shared ai-cli-mcp core readiness ───────────────────────────────
# This replaces the old duplicated Node/package/Claude registration logic and
# the unsafe synthetic ~/.claude/.dangerously-skip-accepted marker. Upstream
# `ai-cli doctor` explicitly checks binary/path availability only, so login and
# terms acceptance remain operator-controlled and are never inferred here.
_log "Steps 1–3: ai-cli-mcp core readiness"
_CORE_ARGS=()
$VERIFY_ONLY && _CORE_ARGS+=(--check)
$FORCE && _CORE_ARGS+=(--force)
if $DRY_RUN; then
  printf '[dry-run] python3 %q' "$_READINESS"
  printf ' %q' ${_CORE_ARGS[@]+"${_CORE_ARGS[@]}"}
  printf '\n'
else
  python3 "$_READINESS" ${_CORE_ARGS[@]+"${_CORE_ARGS[@]}"} \
    || _fail "ai-cli-mcp core readiness failed — follow remediation above"
fi
$NON_INTERACTIVE && _log "Provider authorization remains operator-controlled"

if $CORE_ONLY; then
  _ok "Core ai-cli-mcp readiness complete"
  exit 0
fi

# ── Step 4: Optional Gemini analyzer lane (DEPRECATED) ────────────────────────
_log "Step 4: Gemini analyzer lane"
if ! $INCLUDE_GEMINI; then
  _skip "Gemini not requested; analyzer lane remains opt-in"
else
  if command -v gemini >/dev/null 2>&1 && ! $FORCE; then
    _skip "gemini already installed ($(gemini --version 2>/dev/null | head -1 || echo 'version unknown'))"
  elif $VERIFY_ONLY; then
    _warn "gemini requested but CLI is missing"
  else
    _log "Installing @google/gemini-cli..."
    _run "npm install -g @google/gemini-cli"
  fi

  _log "Step 4b: Gemini auth check"
  if command -v gemini >/dev/null 2>&1; then
    if gemini auth check >/dev/null 2>&1; then
      _ok "gemini authenticated"
    else
      _warn "Gemini auth is not ready; run 'gemini auth login' interactively if this optional lane is required"
    fi
  fi

  _log "Step 4c: Register gemini-mcp-tool in Claude Code"
  if ! command -v claude >/dev/null 2>&1; then
    _skip "Claude Code not installed; gemini-cli client registration skipped"
  elif claude mcp list 2>/dev/null | grep -q "gemini-cli" && ! $FORCE; then
    _skip "gemini-cli already registered in Claude Code"
  elif $VERIFY_ONLY; then
    _warn "gemini-cli is not registered in Claude Code"
  else
    _run "claude mcp add -s user gemini-cli -- npx -y gemini-mcp-tool@latest"
    _ok "gemini-cli registered. Restart Claude Code, then verify with /mcp"
  fi
fi

# ── Step 5: OpenClaw MCP registry ─────────────────────────────────────────────
_log "Step 5: OpenClaw MCP registry"
if command -v openclaw >/dev/null 2>&1; then
  if openclaw mcp list 2>/dev/null | grep -q "ai-cli-mcp" && ! $FORCE; then
    _skip "ai-cli-mcp already in OpenClaw registry"
  elif $VERIFY_ONLY; then
    _warn "ai-cli-mcp is not registered in OpenClaw"
  else
    _run "openclaw mcp set ai-cli-mcp '{\"command\":\"npx\",\"args\":[\"-y\",\"ai-cli-mcp@${AI_CLI_MCP_VERSION}\"],\"env\":{\"MCP_CLAUDE_DEBUG\":\"false\"}}'"
    _ok "ai-cli-mcp registered in OpenClaw"
  fi

  if $INCLUDE_GEMINI; then
    if openclaw mcp list 2>/dev/null | grep -q "gemini-cli" && ! $FORCE; then
      _skip "gemini-cli already in OpenClaw registry"
    elif $VERIFY_ONLY; then
      _warn "gemini-cli is not registered in OpenClaw"
    else
      _run "openclaw mcp set gemini-cli '{\"command\":\"npx\",\"args\":[\"-y\",\"gemini-mcp-tool@latest\"]}'"
      _ok "gemini-cli registered in OpenClaw"
    fi
  fi
else
  _skip "OpenClaw registry (openclaw CLI not installed)"
fi

# ── Step 5b: Mirror orama SKILL.md to platform skill directories ─────────────
if $MIRROR_SKILLS; then
  _log "Step 5b: Mirroring orama SKILL.md files to platform skill dirs"
  _SKILLS_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"
  _PLATFORMS=(
    "$HOME/.claude/skills:claude"
    "$HOME/.codex/skills:codex"
    "$HOME/.gemini/skills:gemini (DEPRECATED)"
  )
  for _src_skill in "$_SKILLS_ROOT"/*/SKILL.md "$_SKILLS_ROOT/SKILL.md"; do
    [ -f "$_src_skill" ] || continue
    if [ "$_src_skill" = "$_SKILLS_ROOT/SKILL.md" ]; then
      _skill_name="orama-system"
    else
      _skill_name="$(basename "$(dirname "$_src_skill")")"
    fi
    for _plat in "${_PLATFORMS[@]}"; do
      _dst_root="${_plat%%:*}"
      _tool="${_plat##*:}"
      _dst_dir="$_dst_root/$_skill_name"
      _dst="$_dst_dir/SKILL.md"
      if [ ! -d "$_dst_root" ] && ! $FORCE; then
        _skip "$_tool (no $_dst_root)"
        continue
      fi
      if [ -f "$_dst" ] && command -v shasum >/dev/null 2>&1; then
        _src_hash=$(shasum -a 256 "$_src_skill" | awk '{print $1}')
        _dst_hash=$(shasum -a 256 "$_dst" | awk '{print $1}')
        if [ "$_src_hash" = "$_dst_hash" ]; then
          _skip "$_tool/$_skill_name (identical)"
          continue
        fi
      fi
      _safe_path "$_dst_dir"
      _safe_path "$_src_skill"
      _safe_path "$_dst"
      if $VERIFY_ONLY; then
        _warn "$_tool/$_skill_name differs from canonical skill"
      else
        _run "mkdir -p \"$_dst_dir\" && install -m 0644 \"$_src_skill\" \"$_dst\""
        _ok "mirror $_skill_name → $_tool"
      fi
    done
  done

  if command -v openclaw >/dev/null 2>&1; then
    for _src_skill in "$_SKILLS_ROOT"/*/SKILL.md; do
      [ -f "$_src_skill" ] || continue
      _skill_name="$(basename "$(dirname "$_src_skill")")"
      _safe_path "$_skill_name"
      _safe_path "$_src_skill"
      if $VERIFY_ONLY; then
        _skip "openclaw skill registry verification is not mutating"
      else
        _run "openclaw skill set \"$_skill_name\" \"$_src_skill\""
        _ok "openclaw skill set $_skill_name"
      fi
    done
  else
    _skip "openclaw skill registry (openclaw CLI not installed)"
  fi
  echo ""
fi

# ── Step 5c: Cursor project MCP stack ─────────────────────────────────────────
_log "Step 5c: Cursor MCP stack (orama-system/.cursor/mcp.json)"
_SYNC_CURSOR="$_SCRIPT_DIR/sync-cursor-mcp.sh"
if [ -f "$_SYNC_CURSOR" ]; then
  if $VERIFY_ONLY; then
    _skip "Cursor sync mutation skipped in --verify mode"
  else
    _run "bash \"$_SYNC_CURSOR\""
    _ok "Cursor project MCP: code-review-graph + ai-cli-mcp"
  fi
else
  _skip "sync-cursor-mcp.sh not found"
fi

echo ""
_log "Step 6: Verification summary"
echo "  ai-cli-mcp: ${AI_CLI_MCP_VERSION} (pinned core contract)"
echo "  provider auth: operator-controlled; not inferred by installer"
if command -v claude >/dev/null 2>&1; then
  echo "  claude mcp list:"
  claude mcp list 2>/dev/null | grep -E "gemini-cli|ai-cli" | sed 's/^/    /' || echo "    (no matching registration visible)"
fi
if command -v openclaw >/dev/null 2>&1; then
  echo "  openclaw mcp list:"
  openclaw mcp list 2>/dev/null | grep -E "gemini-cli|ai-cli" | sed 's/^/    /' || echo "    (empty)"
fi

echo ""
_log "Installation/readiness pass complete."
if $INCLUDE_GEMINI; then
  _log "NOTE: Gemini is deprecated for unpaid tiers (cutoff 2026-06-18). Prefer AGY for reviewer lanes."
fi
_log "Platform checklist (if not done): bash $_SCRIPT_DIR/first-run-install.sh status"

cat << 'ROLLBACK'

── ROLLBACK (if something went wrong) ──────────────────────────────────────────
  npm uninstall -g @google/gemini-cli ai-cli-mcp
  claude mcp remove -s user gemini-cli 2>/dev/null || claude mcp remove gemini-cli 2>/dev/null || true
  claude mcp remove -s user ai-cli 2>/dev/null || claude mcp remove ai-cli 2>/dev/null || true
  openclaw mcp unset gemini-cli 2>/dev/null || true
  openclaw mcp unset ai-cli-mcp 2>/dev/null || true
  NOTE: provider login/terms state is not written by this installer.
────────────────────────────────────────────────────────────────────────────────
ROLLBACK
