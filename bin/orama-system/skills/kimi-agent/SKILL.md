---
name: kimi-agent
description: >-
  Install, configure, and operate the Kimi Code CLI (`kimi`) for fanning out
  light/parallel tasks alongside the main orchestration session, and for
  monitoring its background server and session logs. Cross-platform installer
  (Moonshot AI); this skill documents the macOS/Linux path verified live on
  2026-07-10 (darwin-arm64, v0.23.4). Windows path is unverified — probe with
  the install script's PowerShell equivalent before relying on it there.
version: 1.0.0
license: Apache 2.0
compatibility: darwin, linux, orama-system, openclaw, hermes-harness
parent_skill: orama-system
triggers:
  - kimi
  - kimi code
  - kimi-code
  - kimi cli
  - fan out to kimi
  - moonshot kimi
allowed-tools: bash, file-operations
---

# Kimi Code Agent Skill

## Disambiguation

**`kimi`** (`~/.kimi-code/bin/kimi`) is Moonshot AI's Kimi Code CLI — a
standalone agentic coding tool in the same category as `cursor-agent`,
`codex`, and `gemini-cli`: a fan-out worker the main session can dispatch
light/parallel tasks to, NOT an internal oramasys stage worker (does not
belong in `bin/config/agent_registry.json`, which is reserved for
SOUL-file-backed OpenClaw/oramasys agents bound to a gateway provider).

| Command | Binary | What it is |
|---------|--------|------------|
| `kimi` | `~/.kimi-code/bin/kimi` | Moonshot Kimi Code CLI — use this |
| `cursor-agent` | `~/.local/bin/cursor-agent` | Cursor's background agent — separate product, see `../cursor-agent/SKILL.md` |

## Install

### macOS / Linux (verified 2026-07-10, darwin-arm64, v0.23.4)

```bash
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
# Installs to ~/.kimi-code/bin/kimi; appends PATH entry to ~/.zshrc (or ~/.bashrc)
# New shells pick it up automatically; in an existing shell:
export PATH="$HOME/.kimi-code/bin:$PATH"
```

Verify:

```bash
kimi --version    # e.g. 0.23.4
kimi doctor       # validates config.toml / tui.toml — SKIP is fine on first run
```

### Windows

**Unverified — no PowerShell installer confirmed live.** Before relying on
Kimi on Windows/Hermes, check `https://code.kimi.com/kimi-code/` for a
`.ps1` equivalent, or run the bash installer under Git Bash and manually
add `%USERPROFILE%\.kimi-code\bin` to PATH. Do not assume parity with
`cursor-agent`'s Windows path until confirmed.

## Canonical Install Locations (binary tracking)

**Tracked so any session can call the binary without re-discovering it —
mirrors the `cursor-agent` canonical-paths table.**

| Item | Path |
|------|------|
| Binary | `~/.kimi-code/bin/kimi` |
| Config | `~/.kimi-code/config.toml` (empty until `login`/`provider add`) |
| Device ID | `~/.kimi-code/device_id` (mode 600 — do not commit, do not log) |
| Diagnostic log | `~/.kimi-code/logs/kimi-code.log` (not rotated; `.1` files are) |
| PATH entry | Appended to `~/.zshrc` by the installer — idempotent, re-running the installer does not duplicate |
| Session data | Managed internally by `kimi`; export via `kimi export [sessionId]` |

Quick binary-location check for any agent/script before invoking Kimi:

```bash
command -v kimi >/dev/null 2>&1 || export PATH="$HOME/.kimi-code/bin:$PATH"
command -v kimi >/dev/null 2>&1 || { echo "kimi not installed — see kimi-agent/SKILL.md § Install"; exit 1; }
```

## Provider Setup (REQUIRED before fan-out — ASK FIRST, do not fabricate)

`kimi doctor` reports config as empty by default — **no LLM provider is wired
until one of these runs**, and this is a live credentials/config decision,
not something to auto-decide:

| Path | Command | Notes |
|------|---------|-------|
| Moonshot cloud (Kimi K2 family) | `kimi login` | Interactive device-code OAuth in browser — cannot be completed headlessly by an agent |
| models.dev catalog import (e.g. local LM Studio) | `kimi provider catalog add lmstudio --api-key <key>` | **Verified blocked without a key** even for a local/no-auth backend — confirm with the user whether to pass a placeholder or use the custom-registry path instead |
| Custom registry (point directly at a local OpenAI-compatible endpoint, e.g. Win LM Studio `:1234` or Mac Ollama `:11434`) | `kimi provider add <url-to-api.json> [--api-key <key>]` | Needs a hand-authored `api.json` — not yet created; this is the local-first-doctrine-aligned path (see orama-system `SKILL.md § Local API Fallback`) and should be scripted once the user picks a default |

