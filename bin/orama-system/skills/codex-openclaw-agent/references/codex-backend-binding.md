# Codex Backend Binding Reference

**Skill:** `codex-openclaw-agent`
**Purpose:** Documents the opportunistic fail-forward resolver that binds
OpenClaw's `codex-agent` to the Codex CLI / GPT-5.5 backend.

---

## Preserved routing (invariants — binding must not touch these)

```
agents.defaults.model.primary  =  ollama/qwen3.5:9b-nvfp4      ← LaunchAgent default
agents.list[id=main].model.primary  =  lmstudio-mac/qwen3.5-9b-mlx
agents.list[id=coder].model.primary =  lmstudio-win/qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2
```

The LaunchAgent plist (`ai.openclaw.gateway`) is **never modified** by this
skill. If any of the three routing invariants above are absent after the
binding script exits, it is an error.

---

## Resolver ladder (steps a → e, in order)

### (a) PROBE — read-only, no mutation

```bash
# 1. Is Codex CLI installed?
command -v codex >/dev/null 2>&1

# 2. Is the user authed with Codex?
#    Read structure of ~/.codex/config.toml without printing values.
python3 -c "
import tomllib, pathlib, sys
p = pathlib.Path.home() / '.codex' / 'config.toml'
if not p.exists():
    sys.exit(1)
d = tomllib.loads(p.read_text())
sys.exit(0 if ('openai_api_key' in d or 'api_key' in d or 'auth' in d) else 1)
"

# 3. Is the openclaw-codex-app-server plugin present?
openclaw plugins list 2>/dev/null | grep -q "openclaw-codex-app-server"
PLUGIN_PRESENT=$?   # 0=yes, 1=no

# 4. Is the codex app-server endpoint reachable?
#    Codex exposes an OpenAI-compatible server at 127.0.0.1:61234 when
#    running in app-server mode. Probe without starting it.
curl -sf --max-time 2 "http://127.0.0.1:61234/v1/models" >/dev/null 2>&1
APPSERVER_UP=$?     # 0=yes, 1=no

# 5. Is a stale app-server state file present?
#    Existence alone is NOT proof the server is running — always use the
#    health check above, not this file.
[ -f ~/.codex/.app-server-state-reconciled-v1 ]
```

**Probe false-positive guard:** the state file can survive a crash.
Only `APPSERVER_UP=0` (live HTTP response) confirms the app-server is running.
If the state file exists but the health check fails, log a warning and
proceed to step (b) as if the server is down.

---

### (b) PRIMARY path — native plugin

Requires: `PLUGIN_PRESENT=0` AND `APPSERVER_UP=0`.

```bash
# Onboard codex as the auth choice
openclaw onboard --auth-choice openai-codex

# Resume / bind the Codex app-server session
openclaw /cas_resume

# Set codex-agent's primary model in openclaw.json
jq '
  (.agents.list[] | select(.id == "codex-agent")).model.primary = "codex/gpt-5.5" |
  (.agents.list[] | select(.id == "codex-agent")).model.reasoning_effort = "'${EFFORT:-high}'"
' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
```

---

### (c) IDEMPOTENT INSTALL — plugin absent but installable

Requires: `PLUGIN_PRESENT=1` AND the openclaw plugin registry is reachable.

```bash
# Check-then-install — safe to re-run
if ! openclaw plugins list 2>/dev/null | grep -q "openclaw-codex-app-server"; then
    openclaw plugins install openclaw-codex-app-server
fi
# Then retry step (b)
```

If installation fails (registry down, auth error), fall through to step (d).

---

### (d) FALLBACK — register codex app-server as OpenAI-compatible provider

Used when: plugin unavailable OR app-server unreachable even after install.

The Codex CLI exposes an OpenAI-compatible HTTP server on
`http://127.0.0.1:61234/v1` when started with `codex serve` (or the daemon
background mode). This fallback registers it as a named provider directly in
`openclaw.json` without requiring the plugin.

```bash
# Start codex in daemon/serve mode if not already running
if ! curl -sf --max-time 2 "http://127.0.0.1:61234/v1/models" >/dev/null 2>&1; then
    codex serve --port 61234 --background
    sleep 3
fi

# Register the provider in openclaw.json
jq '
  .models.providers.codex = {
    "api": "openai-completions",
    "apiKey": "${CODEX_API_KEY_REF}",
    "baseUrl": "http://127.0.0.1:61234/v1",
    "models": [
      {
        "id": "gpt-5.5",
        "name": "Codex — GPT-5.5",
        "contextWindow": 200000,
        "cost": { "input": 0, "output": 0 }
      }
    ]
  }
' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
```

