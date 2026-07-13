---
name: kimi-agent
description: >-
  Install, configure, and operate the Kimi Code CLI (`kimi`) for fanning out
  light/parallel tasks alongside the main orchestration session, and for
  monitoring its background server and session logs. Cross-platform installer
  (Moonshot AI); macOS/Linux path verified live 2026-07-10 (darwin-arm64,
  v0.23.4); Windows path verified live 2026-07-13 (win32-x64, v0.23.6, via the
  official PowerShell installer).
version: 1.1.0
license: Apache 2.0
compatibility: darwin, linux, win32, orama-system, openclaw, hermes-harness
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

### Windows (verified 2026-07-13, win32-x64, v0.23.6)

An official PowerShell installer exists at the same domain as the macOS/Linux
one — confirmed live, not just documented:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
irm https://code.kimi.com/kimi-code/install.ps1 | iex
# Installs to %USERPROFILE%\.kimi-code\bin\kimi.exe; adds to User PATH — idempotent
# (re-running backs up the existing binary to kimi.exe.bak and reinstalls).
# New shells pick up PATH automatically; in an existing shell:
$env:Path = "$env:USERPROFILE\.kimi-code\bin;" + $env:Path
```

Verify:

```powershell
kimi --version    # e.g. 0.23.6
kimi doctor       # validates config.toml / tui.toml
kimi provider list
```

Provider setup is identical to macOS/Linux (`kimi login`, § Provider Setup
below) — confirmed working with the same managed Moonshot-cloud provider
already authenticated on this stack.

The TLS 1.2 line is only needed on hosts where PowerShell 5.1 doesn't
negotiate it by default (older Windows); the installer script sets this
itself, but doing it explicitly before `irm` avoids a silent TLS handshake
failure on some machines.

## Canonical Install Locations (binary tracking)

**Tracked so any session can call the binary without re-discovering it —
mirrors the `cursor-agent` canonical-paths table.**

| Item | macOS/Linux | Windows |
|------|-------------|---------|
| Binary | `~/.kimi-code/bin/kimi` | `%USERPROFILE%\.kimi-code\bin\kimi.exe` |
| Config | `~/.kimi-code/config.toml` (empty until `login`/`provider add`) | `%USERPROFILE%\.kimi-code\config.toml` |
| Device ID | `~/.kimi-code/device_id` (mode 600 — do not commit, do not log) | `%USERPROFILE%\.kimi-code\device_id` |
| Diagnostic log | `~/.kimi-code/logs/kimi-code.log` (not rotated; `.1` files are) | `%USERPROFILE%\.kimi-code\logs\kimi-code.log` |
| PATH entry | Appended to `~/.zshrc` by the installer — idempotent | Added to User PATH registry by the installer — idempotent |
| Session data | Managed internally by `kimi`; export via `kimi export [sessionId]` | Same |

Quick binary-location check for any agent/script before invoking Kimi:

```bash
command -v kimi >/dev/null 2>&1 || export PATH="$HOME/.kimi-code/bin:$PATH"
command -v kimi >/dev/null 2>&1 || { echo "kimi not installed — see kimi-agent/SKILL.md § Install"; exit 1; }
```

## Provider Setup

**Status: WIRED (verified 2026-07-10).** The user ran `kimi login`
(Moonshot cloud device-code OAuth) — `kimi doctor` now reports both config
files `OK`, and `kimi provider list` shows:

```
managed:kimi-code  type=kimi  models=2  source=oauth
Default model: kimi-code/kimi-for-coding
```

Fan-out dispatch (`kimi -p ...`) is live and smoke-tested (see § Light Task
Fanout Pattern). No further setup needed for the Moonshot-cloud path.

**If the managed provider is ever removed/expired, or a local-first path is
wanted instead** (frugality — avoid Moonshot cloud calls for mechanical
tasks), these remain the options — still a live credentials/config decision,
ask before picking one:

| Path | Command | Notes |
|------|---------|-------|
| Moonshot cloud (Kimi K2 family) | `kimi login` | Interactive device-code OAuth in browser — cannot be completed headlessly by an agent. **Already done.** |
| models.dev catalog import (e.g. local LM Studio) | `kimi provider catalog add lmstudio --api-key <key>` | **Verified blocked without a key** even for a local/no-auth backend — confirm with the user whether to pass a placeholder or use the custom-registry path instead |
| Custom registry (point directly at a local OpenAI-compatible endpoint, e.g. Win LM Studio `:1234` or Mac Ollama `:11434`) | `kimi provider add <url-to-api.json> [--api-key <key>]` | Needs a hand-authored `api.json` — not yet created; this is the local-first-doctrine-aligned path (see orama-system `SKILL.md § Local API Fallback`) and should be scripted if a local default is ever wanted |

**Do not fabricate an API key on the user's behalf** for the fallback paths
above; the Moonshot-cloud path is already authenticated and is the current
default.

## Key Options (from `kimi --help`, v0.23.4 — verified)

| Option | Purpose |
|--------|---------|
| `-p, --prompt <prompt>` | Headless single-turn — prints response to stdout (equivalent to `cursor-agent --print`) |
| `--output-format <fmt>` | `text` (default) or `stream-json` |
| `-m, --model <model>` | Override model alias (defaults to `default_model` in `config.toml`) |
| `-y, --yolo` | Auto-approve all actions (trusted/CI only) — **verified INCOMPATIBLE with `-p`/`--prompt`**: `kimi -p "..." --yolo` fails hard with `error: Cannot combine --prompt with --yolo.` `-p` mode is already non-interactive by definition (no approval loop exists to bypass), so it needs no auto-approve flag at all — just drop `--yolo` when using `-p`. |
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

**Output shape (verified live, `--output-format text`) — NOT clean
answer-only stdout.** A real smoke test (`kimi -p "Reply with exactly:
KIMI_READY"`) returned:

