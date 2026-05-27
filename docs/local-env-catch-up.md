# Local environment catch-up

> **After the 2026-05-23 secret redaction:** `config/mac-orchestrator.json` no longer contains literal API keys or bot tokens. Redacted credential values belong in `.env.local` only (never back into tracked JSON). Your machine must supply them via environment variables (typically `orama-system/.env.local` in this repo, or OpenClaw launcher scripts under `$OPENCLAW_ROOT`).

Use this page when you pulled `main` and channels, gateway auth, or Gemini fallbacks stopped working.

---

## Do this now (5 steps)

1. `cd` to your **orama-system** clone and `git pull origin main`.
2. `cp .env.example .env.local` — edit LAN IPs and paths; **never commit** `.env.local`.
3. Set **`OPENCLAW_ROOT`** to the parent of `orama-system` (see below) and export the four **`OPENCLAW_*`** secrets from the table (rotate if they were ever in git history).
4. `source scripts/env/load-local.sh` (or run `./start.sh` — it sources this automatically).
5. `bash scripts/check-local-env.sh` — fix anything marked `MISSING`.
6. `bash scripts/git/check_identity.sh` && `bash bin/orama-system/scripts/first-run-install.sh status` && `python3 scripts/review/repo_hygiene.py .`

---

## Layout: where files live

| Path | Tracked? | Role |
|------|----------|------|
| `.env.example` | Yes | Template only — no secrets |
| `.env` | No (gitignored) | Optional machine endpoints (portal loads first) |
| `.env.local` | No (gitignored) | **Session secrets** — overrides `.env` |
| `.paths` | No | Generated paths (never commit) |
| `config/mac-orchestrator.json` | Yes | OpenClaw config with `${env:...}` placeholders |
| `~/.orama-system/first-run.json` | No | First-run installer state |

**`OPENCLAW_ROOT`** = directory that **contains** the `orama-system` folder (and usually AlphaClaw, Perpetua-Tools siblings).

Example package layout:

```text
~/…/OpenClaw/                    ← OPENCLAW_ROOT
├── orama-system/                ← this repo (ORAMA_REPO_ROOT)
├── perplexity-api/Perpetua-Tools/
├── AlphaClaw/
└── .mcp.json                    ← MCP_JSON = $OPENCLAW_ROOT/.mcp.json
```

Auto-detection (no export needed if layout matches): `bin/orama-system/scripts/lib/openclaw-env.sh` sets `OPENCLAW_ROOT` to the parent of the git root.

Explicit override:

```bash
export OPENCLAW_ROOT="/absolute/path/to/OpenClaw"
```

---

## Cursor Cloud: do not secret-map loopback

Loopback and bind-all addresses are configuration, not credentials. In
[Cursor Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents), **remove**
host-only secrets (for example legacy `LOCAL_MAC_HOST`) whose value is only a loopback or
bind-all address. If those entries are marked **Redacted**, the commit scanner blocks staged
files containing those strings and agents may litter source with scanner placeholders.

Use `OLLAMA_MAC_ENDPOINT=http://localhost:11434`, the committed `.cursor/environment.json`
defaults, and `*_BIND_LAN=1` when you intentionally need LAN exposure. See
`.cursor/cloud-secrets-guidance.md`.

---

## Copy template → local files

```bash
cd /path/to/orama-system
cp -n .env.example .env.local
# Optional: split non-secrets into .env and keep secrets only in .env.local
source scripts/env/load-local.sh   # .env then .env.local (override)
export OPENCLAW_ROOT="$(git rev-parse --show-toplevel)/.."
bash scripts/check-local-env.sh
```

Fill in:

- Your LAN IPs for Ollama / LM Studio (replace example `192.168.x.x` values).
- `PERPETUA_TOOLS_ROOT` if Perpetua-Tools is not at the default sibling path.
- All **Tier S** variables in the table below.

---

## Environment variable inventory

### Tier S — secrets (`.env.local` only; rotate if ever committed)

| Variable | Purpose | Used in |
|----------|---------|---------|
| `OPENCLAW_TELEGRAM_BOT_TOKEN` | Telegram bot API token | `config/mac-orchestrator.json` → `channels.telegram.botToken` |
| `OPENCLAW_GATEWAY_AUTH_TOKEN` | Gateway LAN auth token | `config/mac-orchestrator.json` → `gateway.auth.token` |
| `OPENCLAW_MODELS_PROVIDERS_GEMINI_MAIN_APIKEY` | Google AI (main Gemini models) | `config/mac-orchestrator.json` → `models.providers.gemini-main.apiKey` |
| `OPENCLAW_MODELS_PROVIDERS_GEMINI_FALLBACK_APIKEY` | Google AI (FALL model aliases) | `config/mac-orchestrator.json` → `models.providers.gemini-fallback.apiKey` |
| `SETUP_PASSWORD` | Portal setup / local bootstrap gate | `.env.example`, `scripts/openclaw_bootstrap.py` |
| `XAI_API_KEY` | Optional Grok fallback | `api_server.py`, `scripts/openclaw_bootstrap.py` |
| `OPENROUTER_API_KEY` | Optional cloud routing | `portal_server.py` dashboard |

