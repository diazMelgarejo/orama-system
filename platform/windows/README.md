# orama-system — Windows

Windows counterpart to `start.sh`. All Windows-specific files live here.

**Working directory:** examples below assume **orama-system repository root**
(the directory that contains `start.sh` and `platform/windows/`).

## Files

| File | Purpose |
|------|---------|
| `start.ps1` | Full Windows equivalent of `../start.sh` — same CLI modes |
| `install.ps1` | One-time idempotent setup (venv, deps; optional legacy `openclaw.json` stub) |
| `requirements-windows.txt` | Windows-only Python deps (pywin32, colorama, etc.) |
| `peer_inbox_portal.py` | Win lane `/peer-inbox` HTML + remote peer fetch helpers |
| `markdown_render.py` | Server-side markdown → HTML for inbox previews (no CDN) |

## Peer inbox portal (Win lane)

Canonical operator URL: **`http://localhost:8002/peer-inbox`**

- Bidirectional LAN file inbox (local + peer columns)
- Server-side markdown preview via `/api/peer-inbox/{file}/html`
- Mac lane co-orchestration UI remains at `/co-orchestration` until manual merge

Shared inbox core stays in `src/orama_system/` (`lan_peer_files.py`, `/api/peer-file`).
Win-specific presentation lives here under `platform/windows/`.

## First-time setup

```powershell
# Allow local scripts (once)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Install dependencies (OpenClaw optional — Hermes is the local orchestrator)
powershell -File .\platform\windows\install.ps1

# Ensure partner CLIs on User PATH (Hermes, Codex, AGY, cursor-agent)
powershell -File .\platform\windows\ensure-partner-cli-paths.ps1

# Optional: write legacy openclaw.json stub (not needed for Hermes-only hosts)
powershell -File .\platform\windows\install.ps1 -WriteOpenClawConfig
```

## Usage

```powershell
# Start all services + open browser
.\platform\windows\start.ps1

# Start without opening browser
.\platform\windows\start.ps1 --no-open

# Stop all
.\platform\windows\start.ps1 --stop

# Status (port check + policy)
.\platform\windows\start.ps1 --status

# Re-run path discovery (.paths.ps1)
.\platform\windows\start.ps1 --discover

# Validate model↔hardware affinity policy (delegates to Perpetua-Tools CLI)
.\platform\windows\start.ps1 --hardware-policy
```

Validates model↔hardware affinity via Perpetua-Tools CLI (`--list` + Win model `--validate`).
Hermes is the primary Windows orchestrator; OpenClaw is optional. `--check-openclaw` runs only when
`~/.openclaw/openclaw.json` exists (legacy/cross-repo installs); Hermes-only hosts skip it gracefully.

## CLI parity table

| `start.sh` mode | `start.ps1` equivalent |
|---|---|
| `./start.sh` | `.\platform\windows\start.ps1` |
| `./start.sh --no-open` | `.\platform\windows\start.ps1 --no-open` |
| `./start.sh --stop` | `.\platform\windows\start.ps1 --stop` |
| `./start.sh --status` | `.\platform\windows\start.ps1 --status` |
| `./start.sh --discover` | `.\platform\windows\start.ps1 --discover` |
| `./start.sh --hardware-policy` | `.\platform\windows\start.ps1 --hardware-policy` |
| `lsof -ti tcp:PORT` | `netstat -ano` + `Stop-Process` |
| `nc -z localhost PORT` | `TcpClient.ConnectAsync` |
| `open URL` | `Start-Process URL` |
| `ipconfig getifaddr en0` | `Get-NetIPAddress` / `Get-NetRoute` |
| `pid_on_port()` | `Get-PidOnPort` (netstat-based) |

## Architecture notes

- **LM Studio single-model invariant** — on any machine (Mac/Linux/Windows), LM Studio loads **only one model at a time**. Loading a second model fails (e.g. `Failed to load model "gemma-4-e4b-it". Error: Operation canceled.`). Multiple models simultaneously only across **different remote machine IPs** (e.g. Mac LM Studio + Win LM Studio on LAN).
- Windows GPU loads **ONE model at a time** — never configure parallel inference on one host
- LM Studio on Windows listens on `localhost:1234` (locality rule — use `localhost`, not LAN IP)
- LM Studio server logs: Windows `%USERPROFILE%\.lmstudio\server-logs`; Mac/Linux `~/.lmstudio/server-logs` (e.g. `2026-06\2026-06-28.1.log`). After failed canary probes: `python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --tail-lmstudio-logs`
- Cross-machine Mac LM Studio IP: set `LM_STUDIO_MAC_ENDPOINT` / `OLLAMA_MAC_ENDPOINT`, or gateway `.110` heuristic; Mac OpenClaw hosts run `discover.py` — Windows Hermes does not require OpenClaw or `openclaw.json`
- Services log to `../.logs/{pt,orama,portal}.log` (same as macOS)
- `.paths.ps1` caches discovered paths (gitignored, auto-generated)
- **Hermes on Windows** is the sole local orchestrator — OpenClaw/AlphaClaw are Mac/Linux only