**Do not run `kimi login` or fabricate an API key on the user's behalf.**
Surface this table and ask which provider to wire before any dispatch that
needs a live model.

## Key Options (from `kimi --help`, v0.23.4 — verified)

| Option | Purpose |
|--------|---------|
| `-p, --prompt <prompt>` | Headless single-turn — prints response to stdout (equivalent to `cursor-agent --print`) |
| `--output-format <fmt>` | `text` (default) or `stream-json` |
| `-m, --model <model>` | Override model alias (defaults to `default_model` in `config.toml`) |
| `-y, --yolo` | Auto-approve all actions (trusted/CI only) |
| `--auto` | Start in auto permission mode |
| `--plan` | Read-only planning mode |
| `-S, --session [id]` | Resume a session (interactive picker without an id) |
| `-c, --continue` | Continue the previous session for the working directory |
| `--add-dir <dir>` | Add an extra workspace directory (repeatable) |
| `--skills-dir <dir>` | Load skills from a custom dir instead of auto-discovery (repeatable) |

## Light Task Fanout Pattern

Same shape as the `cursor-agent` pattern — headless, backgrounded, `wait` to collect:

```bash
export PATH="$HOME/.kimi-code/bin:$PATH"

kimi -p "Add type annotations to scripts/discover.py; only functions, no variables" \
  --output-format text > /tmp/kimi-task-a.txt &

kimi -p "Rename all snake_case variables in tests/test_foo.py to camelCase" \
  --output-format text > /tmp/kimi-task-b.txt &

wait   # collect when done
```

**Division of labour (matches the cursor-agent table — Kimi slots into the
same "mechanical fan-out" tier, not the orchestrator tier):**

| Main session (orchestrator) | `kimi` (fan-out worker) |
|------------------------------|--------------------------|
| Architecture decisions | Mechanical file edits |
| CIDF write discipline | Grep-and-replace tasks |
| Cross-repo synthesis | Doc generation |
| Security & policy review | Test scaffolding |
| Final crystallisation | Format / lint fixes |

## Local Server (REST + WebSocket + Web UI) — the observability surface

Kimi ships its own local daemon — this IS the "monitor/observe" surface for
a single Kimi CLI instance, distinct from LAN-peer gossip (that's
`scripts/lm_link_watch.py`, a different concern: cross-machine inference-link
health, not one CLI agent's own liveness).

```bash
kimi server run                              # background daemon, default port 58627
kimi server run --foreground --log-level info  # attached, live logs, for debugging
kimi server run --open                       # also opens the web UI once healthy
```

**Security posture (verified from `kimi server run --help`, v0.23.4) —
defaults are safe, every widening flag is explicit and off by default:**

| Flag | Default behavior | What it changes |
|------|-------------------|------------------|
| `--host [host]` | omitted → binds `127.0.0.1` only | pass `--host` (no value) to bind `0.0.0.0`, or `--host <host>` for a specific interface — **widens exposure, only do this deliberately** |
| `--port <port>` | `58627` | bind port |
| *(bearer token)* | printed to stdout at startup, required on every REST/WS route | the only auth mechanism unless bypassed below |
| `--dangerous-bypass-auth` | off | disables bearer-token auth entirely — name is the warning |
| `--allow-remote-shutdown` | off (route 404s on non-loopback bind) | re-enables `POST /api/v1/shutdown` remotely |
| `--allow-remote-terminals` | off (404s) | re-enables PTY `/api/v1/terminals/*` — remote shell, high risk |
| `--allowed-host <host...>` | none | extra Host headers allowed through the DNS-rebinding check (repeatable, leading `.` = domain suffix) |
| `--insecure-no-tls` | `true` | only matters for non-loopback binds — a TLS-terminating reverse proxy is otherwise expected |
| `--keep-alive` | off (exits after 60s idle) | implied automatically once you pass `--host`/`--allowed-host`, and always on with `--foreground` |
| `--debug-endpoints` | off | mounts `/api/v1/debug/*` — leave unset outside test runs |

**For this stack's purposes, the default (loopback-only, token-required,
60s-idle-exit) is correct — do not pass `--host`, `--dangerous-bypass-auth`,
or the `--allow-remote-*` flags without an explicit reason.**

```bash
kimi server ps --json      # list connected clients, machine-readable
kimi server kill           # graceful stop (API) + forced PID kill fallback
kimi server rotate-token   # invalidate the current bearer token immediately
kimi vis [sessionId]       # session visualizer in browser (per-session trace)
kimi doctor                # config sanity check — run before any dispatch
tail -f ~/.kimi-code/logs/kimi-code.log   # diagnostic log, not rotated (.1 files are)
```