**Rotation reminder:** If a Google API key (`AIza…`) or Telegram bot token (`…:…` from @BotFather) ever appeared in a committed file or chat log, **revoke and re-issue** before putting the new value in `.env.local`.

### Tier L — layout & paths

| Variable | Purpose | Used in |
|----------|---------|---------|
| `OPENCLAW_ROOT` / `ORAMA_OPENCLAW_ROOT` | OpenClaw multi-repo parent | `openclaw-env.sh`, `first-run-install.sh`, docs |
| `ORAMA_REPO_ROOT` / `ORAMA_INSTALL_DIR` | This git root | `openclaw-env.sh`, installers |
| `OPENCLAW_MCP_JSON` | Override path to `.mcp.json` | `crg-embed-mode`, `setup-embeddings` |
| `PERPETUA_TOOLS_ROOT` | Perpetua-Tools checkout | `api_server.py`, `portal_server.py`, `openclaw-env.sh` |
| `PERPETUATOOLSROOT` | Legacy alias for PT root | `api_server.py`, `bin/agents/dispatcher.py` |
| `ORAMA_STATE_DIR` | Override `~/.orama-system` | `first-run-install.sh` |

### Tier H — hardware & endpoints (`.env` or `.env.local`)

| Variable | Purpose | Used in |
|----------|---------|---------|
| `OLLAMA_MAC_ENDPOINT` | Mac Ollama API | `portal_server.py`, `spawn_agents.py`, `.env.example` |
| `OLLAMA_WINDOWS_ENDPOINT` | Win Ollama API | `portal_server.py`, bootstrap scripts |
| `LM_STUDIO_MAC_ENDPOINT` | Mac LM Studio | `portal_server.py`, `api_server.py` |
| `LM_STUDIO_WIN_ENDPOINTS` | Win LM Studio pool (comma-sep) | `portal_server.py`, `api_server.py`, tests |
| `WIN_LM_STUDIO_HOST` | Win host for URL build | `api_server.py` |
| `LM_STUDIO_API_TOKEN` | LM Studio API key | `portal_server.py`, spawn scripts |
| `ORCHESTRATOR_ENDPOINT` | Perpetua-Tools orchestrator URL | `portal_server.py` |
| `ULTRATHINK_ENDPOINT` / `ULTRATHINK_PORT` / `ULTRATHINK_HOST` | orama API server | `portal_server.py`, `api_server.py` |
| `PORTAL_HOST` / `PORTAL_PORT` | Operator portal | `portal_server.py` |
| `DEFAULT_MODEL` / `FAST_MODEL` / `CODE_MODEL` | Model names | `api_server.py`, `.env.example` |

### Tier O — OpenClaw runtime overrides

| Variable | Purpose | Used in |
|----------|---------|---------|
| `OPENCLAW_GATEWAY` | Gateway base URL for MCP bridge | `bin/mcp_servers/openclaw_bridge.py` |
| `OPENCLAW_GATEWAY_URL` | Discovered gateway URL | `openclaw_bootstrap.py`, wiki gateway discovery |
| `OPENCLAW_GATEWAY_PORT` | Gateway listen port (default 18789) | `openclaw_bootstrap.py` |
| `OPENCLAW_TIMEOUT` | HTTP timeout for bridge | `openclaw_bridge.py` |
| `ORAMA_PLATFORM` | `mac` \| `windows` for routing tests | `api_server.py`, tests |
| `ORAMA_BACKEND_PRIORITY` | `local` \| `cloud` \| `windows` | `api_server.py` |

### Tier M — MCP / Codex / optional

| Variable | Purpose | Used in |
|----------|---------|---------|
| `CODEX_GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP for Codex | `docs/wiki/11-codex-github-mcp-config.md` |
| `OMNIROUTE_TOKEN` | Optional OmniRoute sidecar | `first-run-install.sh` (probe only) |
| `NVM_NODE_BIN` | Preferred Node 22+ path | `first-run-install.md`, installer |

Naming convention for new OpenClaw secrets: `OPENCLAW_<SERVICE>_<DETAIL>` (uppercase, underscores). See `bin/orama-system/skills/openclaw-skills/SKILL.md`.

---

## Where secrets are loaded (OpenClaw vs orama)

| Layer | How env reaches the gateway |
|-------|---------------------------|
| **orama-system** | `scripts/env/load-local.sh`, `start.sh`, `portal_server.py`, `api_server.py` — `.env` then `.env.local` |
| **OpenClaw gateway** | macOS LaunchAgent / `start-*.sh` / `openclaw-secrets.sh` under `$OPENCLAW_ROOT` (not in this repo) |
| **mac-orchestrator.json** | `${env:VAR}` substitution at runtime — vars must be in the **gateway process environment** |

After editing `.env.local`, restart the OpenClaw gateway (LaunchAgent or `openclaw` CLI) so Telegram and Gemini providers pick up new values.

---

## Verification commands

```bash
# Git commit identity (approved: cyre + Lawrence@cyre.me or diazMelgarejo@gmail.com, or Codex)
bash scripts/git/check_identity.sh