**Security note:** `apiKey` is referenced via the shell env var
`$CODEX_API_KEY_REF` which the OpenClaw runtime resolves from your shell
environment (set by `~/.codex/config.toml` loader). The key is **never
copied into the JSON file as a literal string**.

---

### (e) VERIFY — assert backend identity

This step runs after either (b) or (d) succeeds, before declaring the
binding complete.

```bash
# Run a zero-side-effect probe task and capture the backend in use
IDENTITY=$(openclaw run codex-agent --task "reply with exactly: CODEX_BACKEND_OK" \
    --no-save --timeout 60 2>&1)

if echo "$IDENTITY" | grep -q "CODEX_BACKEND_OK"; then
    echo "VERIFY OK: codex-agent is live on GPT-5.5/Codex backend"
else
    echo "VERIFY FAIL: expected CODEX_BACKEND_OK, got: $IDENTITY" >&2
    exit 1
fi

# Confirm ollama was NOT used (belt-and-suspenders)
if openclaw status --json 2>/dev/null | jq -e \
    '.agents[] | select(.id=="codex-agent") | .model.last_used' \
    | grep -q "ollama"; then
    echo "VERIFY FAIL: codex-agent routed through ollama" >&2
    exit 1
fi
```

---

## Provider entry shape (for `~/.openclaw/openclaw.json`)

```json
"codex": {
  "api": "openai-completions",
  "apiKey": "${CODEX_API_KEY_REF}",
  "baseUrl": "http://127.0.0.1:61234/v1",
  "models": [
    {
      "id": "gpt-5.5",
      "name": "Codex — GPT-5.5",
      "contextWindow": 200000,
      "cost": { "input": 0, "output": 0 }
    }
  ]
}
```

---

## Agent entry shape (for `openclaw.json` `agents.list`)

```json
{
  "id": "codex-agent",
  "name": "Codex Agent (GPT-5.5)",
  "mode": "sub-agent",
  "model": {
    "primary": "codex/gpt-5.5",
    "reasoning_effort": "high",
    "fallbacks": []
  },
  "tools": {
    "profile": "coding"
  },
  "workspace": "${HOME}/.openclaw/agents/codex-agent"
}
```

**No fallback to Ollama or LM Studio** — if Codex is down, the agent
fails loudly rather than silently routing through the default.

---

## `~/.codex/config.toml` merge target

```toml
# Managed by codex-openclaw-agent (orama-system)
# Auth: credentials referenced from ~/.codex/ by path only.
# Do not paste API keys here.
model = "gpt-5.5"
model_reasoning_effort = "high"
```

The script merges only the `model` and `model_reasoning_effort` keys,
leaving all existing auth and provider config untouched.

---

## Invariant check (run after every binding)

```bash
# These three lines must NOT have changed.
jq -r '.agents.defaults.model.primary' openclaw.json | grep -q "ollama/qwen3.5:9b-nvfp4"
jq -r '.agents.list[] | select(.id=="main") | .model.primary' openclaw.json \
    | grep -q "lmstudio-mac/"
jq -r '.agents.list[] | select(.id=="coder") | .model.primary' openclaw.json \
    | grep -q "lmstudio-win/"
echo "Invariants OK"
```

If any invariant fails: roll back `openclaw.json.bak`, log the diff, and
exit non-zero.

---

## Known edge cases and mitigations

| Edge case | Mitigation |
|---|---|
| Stale `.app-server-state-reconciled-v1` after crash | Always use live health check; log warning if file exists but ping fails |
| Plugin present but broken (install incomplete) | Probe includes `openclaw plugins verify openclaw-codex-app-server`; broken → fall to (d) |
| Concurrent regen / race on `openclaw.json` | Script acquires `~/.openclaw/.codex-bind.lock` (flock) before any write |
| Partial write (power loss mid-jq) | Write to `.tmp`, atomic `mv`; backup saved as `openclaw.json.bak` before any mutation |
| `codex serve` port 61234 already in use | Check PID of port first; if not codex process, use 61235 and update provider `baseUrl` accordingly |
| `--force` flag | Skips probe step (a); runs (c) + (b) unconditionally; still runs verify |
| `--dry-run` flag | Prints all planned `jq` mutations and `openclaw.json` diffs without writing |

---

*See `scripts/bind_codex_backend.sh` for the executable version of this ladder.*