**Health-check one-liner** for a pulse cron / pre-dispatch gate:

```bash
command -v kimi >/dev/null 2>&1 && kimi doctor >/dev/null 2>&1 && echo "kimi: OK" || echo "kimi: NOT READY"
```

Or use the packaged probe: `bash bin/orama-system/skills/kimi-agent/scripts/kimi_status.sh` —
JSON output (`kimi_installed`, `version`, `doctor_ok`, `provider_lines`,
`server_clients`), exit 0 healthy / 1 doctor-failed / 2 not-installed.

## Agent Client Protocol (ACP)

```
Usage: kimi acp [options]
Run kimi-code as an Agent Client Protocol (ACP) server over stdio.

Options:
  --login     Run the device-code login flow then exit (entry point for ACP terminal-auth)
  -h, --help  Show help.
```

**What ACP is:** a stdio JSON-RPC protocol (distinct from MCP) for an editor
or host tool to drive an agentic coding backend — the same category of
integration point Zed and other ACP-aware editors use. `kimi acp` turns the
CLI into that backend: the host process spawns `kimi acp` as a child,
speaks ACP over its stdin/stdout, and gets Kimi's agentic loop (file edits,
shell, tool calls) without the CLI's own TUI.

```bash
# Run as an ACP server (host tool spawns this; not meant to be run standalone
# in a terminal and watched — stdin/stdout carry the protocol):
kimi acp

# First-time auth from inside an ACP host that can't do an interactive
# browser flow itself — run once to complete device-code login, then exit:
kimi acp --login
```

**Relationship to this stack's MCP registry — NOT the same integration
point.** MCP (`.mcp.json`, `claude mcp add`, `code-review-graph`, `gbrain`)
is how *this* Claude Code session reaches tools. ACP is how *an ACP-aware
host* (e.g. an editor) would drive *Kimi* as its backend — the direction is
reversed, and Kimi is the backend being driven, not a tool being called.
**Do not register `kimi acp` as an MCP server** — it speaks a different
protocol and the roles don't match. If a future need arises to embed Kimi
inside an ACP-native host in this stack, evaluate it as its own integration,
not a variant of the existing MCP wiring.

## Session Export

```bash
kimi export [sessionId] -o /path/to/archive.zip   # defaults to most recent session
# --no-include-global-log to exclude ~/.kimi-code/logs/kimi-code.log from the bundle
```

## Update

```bash
kimi upgrade   # alias: kimi update
```

## Commands Summary (v0.23.4, verified)

| Command | Purpose |
|---------|---------|
| `kimi login` | Authenticate via device-code OAuth (Moonshot cloud) |
| `kimi doctor` | Validate config files |
| `kimi provider add\|remove\|list\|catalog` | Manage LLM providers non-interactively |
| `kimi server run\|ps\|kill\|rotate-token` | Local REST+WS daemon — observability surface |
| `kimi web` | Open the Kimi web UI (starts daemon if needed) |
| `kimi vis [sessionId]` | Session visualizer in browser |
| `kimi export [sessionId]` | Export a session as a ZIP archive |
| `kimi migrate` | Migrate data from a legacy `kimi-cli` install |
| `kimi acp [--login]` | Run as an Agent Client Protocol server over stdio (see § Agent Client Protocol — NOT an MCP server, different protocol/direction) |
| `kimi upgrade` \| `kimi update` | Upgrade to latest version |

## References

- Platform-affinity routing (canonical known-agents table, Kimi added as a
  fan-out row): [`../hermes-harness/references/platform-affinity-routing.md`](../hermes-harness/references/platform-affinity-routing.md)
- Sibling fan-out agent (fuller precedent for this skill's structure):
  [`../cursor-agent/SKILL.md`](../cursor-agent/SKILL.md)
- Local-first fallback doctrine: [`../../../SKILL.md § Local API Fallback`](../../../SKILL.md)
- orama-system Stage 4 dispatch pattern: [`../../../SKILL.md § MODE 2 Stage 4`](../../../SKILL.md)

## Open Items (do not silently resolve — surface to user)

1. **Provider not yet wired** — `kimi doctor` passes on empty config, but no
   model can actually run until `login` or a `provider add`/`catalog add`
   path is chosen (see § Provider Setup). Ask before picking one.
2. **Windows install path unverified** — do not claim Hermes/Win parity
   until a `.ps1` installer or Git-Bash fallback is actually tested there.
3. **`kimi acp` embedding inside an ACP-native host** (e.g. an editor) is
   documented above but not yet exercised end-to-end in this stack — the
   protocol mechanics are verified from `--help`, live usage is not.