# Env var checklist (this repo)
bash scripts/check-local-env.sh

# Toolchain bootstrap state (fast)
bash bin/orama-system/scripts/first-run-install.sh status

# Full bootstrap / heal
bash bin/orama-system/scripts/first-run-install.sh run

# Repo hygiene (secrets, paths, links)
python3 scripts/review/repo_hygiene.py .

# Optional: MCP workers (separate from first-run)
bash bin/orama-system/scripts/install-mcp-stack.sh
```

---

## gbrain: `getaddrinfo ENOTFOUND` (Cursor agents / sandboxes)

**Symptom:** `gbrain search`, `gbrain query`, or `gbrain code-def` fail inside a Cursor subagent or sandbox with `getaddrinfo ENOTFOUND`, while the same command works in a normal Terminal on the Mac (host shell **PASS** as of 2026-05-25).

**Why it happens:**

| Cause | What to check |
|-------|----------------|
| **Sandbox network** | Cursor agent sandboxes may block outbound DNS/TCP to the host in `~/.gbrain/config.json` (common with Supabase `*.supabase.co` URLs). |
| **Wrong backend URL** | Stale `database_url` / `DATABASE_URL` after machine migration or mode switch (local PGLite vs remote Postgres). |
| **Host not running** | Local Postgres hostname in config but server not up (less common than ENOTFOUND — often `ECONNREFUSED` instead). |

**Diagnose (run in the same environment that fails — agent terminal vs Mac Terminal):**

```bash
command -v gbrain && gbrain --version
gbrain search "first-run" 2>&1 | head -5
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home() / ".gbrain" / "config.json"
if p.exists():
    c = json.loads(p.read_text())
    url = c.get("database_url") or c.get("DATABASE_URL") or ""
    # redact credentials in output
    if "@" in url:
        url = url.split("@", 1)[1]
    print("config host:", url.split("/")[0] if url else "(empty)")
else:
    print("missing:", p)
PY
```

**Fixes (pick what matches your setup):**

1. **Host-only workflow (recommended for agents):** Run `gbrain` from your Mac Terminal for sync and heavy queries; in agents use **CRG MCP first** (`detect_changes_tool`, `query_graph_tool`), then **Grep** for exact strings. See [`bin/orama-system/skills/code-review/references/tool-chain.md`](../bin/orama-system/skills/code-review/references/tool-chain.md).
2. **Re-bootstrap gbrain:** `/setup-gbrain` or `bash bin/orama-system/scripts/first-run-install.sh run` — ensures `~/.gbrain/config.json` mode `0600` and embedding model aligned with CRG (`ollama:bge-m3`).
3. **Local brain instead of remote:** If Supabase is blocked in sandboxes, prefer **local-stdio / PGLite** per [`bin/orama-system/mcp-install/references/setup-gbrain.md`](../bin/orama-system/mcp-install/references/setup-gbrain.md) so agents hit loopback, not cloud DNS.
4. **Cursor permissions:** When the agent must call cloud gbrain, retry the tool invocation with **full network** (or run the query in a non-sandbox shell) — do not paste `config.json` contents into chat.
5. **Worktree pin:** Ensure `.gbrain-source` exists in the repo root (gitignored) after `/sync-gbrain`; wrong source name does not cause ENOTFOUND but breaks empty search results.

**Code-review fallback when gbrain is down:** Skip Phase B gbrain steps; continue `list_graph_stats_tool` → `detect_changes_tool` → `get_review_context_tool` → scoped `Read`. Document the skip in the review note.

**Never commit:** `~/.gbrain/config.json`, `.gbrain-source`, or any literal `DATABASE_URL` in tracked files.

---

## Open TODOs (environment)

- [x] **gbrain** `getaddrinfo ENOTFOUND` — documented above (host shell PASS 2026-05-25; sandboxes may still fail until local brain or network policy fixed)
- [x] **CRG MCP in Cursor** — `cursor-mcp.stack.json` + `bash bin/orama-system/scripts/sync-cursor-mcp.sh` → `.cursor/mcp.json` (CRG + ai-cli-mcp); reload MCP after pull. Until reload, use CLI: `uvx code-review-graph status --repo "$ORAMA_REPO_ROOT"` (see [`mcp-tools-crg.md`](../../bin/orama-system/skills/code-review/references/mcp-tools-crg.md) § CLI fallback)

---

## Related docs

- [Agent first-open visibility map](reference/agent-first-open-visibility.md)
- [First-run through code review (E2E how-to)](how-to/first-run-and-code-review.md)
- [First-run install reference](../bin/orama-system/references/first-run-install.md)
- [OpenClaw setup (mirror)](openclaw-setup.md)
- [Git hygiene wiki](wiki/08-git-hygiene-and-branching.md)
- [Gateway discovery](wiki/04-gateway-discovery.md)
- Path helpers: `bin/orama-system/scripts/lib/openclaw-env.sh`