```
• The user wants exactly "KIMI_READY". I should reply with that exact text, no tools.

• KIMI_READY

To resume this session: kimi -r session_abe4f2aa-cdd6-493f-9414-faffb829536d
```

`text` mode includes a `•`-prefixed reasoning/narration line before the
actual answer, and always appends a `To resume this session: kimi -r
<id>` footer. **Any script parsing `kimi -p` output must not assume line 1
or the full stdout is the answer** — either use `--output-format
stream-json` and parse structured events, or grep/strip the narration and
resume-footer lines. Not yet determined which `stream-json` event carries
the final answer cleanly; verify before building an automated parser.

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
`provider_lines` is a rough presence count (0 = no provider, >0 = at least
one configured) from `kimi provider list` output — not an exact provider
count; verified `0 → 3` across the `kimi login` transition.

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

1. ~~Provider not wired~~ — **RESOLVED 2026-07-10**: user ran `kimi login`;
   managed Moonshot provider is live (2 models, `kimi-code/kimi-for-coding`
   default). Fallback local-provider paths in § Provider Setup remain
   undone and are opt-in only if frugality later demands it.
2. **`kimi -p` text output is not clean answer-only stdout** — includes a
   `•` narration line and a `To resume this session:` footer (verified
   live). Any automated parsing of fan-out results needs to account for
   this; `stream-json` structure not yet mapped.
3. ~~Windows install path unverified~~ — **RESOLVED 2026-07-13**: official
   `.ps1` installer confirmed live at `https://code.kimi.com/kimi-code/install.ps1`,
   verified end-to-end on win-rtx5080 (v0.23.6, `kimi doctor` OK, provider
   already wired, smoke-tested with `kimi -p "Reply with exactly: KIMI_READY"`
   matching the documented output shape exactly). Hermes/Win parity with
   `cursor-agent` confirmed for the install + dispatch path; `kimi server`
   and `kimi acp` on Windows remain unexercised (see item 4).
4. **`kimi acp` embedding inside an ACP-native host** (e.g. an editor) is
   documented above but not yet exercised end-to-end in this stack — the
   protocol mechanics are verified from `--help`, live usage is not.
5. **`kimi server`/`kimi vis` local daemon not yet tested on Windows** —
   install + `-p` dispatch are verified there; the REST/WS observability
   surface (§ Local Server) is unverified on win32 specifically.
