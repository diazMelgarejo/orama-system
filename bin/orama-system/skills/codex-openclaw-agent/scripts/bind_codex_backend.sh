#!/usr/bin/env bash
# bind_codex_backend.sh
# Opportunistic fail-forward resolver that wires OpenClaw's codex-agent to
# Codex CLI / GPT-5.5. Safe to re-run (idempotent).
#
# Usage:
#   bash bind_codex_backend.sh [--effort medium|high] [--dry-run] [--force]
#
# What this script NEVER does:
#   - Modify agents.defaults.model.primary  (ollama/qwen3.5:9b-nvfp4)
#   - Modify the main or coder agent entries
#   - Write any literal API key into any file
#   - Touch the LaunchAgent plist
#
# Security: auth is referenced by env var name ($CODEX_API_KEY_REF), not
# by value. The OpenClaw runtime resolves the env var at connection time.

set -euo pipefail

# ── args ────────────────────────────────────────────────────────────────────
EFFORT="${EFFORT:-high}"
DRY_RUN="${DRY_RUN:-false}"
FORCE="${FORCE:-false}"
while [[ $# -gt 0 ]]; do
    case $1 in
        --effort)   EFFORT="$2"; shift 2 ;;
        --dry-run)  DRY_RUN="true"; shift ;;
        --force)    FORCE="true"; shift ;;
        *)          echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

# ── paths ───────────────────────────────────────────────────────────────────
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME}"
OC_JSON="$OPENCLAW_HOME/.openclaw/openclaw.json"
LOCK_FILE="$OPENCLAW_HOME/.openclaw/.codex-bind.lock"
CODEX_CONFIG="$HOME/.codex/config.toml"
CODEX_STATE="$HOME/.codex/.app-server-state-reconciled-v1"
CODEX_PORT=61234

log()  { echo "[codex-bind] $*"; }
warn() { echo "[codex-bind] WARN: $*" >&2; }
fail() { echo "[codex-bind] FAIL: $*" >&2; exit 1; }

dry_check() {
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY-RUN: would $*"
        return 1   # callers: check return code before executing
    fi
    return 0
}

# ── pre-flight ───────────────────────────────────────────────────────────────
command -v jq >/dev/null 2>&1 || fail "jq is required but not installed"
command -v openclaw >/dev/null 2>&1 || fail "openclaw CLI not found"
[ -f "$OC_JSON" ] || fail "openclaw.json not found at $OC_JSON"

# ── acquire lock (skip in dry-run) ──────────────────────────────────────────
if [ "$DRY_RUN" = "false" ]; then
    exec 9>"$LOCK_FILE"
    flock -w 10 9 || fail "Could not acquire lock $LOCK_FILE — another bind may be running"
fi

# ── backup ──────────────────────────────────────────────────────────────────
OC_JSON_BAK="$OC_JSON.bak"
if dry_check "cp $OC_JSON $OC_JSON_BAK"; then
    cp "$OC_JSON" "$OC_JSON_BAK"
    log "Backup: $OC_JSON_BAK"
fi

# ── invariant snapshot (before any mutation) ─────────────────────────────────
ORIG_DEFAULT=$(jq -r '.agents.defaults.model.primary // empty' "$OC_JSON")
ORIG_MAIN=$(jq -r '.agents.list[] | select(.id=="main") | .model.primary // empty' "$OC_JSON")
ORIG_CODER=$(jq -r '.agents.list[] | select(.id=="coder") | .model.primary // empty' "$OC_JSON")

