---
name: omniroute
description: >
  Optional LAZY SIDECAR for OmniRoute (the local "Unified AI API Proxy" DMG app).
  Covers Claude Code MCP-endpoint config, GUI password reset, storage.sqlite layout,
  and the full verified disable/re-enable runbook. Activates ONLY when OmniRoute is
  installed/running (~/.omniroute or /Applications/OmniRoute.app present); skip entirely
  if absent. Neither required by nor a dependency of any other skill — pure sidecar.
metadata:
  type: reference
  optional: true
  sidecar: true
  verified: 2026-06-14
  status: DISABLED  # set to ENABLED when re-enabled; update probe section accordingly
---

# OmniRoute — lazy sidecar (optional, machine-specific)

## Current Status

> **DISABLED as of 2026-06-14.** Do not probe, start, or route work through OmniRoute.
> Continue on the standard stack (code-review-graph → gbrain → Gemini → ai-cli).
> When no external API is reachable, fall back to Local API Fallback (Ollama → LM Studio).
>
> To re-enable: see **§ Re-enable OmniRoute** below.

---

> **Activation guard — skip if OmniRoute is absent.** Run first; if it prints SKIP, do nothing else.
>
> ```bash
> { [ -d "$HOME/.omniroute" ] || [ -d "/Applications/OmniRoute.app" ]; } \
>   || { echo "OmniRoute not installed — SKIP sidecar"; exit 0; }
> ```

## What it is

- **OmniRoute** = local "Unified AI API Proxy" (multi-provider routing, load-balancing, usage tracking),
  shipped as a macOS **DMG app** (`/Applications/OmniRoute.app`, e.g. v3.8.3) running a bundled Next.js
  **`next-server` on `http://127.0.0.1:20128`**.
- **Data dir `~/.omniroute/`:** `storage.sqlite` (settings + keys + logs), `.env` (`STORAGE_ENCRYPTION_KEY`),
  `cloudflared/` (quick-tunnel that also exposes it at a `*.trycloudflare.com` URL), `db_backups/` (auto
  pre-write snapshots).
