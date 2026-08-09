#!/usr/bin/env bash
# install-mcp-stack.sh — idempotent MCP orchestration stack installer/readiness probe.
set -euo pipefail

AI_CLI_MCP_VERSION="${AI_CLI_MCP_VERSION:-2.22.0}"
DRY_RUN=false; FORCE=false; INCLUDE_GEMINI=false; MIRROR_SKILLS=false
CORE_ONLY=false; VERIFY_ONLY=false; NON_INTERACTIVE=false
usage(){ cat <<USAGE
Usage: bash install-mcp-stack.sh [--dry-run] [--force] [--include-gemini] [--mirror-skills]
                                 [--core-only] [--verify] [--non-interactive]
USAGE
}
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true;; --force) FORCE=true;; --include-gemini) INCLUDE_GEMINI=true;;
    --mirror-skills) MIRROR_SKILLS=true;; --core-only) CORE_ONLY=true;; --verify) VERIFY_ONLY=true;;
    --non-interactive) NON_INTERACTIVE=true;; -h|--help) usage; exit 0;;
    *) echo "[mcp-install] unknown option: $arg" >&2; usage >&2; exit 2;;
  esac
done
$VERIFY_ONLY && DRY_RUN=false

_log(){ echo "[mcp-install] $*"; }
_ok(){ echo "[mcp-install] ✓ $*"; }
_skip(){ echo "[mcp-install] → skip: $*"; }
_fail(){ echo "[mcp-install] ✗ FATAL: $*" >&2; exit 1; }
_run(){ $DRY_RUN && printf '[dry-run] %s\n' "$*" || eval "$*"; }

provider_claude="NOT_INSTALLED"; provider_codex="NOT_INSTALLED"; provider_gemini="DISABLED"
checks=(); remediation=()
check(){ checks+=("$1"); }
remedy(){ remediation+=("$1"); }

_log "ai-cli-mcp ${AI_CLI_MCP_VERSION} readiness | verify=${VERIFY_ONLY} core-only=${CORE_ONLY} non-interactive=${NON_INTERACTIVE}"

# Node contract follows upstream ai-cli-mcp engines: ^20.19.0 || >=22.12.0.
command -v node >/dev/null 2>&1 || _fail "Node.js not found (requires >=20.19 on Node 20, or >=22.12)."
node -e 'const [M,m]=process.versions.node.split(".").map(Number); process.exit((M===20&&m>=19)||M>=22?0:1)' \
  || _fail "Node.js $(node -v) is unsupported by ai-cli-mcp ${AI_CLI_MCP_VERSION}; require >=20.19 or >=22.12."
check "node:$(node -v)"
command -v npm >/dev/null 2>&1 || _fail "npm not found."
command -v npx >/dev/null 2>&1 || _fail "npx not found."
check "npm+npx:ready"

if ! command -v ai-cli >/dev/null 2>&1 || ! command -v ai-cli-mcp >/dev/null 2>&1 || $FORCE; then
  if $VERIFY_ONLY; then _fail "ai-cli-mcp core binaries missing; run without --verify to repair."; fi
  _log "Installing pinned ai-cli-mcp@${AI_CLI_MCP_VERSION} globally..."
  _run "npm install -g 'ai-cli-mcp@${AI_CLI_MCP_VERSION}'"
  $DRY_RUN || hash -r 2>/dev/null || true
else
  _skip "ai-cli + ai-cli-mcp already installed"
fi
if ! $DRY_RUN; then
  command -v ai-cli >/dev/null 2>&1 || _fail "ai-cli missing after install/repair."
  command -v ai-cli-mcp >/dev/null 2>&1 || _fail "ai-cli-mcp missing after install/repair."
  ai-cli doctor >/dev/null 2>&1 || _fail "ai-cli doctor failed."
  ai-cli models >/dev/null 2>&1 || _fail "ai-cli models failed."
  check "ai-cli:doctor+models:ready"
fi

if ! command -v claude >/dev/null 2>&1; then
  provider_claude="NOT_INSTALLED"; remedy "Install Claude Code, then rerun --verify."
  _fail "Claude Code CLI not found; canonical ai-cli MCP registration cannot be verified."
