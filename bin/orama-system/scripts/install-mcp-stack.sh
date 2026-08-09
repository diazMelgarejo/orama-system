#!/usr/bin/env bash
# install-mcp-stack.sh — deterministic, idempotent MCP readiness installer.
# Core contract: ai-cli-mcp package + Claude MCP registration.
# Provider authentication is reported separately and is never auto-accepted.
set -euo pipefail

AI_CLI_MCP_VERSION="${AI_CLI_MCP_VERSION:-2.22.0}"
DRY_RUN=0
FORCE=0
INCLUDE_GEMINI=0
MIRROR_SKILLS=0
CORE_ONLY=0
VERIFY_ONLY=0
NON_INTERACTIVE=0

_usage() {
  cat <<'USAGE'
Usage: install-mcp-stack.sh [options]

Options:
  --core-only        Install/repair only the core ai-cli-mcp + Claude registration.
  --verify           Make no changes; verify readiness and exit non-zero if core is not READY.
  --non-interactive  Never start login, browser, consent, or first-run prompts.
  --dry-run          Print mutations without executing them.
  --force            Repair/reinstall even when an existing installation is detected.
  --include-gemini   Configure the optional Gemini lane (never logs in automatically).
  --mirror-skills    Mirror ORAMASYS skills to installed platform skill directories.
  --help             Show this help.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --core-only) CORE_ONLY=1 ;;
    --verify) VERIFY_ONLY=1 ;;
    --non-interactive) NON_INTERACTIVE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --include-gemini) INCLUDE_GEMINI=1 ;;
    --mirror-skills) MIRROR_SKILLS=1 ;;
    --help|-h) _usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; _usage >&2; exit 2 ;;
  esac
done

_log()  { printf '[mcp-install] %s\n' "$*"; }
_ok()   { printf '[mcp-install] ✓ %s\n' "$*"; }
_warn() { printf '[mcp-install] ! %s\n' "$*" >&2; }
_fail() { printf '[mcp-install] ✗ FATAL: %s\n' "$*" >&2; exit 1; }

_run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

_json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip("\n")))'
}

_provider_claude="NOT_INSTALLED"
_provider_codex="NOT_INSTALLED"
_provider_gemini="DISABLED"
_remediation=()

# Upstream ai-cli-mcp 2.22.0 requires Node ^20.19.0 or >=22.12.0.
_check_node_runtime() {
  command -v node >/dev/null 2>&1 || _fail "Node.js is missing. ai-cli-mcp ${AI_CLI_MCP_VERSION} requires Node 20.19+ or 22.12+."
  command -v npm >/dev/null 2>&1 || _fail "npm is missing."
  command -v npx >/dev/null 2>&1 || _fail "npx is missing."
  node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
const ok = (major === 20 && minor >= 19) || (major === 22 && minor >= 12) || major > 22;
process.exit(ok ? 0 : 1);
' || _fail "Unsupported Node $(node -v). ai-cli-mcp ${AI_CLI_MCP_VERSION} requires Node 20.19+ or 22.12+."
  _ok "Node $(node -v), npm and npx satisfy ai-cli-mcp runtime requirements"
}

_installed_version() {
  npm list -g ai-cli-mcp --depth=0 --json 2>/dev/null \
    | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print((d.get("dependencies") or {}).get("ai-cli-mcp",{}).get("version",""))
except Exception:
    print("")' 2>/dev/null || true
}

_ensure_package() {
  local installed
  installed="$(_installed_version)"
  if [ "$installed" = "$AI_CLI_MCP_VERSION" ] \
     && command -v ai-cli >/dev/null 2>&1 \
     && command -v ai-cli-mcp >/dev/null 2>&1 \
     && [ "$FORCE" -eq 0 ]; then
    _ok "ai-cli-mcp ${installed} already installed"
    return 0
  fi

  if [ "$VERIFY_ONLY" -eq 1 ]; then
    _fail "ai-cli-mcp ${AI_CLI_MCP_VERSION} is not installed exactly (found: ${installed:-none})."
  fi

  _log "Installing reviewed ai-cli-mcp ${AI_CLI_MCP_VERSION}..."
  _run npm install -g "ai-cli-mcp@${AI_CLI_MCP_VERSION}"
  [ "$DRY_RUN" -eq 1 ] && return 0

  installed="$(_installed_version)"
  [ "$installed" = "$AI_CLI_MCP_VERSION" ] || _fail "Installed ai-cli-mcp version ${installed:-unknown}; expected ${AI_CLI_MCP_VERSION}."
  command -v ai-cli >/dev/null 2>&1 || _fail "ai-cli command missing after ai-cli-mcp install."
  command -v ai-cli-mcp >/dev/null 2>&1 || _fail "ai-cli-mcp command missing after install."
  _ok "ai-cli-mcp ${AI_CLI_MCP_VERSION} installed"
}

_claude_registration_matches() {
  command -v claude >/dev/null 2>&1 || return 1
  local details
  details="$(claude mcp get ai-cli 2>/dev/null || true)"
  printf '%s\n' "$details" | grep -Fq "ai-cli-mcp@${AI_CLI_MCP_VERSION}"
}