# ── (a) PROBE ────────────────────────────────────────────────────────────────
if [ "$FORCE" = "false" ]; then
    log "Step (a): probe"

    command -v codex >/dev/null 2>&1 || fail "Codex CLI not found — install with: npm install -g @openai/codex"

    # Auth check: accept Codex's real auth surfaces, never print values.
    if [ -n "${CODEX_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ] || [ -f "$HOME/.codex/auth.json" ]; then
        log "Codex auth reference found"
    elif [ -f "$CODEX_CONFIG" ]; then
        python3 - <<'PYEOF'
import sys, pathlib
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("WARN: no tomllib/tomli — skipping config.toml structure check", file=sys.stderr)
        sys.exit(0)
p = pathlib.Path.home() / ".codex" / "config.toml"
d = tomllib.loads(p.read_text())
auth_keys = [k for k in d if any(s in k.lower() for s in ("key","token","auth","secret"))]
if not auth_keys:
    print("WARN: no auth key found in ~/.codex/config.toml", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PYEOF
    else
        fail "Codex auth not found — run: codex login"
    fi

    PLUGIN_PRESENT=1
    openclaw plugins list 2>/dev/null | grep -q "openclaw-codex-app-server" && PLUGIN_PRESENT=0

    APPSERVER_UP=1
    curl -sf --max-time 2 "http://127.0.0.1:${CODEX_PORT}/v1/models" >/dev/null 2>&1 \
        && APPSERVER_UP=0

    # Stale state file guard
    if [ -f "$CODEX_STATE" ] && [ "$APPSERVER_UP" -ne 0 ]; then
        warn "Stale app-server state file detected — server is not actually running"
        APPSERVER_UP=1
    fi
else
    log "Step (a): skipped (--force)"
    PLUGIN_PRESENT=1
    APPSERVER_UP=1
fi

# ── (c) IDEMPOTENT INSTALL (if plugin absent) ────────────────────────────────
if [ "$PLUGIN_PRESENT" -ne 0 ]; then
    log "Step (c): plugin absent — attempting install"
    if dry_check "openclaw plugins install openclaw-codex-app-server"; then
        if openclaw plugins install openclaw-codex-app-server; then
            PLUGIN_PRESENT=0
            # Start app-server now that plugin is ready
            codex serve --port "$CODEX_PORT" --background 2>/dev/null || true
            sleep 3
            curl -sf --max-time 2 "http://127.0.0.1:${CODEX_PORT}/v1/models" >/dev/null 2>&1 \
                && APPSERVER_UP=0
        else
            warn "Plugin install failed — falling through to fallback (d)"
        fi
    fi
fi

# ── (b) PRIMARY path ─────────────────────────────────────────────────────────
BINDING_PATH=""
if [ "$PLUGIN_PRESENT" -eq 0 ] && [ "$APPSERVER_UP" -eq 0 ]; then
    log "Step (b): primary — native openclaw-codex-app-server plugin"
    if dry_check "openclaw onboard + /cas_resume + openclaw.json patch (primary)"; then
        openclaw onboard --auth-choice openai-codex 2>/dev/null || warn "onboard returned non-zero — continuing"
        openclaw /cas_resume 2>/dev/null || warn "/cas_resume returned non-zero — continuing"
        BINDING_PATH="primary"
    else
        BINDING_PATH="dry-run-primary"
    fi
fi

# ── (d) FALLBACK — direct OpenAI-compatible provider registration ─────────────
if [ -z "$BINDING_PATH" ]; then
    log "Step (d): fallback — register codex app-server as openai-completions provider"

    # Start codex serve if not already up
    if [ "$APPSERVER_UP" -ne 0 ]; then
        log "Starting codex serve on port $CODEX_PORT"
        if dry_check "codex serve --port $CODEX_PORT --background"; then
            codex serve --port "$CODEX_PORT" --background 2>/dev/null || true
            sleep 3
            curl -sf --max-time 3 "http://127.0.0.1:${CODEX_PORT}/v1/models" >/dev/null 2>&1 \
                || fail "codex serve did not start on port $CODEX_PORT"
        fi
    fi

    BINDING_PATH="fallback"
fi

# ── Register codex provider in openclaw.json ─────────────────────────────────
log "Registering codex provider in openclaw.json"
PROVIDER_PATCH=$(cat <<JSONEOF
{
  "api": "openai-completions",
  "apiKey": "\${CODEX_API_KEY_REF}",
  "baseUrl": "http://127.0.0.1:${CODEX_PORT}/v1",
  "models": [
    {
      "id": "gpt-5.5",
      "name": "Codex — GPT-5.5",
      "contextWindow": 200000,
      "cost": { "input": 0, "output": 0 }
    }
  ]
}
JSONEOF
)

AGENT_PATCH=$(cat <<JSONEOF
{
  "id": "codex-agent",
  "name": "Codex Agent (GPT-5.5)",
  "mode": "sub-agent",
  "model": {
    "primary": "codex/gpt-5.5",
    "reasoning_effort": "${EFFORT}",
    "fallbacks": []
  },
  "tools": {
    "profile": "coding"
  },
  "workspace": "\${HOME}/.openclaw/agents/codex-agent"
}
JSONEOF
)

if dry_check "write codex provider + codex-agent to openclaw.json"; then
    # Atomic write via tmp file
    jq \
        --argjson provider "$PROVIDER_PATCH" \
        --argjson agent "$AGENT_PATCH" \
        '
        .models.providers.codex = $provider |
        if (.agents.list // [] | map(.id) | index("codex-agent")) then
            (.agents.list[] | select(.id == "codex-agent")) |= . + $agent
        else
            .agents.list = (.agents.list // []) + [$agent]
        end
        ' \
        "$OC_JSON" > "$OC_JSON.tmp"
    mv "$OC_JSON.tmp" "$OC_JSON"
    log "openclaw.json updated"
fi

# ── Write directive files into the runtime OpenClaw home ─────────────────────
log "Creating directive files for codex-agent"
AGENT_DIR="$OPENCLAW_HOME/.openclaw/agents/codex-agent"

if dry_check "mkdir + write directive files for $AGENT_DIR"; then
    mkdir -p "$AGENT_DIR/memory/archives" "$AGENT_DIR/scripts/lib"

    # Six required directive files — write scaffold only if not already present
    for directive in SOUL IDENTITY USER AGENTS TOOLS SECURITY; do
        target="$AGENT_DIR/${directive}.md"
        [ -f "$target" ] && continue
        cat > "$target" <<MDEOF
# ${directive}

## Pending
Populate this file for agent: codex-agent
MDEOF
    done

    # IDENTITY is always written (canonical values)
    cat > "$AGENT_DIR/IDENTITY.md" <<MDEOF
# IDENTITY

- Agent ID: codex-agent
- Display Name: Codex Agent (GPT-5.5)
- Primary Model: codex/gpt-5.5
- Reasoning Effort: ${EFFORT}
- Backend: OpenAI Codex CLI (explicit sub-agent only — not default routing)
- Scope: Invoked via \`openclaw run codex-agent\` only
MDEOF

    # SECURITY scaffold — operator fills sandboxing / approval policies
    cat > "$AGENT_DIR/SECURITY.md" <<MDEOF
# SECURITY

## Operator-defined — fill before production use

### Sandbox policy
<!-- Set to: none | sandbox | strict-sandbox -->
sandbox: sandbox

### Approval mode
<!-- Set to: auto | ask | manual -->
approval_mode: ask

### Auth reference
- Codex auth: \`~/.codex/config.toml\` (by path only — no keys copied here)
- OpenClaw gateway auth: \`${OPENCLAW_HOME}/.openclaw/openclaw.json\` gateway.auth

### Execution policy
- File edits: require approval
- Command execution: require approval
- Commits: require approval

### Invariants (never modify without explicit operator decision)
- This agent never becomes the OpenClaw default
- agents.defaults.model.primary is unchanged (ollama/qwen3.5:9b-nvfp4)
MDEOF
fi

# ── Write ~/.codex/config.toml (merge-safe) ──────────────────────────────────
log "Merging model config into ~/.codex/config.toml"
if dry_check "write model = gpt-5.5 to $CODEX_CONFIG"; then
    if [ -f "$CODEX_CONFIG" ]; then
        # Remove existing model / model_reasoning_effort lines, re-add at end
        TMP=$(mktemp)
        grep -v -E '^model\s*=' "$CODEX_CONFIG" \
            | grep -v -E '^model_reasoning_effort\s*=' > "$TMP" || true
        {
            cat "$TMP"
            echo ""
            echo "# Managed by codex-openclaw-agent (orama-system)"
            echo "model = \"gpt-5.5\""
            echo "model_reasoning_effort = \"${EFFORT}\""
        } > "$CODEX_CONFIG"
        rm "$TMP"
    else
        mkdir -p "$(dirname "$CODEX_CONFIG")"
        cat > "$CODEX_CONFIG" <<TOMLEOF
# Managed by codex-openclaw-agent (orama-system)
# Auth: credentials referenced by path only — do not paste API keys here.
model = "gpt-5.5"
model_reasoning_effort = "${EFFORT}"
TOMLEOF
    fi
    log "~/.codex/config.toml updated"
fi

# ── Sub-agent parent binding (main agent can call codex-agent) ───────────────
if dry_check "wire codex-agent into agents.bindings.main.allowAgents"; then
    jq '
        (.agents.bindings //= {}) |
        (.agents.bindings.main //= {}) |
        (.agents.bindings.main.allowAgents //= []) |
        if (.agents.bindings.main.allowAgents | index("codex-agent")) then .
        else .agents.bindings.main.allowAgents += ["codex-agent"] end
    ' "$OC_JSON" > "$OC_JSON.tmp" && mv "$OC_JSON.tmp" "$OC_JSON"
fi

# ── Restart ──────────────────────────────────────────────────────────────────
if dry_check "openclaw restart"; then
    rm -f ~/.openclaw/cron/jobs.json 2>/dev/null || true
    openclaw restart 2>/dev/null || warn "openclaw restart returned non-zero"
    sleep 2
fi

# ── (e) VERIFY ───────────────────────────────────────────────────────────────
log "Step (e): verify backend identity"
if [ "$DRY_RUN" = "false" ]; then
    IDENTITY=$(timeout 60 openclaw run codex-agent \
        --task "reply with exactly: CODEX_BACKEND_OK" \
        --no-save 2>&1 || true)

    if echo "$IDENTITY" | grep -q "CODEX_BACKEND_OK"; then
        log "VERIFY OK — codex-agent confirmed on GPT-5.5/Codex backend"
    else
        warn "VERIFY FAIL — expected CODEX_BACKEND_OK, got: $IDENTITY"
        warn "Restoring backup"
        cp "$OC_JSON_BAK" "$OC_JSON"
        fail "Backend identity verification failed — openclaw.json rolled back"
    fi
else
    log "DRY-RUN: skipping live verify"
fi

# ── Invariant check ──────────────────────────────────────────────────────────
FINAL_DEFAULT=$(jq -r '.agents.defaults.model.primary // empty' "$OC_JSON")
FINAL_MAIN=$(jq -r '.agents.list[] | select(.id=="main") | .model.primary // empty' "$OC_JSON")
FINAL_CODER=$(jq -r '.agents.list[] | select(.id=="coder") | .model.primary // empty' "$OC_JSON")

if [ "$FINAL_DEFAULT" != "$ORIG_DEFAULT" ] || \
   [ "$FINAL_MAIN" != "$ORIG_MAIN" ] || \
   [ "$FINAL_CODER" != "$ORIG_CODER" ]; then
    warn "INVARIANT VIOLATION — routing defaults were mutated. Rolling back."
    cp "$OC_JSON_BAK" "$OC_JSON"
    fail "Invariant check failed. Diff:
  defaults: $ORIG_DEFAULT -> $FINAL_DEFAULT
  main:     $ORIG_MAIN -> $FINAL_MAIN
  coder:    $ORIG_CODER -> $FINAL_CODER"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
log "Done."
echo "{\"status\":\"ok\",\"agent_id\":\"codex-agent\",\"backend\":\"codex/gpt-5.5\",\"effort\":\"${EFFORT}\",\"binding_path\":\"${BINDING_PATH}\",\"dry_run\":${DRY_RUN}}"