- An **older github-clone** install and the **DMG** install can leave stale config behind. Identify the
  *running* one: `lsof -a -p <pid> -d cwd` — cwd under `/Applications/OmniRoute.app/...` = DMG (no separate
  clone running; `~/.omniroute` is just the DMG's data dir, **not** a git checkout).

## Claude Code MCP config (verified 2026-06-14)

- Transport is **`streamable-http`**: `sqlite3 ~/.omniroute/storage.sqlite "SELECT value FROM key_value WHERE key='mcpTransport';"`
- **Correct server entry** (`~/.claude.json` → global `mcpServers.omniroute` or a project scope):

  ```json
  { "type": "http", "url": "http://127.0.0.1:20128/api/mcp/stream",
    "headers": { "Authorization": "Bearer <registered-key>" } }
  ```

- **Gotchas that cause `/doctor` "Unable to connect — Is the computer able to access the url?":**
  - `https://cloud.omniroute.online/...` is **dead (404)** — stale cloud endpoint. Use the **local** URL,
    or the current tunnel from `~/.omniroute/cloudflared/quick-tunnel.log`.
  - `/api/mcp/sse` is **only** for `sse` transport — with `streamable-http` it returns
    `{"error":"MCP transport is set to \"streamable-http\", not \"sse\""}`. Use `/api/mcp/stream`.
  - `/api/mcp` (root) **404s** on POST; `/api/mcp/` **308-redirects**. The endpoint is `/api/mcp/stream`
    (POST; a plain GET returns 400 — that's normal for streamable-http).
  - A **project-scope** `mcpServers.omniroute` overrides the global one. If the project points at the dead
    cloud URL while global points local, the project fails even though global works → harmonize both to
    `http://127.0.0.1:20128/api/mcp/stream`.
  - The Bearer token is a **registered API key** (in `registered_keys`/`api_keys`), not in `.env`; it stays
    valid across app updates as long as the key still exists. "Token not in `.env`" ≠ "token invalid".
  - When debugging, `curl … /api/mcp/stream` with a valid token returns HTTP `000` — that's the SSE stream
    holding open, **not** a failure; unauth returns `401`.

## GUI password reset — PROVEN (sets a SPECIFIC password, live, no restart)

- Login auth is **bcrypt `$2b$12`**, stored JSON-string-encoded at `key_value['password']` in
  `storage.sqlite`. `requireLogin` / `setupComplete` / `hasPassword` live in the same table.
- `Default password: CHANGEME` applies **only** when `INITIAL_PASSWORD` is unset on a *fresh* setup. Once
  set up, it's the user's custom password (hashed → unrecoverable; you can only **reset**).
- **Set it to a known value (verified: login returns HTTP 200 immediately, no app restart):**

  ```bash
  DB="$HOME/.omniroute/storage.sqlite"
  NEWPASS='bd0735'                                            # your desired password
  HASH=$(htpasswd -nbBC 12 x "$NEWPASS" | cut -d: -f2- | sed 's/\$2y\$/\$2b\$/')   # $2y→$2b for compat
  cp "$DB" "$DB.bak-$(date +%Y%m%d-%H%M%S)"                   # always back up first
  printf "PRAGMA busy_timeout=8000;\nUPDATE key_value SET value='\"%s\"' WHERE key='password';\n" "$HASH" | sqlite3 "$DB"
  curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:20128/api/auth/login \
       -H 'Content-Type: application/json' -d "{\"password\":\"$NEWPASS\"}"        # expect 200
  ```

  - **bcrypt source order (use the first available):** `htpasswd -B` (Apache; macOS `/usr/sbin/htpasswd`)
    → any on-disk `bcryptjs` module via `node -e "require('<dir>').hashSync(p,12)"` → `python3 -c 'import bcrypt'`.
    The app's own bcrypt is webpacked in `.next` and **not** `require`-able.
  - Pitfall: piping `htpasswd` output through `cut`/`sed` can silently yield empty if you mis-handle stderr —
    run it raw once to confirm you get `x:$2y$12$…` before writing.
- **Official alternatives:** `npx omniroute reset-password` (stop the server first; interactive prompt); or
  set `INITIAL_PASSWORD` in `~/.omniroute/.env`, clear `key_value['password']`, restart.

## storage.sqlite quick map

- `key_value` — settings KV: `mcpTransport`, `mcpEnabled`, `requireLogin`, `setupComplete`, `password`,
  `apiKeySecret`, `jwtSecret`, plus model/cache/compression flags.
- `registered_keys` / `api_keys` — MCP/API Bearer keys. `command_code_auth_sessions` — OAuth/session state.
- `provider_connections`, `routing_decisions`, `call_logs`, `audit_log`, `mcp_tool_audit` — runtime.
- Always `cp` a backup before any write; the app also keeps `~/.omniroute/db_backups/*_pre-write.sqlite`.

## Parallel-dispatch role (merged from `references/omniroute-lazy-sidecar.md`)

Beyond ops/troubleshooting, OmniRoute's other role is **optional parallel dispatch**: when running,
fan suitable subtasks (review passes, draft generation, A/B model comparisons) to free
OpenRouter/AgentRouter models in parallel. Its tools surface in Claude Code as MCP tools.

**Token from env — never hardcode** (a literal token in a tracked file is a committed secret).
Export `OMNIROUTE_TOKEN` in a gitignored `.env`.

### Probe (run once at session start, silent on any failure)

```bash
_OR_URL="http://127.0.0.1:20128/api/mcp/stream"
_OR_TOK="${OMNIROUTE_TOKEN:-}"        # injected from env/.env; never hardcode a token here
_OMNIROUTE="unavailable"
if [ -n "$_OR_TOK" ] && curl -sf --max-time 2 "$_OR_URL" -H "Authorization: Bearer $_OR_TOK" >/dev/null 2>&1; then
  _OMNIROUTE="running"
elif command -v omniroute >/dev/null 2>&1; then
  omniroute serve --daemon --no-open >/dev/null 2>&1; sleep 1
  [ -n "$_OR_TOK" ] && curl -sf --max-time 2 "$_OR_URL" -H "Authorization: Bearer $_OR_TOK" >/dev/null 2>&1 && _OMNIROUTE="started"
fi
echo "OMNIROUTE: $_OMNIROUTE"
```

### Workflow rule

| `OMNIROUTE` | Action |
|-------------|--------|
| `running` / `started` | Route fan-out subtasks (review passes, drafts, A/B model compares) through OmniRoute MCP tools |
| `unavailable` | Continue on the standard stack (code-review-graph → gbrain → Gemini → ai-cli). Do **not** warn the user. |

### Never

- Install or upgrade OmniRoute inside any setup script or `start.sh`.
- Fail, warn, or degrade visibly when OmniRoute is absent.
- Block on OmniRoute being rate-limited / unreliable; retry at most **once** per session if start fails.
- Hardcode the bearer token in a tracked file — read `$OMNIROUTE_TOKEN` from env.

## Why "lazy sidecar"

Reference-only and machine-specific. It is **not** imported, required, or depended on by any other skill —
keep it out of every skill's hard dependency graph. If OmniRoute isn't installed, the activation guard
exits and nothing runs. Use it if present; skip it if not.

---

## Root Cause: "ConnectionRefused" during compaction (verified 2026-06-14)

When OmniRoute is running it acts as a **local AI routing proxy** — Claude Code's outbound API calls
pass through it. Stopping OmniRoute mid-session leaves live requests pointing at the now-dead local
port → `Error during compaction: API Error: Unable to connect to API (ConnectionRefused)`.

**The persistent cause (verified 2026-06-14) is an `env` block in `~/.claude/settings.json`** that
hard-codes `ANTHROPIC_BASE_URL` to the OmniRoute port (e.g. `http://localhost:20128`) plus an
`ANTHROPIC_AUTH_TOKEN` that is an OmniRoute key, not a real Anthropic key. Once OmniRoute is stopped,
**every** terminal-launched `claude` call — Pro, API, or a local-model backend — hits the dead port
and fails, because this `env` block overrides whatever backend you pick. The Claude **Desktop** app
keeps working because it injects `ANTHROPIC_BASE_URL=https://api.anthropic.com` into its own process
env at launch, overriding settings.json. The **terminal CLI** gets no such injection → it is the one
that breaks. Removing the `env` block (Disable § 1b) is the actual fix; stopping the process is not
enough on its own.

**This is not a network outage.** Verify direct reachability:

```bash
# Expect HTTP 401 (Anthropic server answered — auth required, not refused)
curl -s --max-time 5 -o /dev/null -w "HTTP %{http_code} in %{time_total}s" https://api.anthropic.com/v1/models
```

If you get `000` or `ECONNREFUSED`, OmniRoute (or another local proxy) is still intercepting. Check:

```bash
pgrep -la omniroute cloudflared
lsof -iTCP -sTCP:LISTEN | grep -E "20128|3000|4000|8080"
```

---

## Disable OmniRoute — Full Verified Procedure (2026-06-14)

Run in order. Each step is independent — skip any that was already done.

### 1. Remove from Claude Code MCP config

```bash
# Remove the "omniroute" key from global + all project-scoped mcpServers in ~/.claude.json
python3 - <<'EOF'
import json, os
path = os.path.expanduser('~/.claude.json')
with open(path) as f: d = json.load(f)
removed = d.get('mcpServers', {}).pop('omniroute', None)
for proj in d.get('projects', {}).values():
    proj.get('mcpServers', {}).pop('omniroute', None)
with open(path, 'w') as f: json.dump(d, f, indent=2); f.write('\n')
print("Removed:", removed)
EOF
```

Verify: `claude mcp list | grep -i omni` → should print nothing.

### 1b. Remove the API-routing `env` block — THE actual ConnectionRefused fix

This is the step that actually unblocks the terminal `claude` CLI. The MCP entry (§ 1) is unrelated
to API routing — the routing override lives in `~/.claude/settings.json`'s `env` block.

```bash
# Back up first, then drop the whole OmniRoute env block (base URL + auth token + cc/ model overrides)
cp ~/.claude/settings.json "$HOME/.claude/settings.json.bak-omniroute-$(date +%Y%m%d-%H%M%S)"
python3 - <<'EOF'
import json, os
path = os.path.expanduser('~/.claude/settings.json')
with open(path) as f: d = json.load(f)
removed = d.pop('env', None)   # entire block is OmniRoute wiring; remove all of it
with open(path, 'w') as f: json.dump(d, f, indent=2); f.write('\n')
print("Removed env keys:", list(removed.keys()) if removed else None)
EOF
```

**Why remove the whole block, not just the URL:** the `ANTHROPIC_AUTH_TOKEN` is an OmniRoute key — if
you only fix `ANTHROPIC_BASE_URL` back to `https://api.anthropic.com` but leave that token, the CLI
then 401s against real Anthropic. The `cc/`-prefixed model overrides are also OmniRoute/relay format.
Dropping the whole `env` block restores vanilla OAuth + default endpoint for the terminal CLI; the
Desktop app is unaffected (it injects its own env at launch).

Verify (avoid leaving any dead-port reference):

```bash
grep -n "ANTHROPIC_BASE_URL\|ANTHROPIC_AUTH_TOKEN" ~/.claude/settings.json \
  && echo "STILL PRESENT (bad)" || echo "clean"
curl -s --max-time 6 -o /dev/null -w "HTTP %{http_code}\n" https://api.anthropic.com/v1/models  # expect 401
```

### 2. Remove OmniRoute permission allowlist entries

Edit `$OPENCLAW_ROOT/.claude/settings.local.json` and remove any `omniroute`-keyed
entries from the `permissions.allow` array.

### 3. Mark sidecar docs as temporarily disabled

Update this file's `## Current Status` section (and any SKILL.md that loads OmniRoute
as a sidecar) to show `DISABLED`.

### 4. Stop the running process

```bash
pkill -f "omniroute serve" 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true          # if cloudflared tunnel was running
```

### 5. Permanently disable the LaunchAgent (survives reboots; plist kept for easy restore)

```bash
launchctl disable "gui/$(id -u)/com.omniroute.autostart"
# Confirm:
launchctl print "gui/$(id -u)/com.omniroute.autostart" 2>/dev/null \
  | grep -E "state|disabled" || echo "Not in boot domain — correctly inactive"
```

The plist remains at `~/Library/LaunchAgents/com.omniroute.autostart.plist` for restore.

### 6. Backup

```bash
STAMP=$(date +%Y%m%d-%H%M%S)
DEST="$HOME/claude-config-backups/claude-config-backup-$STAMP"
mkdir -p "$DEST"
cp -r ~/.claude "$DEST/"
cp ~/.claude.json "$DEST/"
cp ~/Library/LaunchAgents/com.omniroute.autostart.plist "$DEST/" 2>/dev/null || true
echo "Backed up to $DEST"
```

---

## Re-enable OmniRoute — Full Verified Procedure

### 1. Start the LaunchAgent

```bash
launchctl enable "gui/$(id -u)/com.omniroute.autostart"
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.omniroute.autostart.plist
sleep 2 && pgrep -la omniroute && echo "Running" || echo "Failed to start"
```

### 2. Restore MCP config

Get the Bearer token from `~/.omniroute/storage.sqlite`:

```bash
sqlite3 ~/.omniroute/storage.sqlite \
  "SELECT value FROM registered_keys LIMIT 3;" 2>/dev/null \
  || sqlite3 ~/.omniroute/storage.sqlite \
  "SELECT value FROM api_keys LIMIT 3;" 2>/dev/null
```

Add back to `~/.claude.json` via:

```bash
claude mcp add-json omniroute \
  '{"type":"http","url":"http://127.0.0.1:20128/api/mcp/stream","headers":{"Authorization":"Bearer <TOKEN>"}}'
```

**Gotchas (all verified 2026-06-14):**

- Use `http://127.0.0.1:20128/api/mcp/stream` — NOT `https://cloud.omniroute.online` (dead/404).
- Transport must be `streamable-http` — verify: `sqlite3 ~/.omniroute/storage.sqlite "SELECT value FROM key_value WHERE key='mcpTransport';"`
- A **project-scoped** `mcpServers.omniroute` overrides the global one — harmonize both to the local URL.
- Bearer token is a **registered API key** in `registered_keys`/`api_keys`, not in `.env`.

### 2b. Restore the API-routing `env` block (only if you want the terminal CLI to route through OmniRoute)

Skip this unless you specifically want the terminal `claude` CLI's API traffic to go through OmniRoute
(the Desktop app routes independently and does not need it). Restore from the backup made in Disable § 1b:

```bash
# List backups; pick the newest:
ls -t ~/.claude/settings.json.bak-omniroute-* 2>/dev/null | head -1
# Then merge its env block back, OR re-add manually with the CURRENT OmniRoute token:
python3 - <<'EOF'
import json, os, glob
path = os.path.expanduser('~/.claude/settings.json')
baks = sorted(glob.glob(os.path.expanduser('~/.claude/settings.json.bak-omniroute-*')), reverse=True)
with open(path) as f: d = json.load(f)
with open(baks[0]) as f: old = json.load(f)
if 'env' in old: d['env'] = old['env']    # confirm ANTHROPIC_AUTH_TOKEN still valid in storage.sqlite
with open(path, 'w') as f: json.dump(d, f, indent=2); f.write('\n')
print("Restored env from", baks[0])
EOF
```

### 3. Re-enable sidecar docs

Update this file's `## Current Status` to `ENABLED` and restore the probe command.
Re-enable any SKILL.md sections that were marked disabled.

### 4. Re-add permission allowlist entries

Restore OmniRoute entries to `$OPENCLAW_ROOT/.claude/settings.local.json`.

### 5. Verify

```bash
pgrep -la omniroute && echo "Process: OK"
curl -s --max-time 5 -o /dev/null -w "HTTP %{http_code}\n" \
  http://127.0.0.1:20128/api/mcp/stream \
  -H "Authorization: Bearer $OMNIROUTE_TOKEN"    # expect HTTP 200 (SSE stream holds) or 400
claude mcp list | grep omni && echo "MCP: OK"
```

---

## Quick Status Check

```bash
pgrep -la omniroute && echo "RUNNING" || echo "NOT running"
launchctl print "gui/$(id -u)/com.omniroute.autostart" 2>/dev/null \
  | grep -E "state|disabled" || echo "Not in boot domain"
claude mcp list | grep -i omni || echo "Not in claude mcp list"
curl -s --max-time 3 -o /dev/null -w "HTTP %{http_code}\n" https://api.anthropic.com/v1/models
# ↑ expect 401 (Anthropic answered directly) — NOT 000 (local proxy still intercepting)
```

**Full off-repo ops reference:** `$OPENCLAW_ROOT/OmniRoute-config.md`