_ensure_claude_registration() {
  command -v claude >/dev/null 2>&1 || _fail "Claude Code CLI is required for the canonical ai-cli MCP registration."

  if _claude_registration_matches && [ "$FORCE" -eq 0 ]; then
    _ok "Claude MCP registration ai-cli is pinned to ai-cli-mcp@${AI_CLI_MCP_VERSION}"
    return 0
  fi

  if [ "$VERIFY_ONLY" -eq 1 ]; then
    _fail "Claude MCP registration 'ai-cli' is missing or not pinned to ai-cli-mcp@${AI_CLI_MCP_VERSION}."
  fi

  if [ "$DRY_RUN" -eq 0 ]; then
    claude mcp remove -s user ai-cli >/dev/null 2>&1 || claude mcp remove ai-cli >/dev/null 2>&1 || true
  else
    _log "[dry-run] would replace Claude MCP registration ai-cli"
  fi
  _run claude mcp add -s user ai-cli -- npx -y "ai-cli-mcp@${AI_CLI_MCP_VERSION}"
  [ "$DRY_RUN" -eq 1 ] || _claude_registration_matches \
    || _fail "Claude MCP registration repair did not produce the pinned ai-cli entry."
  _ok "Claude MCP registration repaired"
}

_verify_ai_cli() {
  [ "$DRY_RUN" -eq 1 ] && return 0
  ai-cli doctor >/dev/null 2>&1 || _fail "ai-cli doctor failed."
  ai-cli models >/dev/null 2>&1 || _fail "ai-cli models failed."
  _ok "ai-cli doctor + models passed"
}

_probe_providers() {
  if command -v claude >/dev/null 2>&1; then
    if claude auth status >/dev/null 2>&1; then
      _provider_claude="READY"
    else
      _provider_claude="DEGRADED"
      _remediation+=("Claude is installed but authentication/terms readiness could not be proven non-interactively. Run Claude's documented interactive setup, then rerun --verify.")
    fi
  fi

  if command -v codex >/dev/null 2>&1; then
    if codex login status >/dev/null 2>&1; then
      _provider_codex="READY"
    else
      _provider_codex="DEGRADED"
      _remediation+=("Codex is installed but login readiness could not be proven. Run: codex login")
    fi
  fi

  if [ "$INCLUDE_GEMINI" -eq 1 ]; then
    if command -v gemini >/dev/null 2>&1; then
      if gemini auth check >/dev/null 2>&1; then
        _provider_gemini="READY"
      else
        _provider_gemini="DEGRADED"
        _remediation+=("Gemini is installed but not authenticated. Run: gemini auth login")
      fi
    else
      _provider_gemini="DEGRADED"
      _remediation+=("Gemini lane requested but Gemini CLI is not installed.")
    fi
  fi
}

_configure_optional_lanes() {
  [ "$CORE_ONLY" -eq 1 ] && return 0

  if command -v openclaw >/dev/null 2>&1; then
    local cfg
    cfg="{\"command\":\"npx\",\"args\":[\"-y\",\"ai-cli-mcp@${AI_CLI_MCP_VERSION}\"],\"env\":{\"MCP_CLAUDE_DEBUG\":\"false\"}}"
    if [ "$VERIFY_ONLY" -eq 0 ]; then
      _run openclaw mcp set ai-cli-mcp "$cfg"
    fi
  fi

  local script_dir sync_cursor
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  sync_cursor="${script_dir}/sync-cursor-mcp.sh"
  if [ -f "$sync_cursor" ] && [ "$VERIFY_ONLY" -eq 0 ]; then
    _run bash "$sync_cursor"
  fi

  if [ "$MIRROR_SKILLS" -eq 1 ]; then
    _warn "--mirror-skills remains supported by the dedicated skill installation path; use scripts/install-skills.sh for canonical mirroring."
  fi
}

_emit_readiness_json() {
  local rem="["
  local first=1 r
  for r in "${_remediation[@]:-}"; do
    [ -n "$r" ] || continue
    [ "$first" -eq 1 ] || rem+=","
    rem+="$(printf '%s' "$r" | _json_escape)"
    first=0
  done
  rem+="]"
  printf '{"core":"READY","package":{"name":"ai-cli-mcp","version":"%s"},"provider":{"claude":"%s","codex":"%s","gemini":"%s"},"remediation":%s}\n' \
    "$AI_CLI_MCP_VERSION" "$_provider_claude" "$_provider_codex" "$_provider_gemini" "$rem"
}

_log "MCP readiness installer — ai-cli-mcp ${AI_CLI_MCP_VERSION}"
_check_node_runtime
_ensure_package
_ensure_claude_registration
_verify_ai_cli
_probe_providers
_configure_optional_lanes

if [ "$NON_INTERACTIVE" -eq 1 ]; then
  _log "Non-interactive mode: no provider login, browser, consent, or bypass-permission command was invoked."
fi

_emit_readiness_json
