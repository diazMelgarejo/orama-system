---
name: omniroute
description: >
  Optional LAZY SIDECAR for OmniRoute (the local "Unified AI API Proxy" DMG app).
  Covers Claude Code MCP-endpoint config, GUI password reset, and the storage.sqlite
  settings/keys layout. Activates ONLY when OmniRoute is installed/running
  (~/.omniroute or /Applications/OmniRoute.app present); skip entirely if absent.
  Neither required by nor a dependency of any other skill — pure sidecar.
metadata:
  type: reference
  optional: true
  sidecar: true
  verified: 2026-06-14
---

# OmniRoute — lazy sidecar (optional, machine-specific)

> **Activation guard — skip if OmniRoute is absent.** Run first; if it prints SKIP, do nothing else.
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