fi
if claude mcp list 2>/dev/null | grep -Eq '(^|[[:space:]])ai-cli([[:space:]]|:|$)' && ! $FORCE; then
  _skip "ai-cli already registered in Claude Code"
else
  if $VERIFY_ONLY; then _fail "Claude MCP registration 'ai-cli' missing; rerun without --verify to repair."; fi
  _run "claude mcp add -s user ai-cli -- npx -y 'ai-cli-mcp@${AI_CLI_MCP_VERSION}'"
fi
if ! $DRY_RUN; then
  claude mcp list 2>/dev/null | grep -Eq '(^|[[:space:]])ai-cli([[:space:]]|:|$)' \
    || _fail "Claude MCP registration repair did not verify."
  check "claude-mcp:ai-cli:registered"
fi

# Never synthesize consent/auth state. Presence is not authentication.
provider_claude="DEGRADED"
remedy "If Claude workers fail, complete Claude Code's documented interactive login/terms flow, then rerun --verify."
if command -v codex >/dev/null 2>&1; then provider_codex="DEGRADED"; remedy "If Codex workers fail, complete Codex login interactively."; fi

if ! $CORE_ONLY; then
  if command -v openclaw >/dev/null 2>&1; then
    if ! openclaw mcp list 2>/dev/null | grep -q 'ai-cli-mcp' || $FORCE; then
      $VERIFY_ONLY && _fail "OpenClaw ai-cli-mcp registration missing."
      _run "openclaw mcp set ai-cli-mcp '{\"command\":\"npx\",\"args\":[\"-y\",\"ai-cli-mcp@${AI_CLI_MCP_VERSION}\"],\"env\":{\"MCP_CLAUDE_DEBUG\":\"false\"}}'"
    fi
  fi

  if $INCLUDE_GEMINI; then
    provider_gemini="NOT_INSTALLED"
    if ! command -v gemini >/dev/null 2>&1; then
      $VERIFY_ONLY && _fail "Gemini requested but CLI is missing."
      _run "npm install -g @google/gemini-cli"
    fi
    if command -v gemini >/dev/null 2>&1; then
      if gemini auth check >/dev/null 2>&1; then provider_gemini="READY";
      else
        provider_gemini="DEGRADED"; remedy "Run 'gemini auth login' interactively if this optional lane is required."
        if ! $NON_INTERACTIVE && ! $VERIFY_ONLY && ! $DRY_RUN; then
          _log "Gemini auth is not ready; interactive login is intentionally not automatic."
        fi
      fi
    fi
  fi

  if $MIRROR_SKILLS; then
    _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; _SKILLS_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"
    for src in "$_SKILLS_ROOT"/*/SKILL.md "$_SKILLS_ROOT/SKILL.md"; do
      [ -f "$src" ] || continue
      [ "$src" = "$_SKILLS_ROOT/SKILL.md" ] && name="orama-system" || name="$(basename "$(dirname "$src")")"
      for root in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.gemini/skills"; do
        [ -d "$root" ] || continue; mkdir -p "$root/$name"; cmp -s "$src" "$root/$name/SKILL.md" || cp "$src" "$root/$name/SKILL.md"
      done
    done
  fi

  sync_cursor="$(cd "$(dirname "$0")" && pwd)/sync-cursor-mcp.sh"
  [ -f "$sync_cursor" ] && { $VERIFY_ONLY || _run "bash '$sync_cursor'"; }
fi

python3 - "$provider_claude" "$provider_codex" "$provider_gemini" "${checks[*]}" "${remediation[*]}" <<'PY'
import json,sys
print(json.dumps({"core":"READY","provider":{"claude":sys.argv[1],"codex":sys.argv[2],"gemini":sys.argv[3]},"checks":sys.argv[4].split() if sys.argv[4] else [],"remediation":[sys.argv[5]] if sys.argv[5] else []}, separators=(",",":")))
PY
_log "Core ai-cli-mcp readiness complete. Provider auth/consent remains operator-controlled."
