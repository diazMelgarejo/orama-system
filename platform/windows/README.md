# orama-system — Windows

Windows counterpart to `start.sh`. All Windows-specific files live here.

**Working directory:** examples below assume **orama-system repository root**
(the directory that contains `start.sh` and `platform/windows/`).

## Files

| File | Purpose |
|------|---------|
| `start.ps1` | Full Windows equivalent of `../start.sh` — same CLI modes |
| `install.ps1` | One-time idempotent setup (venv, deps, openclaw.json defaults) |
| `requirements-windows.txt` | Windows-only Python deps (pywin32, colorama, etc.) |

## First-time setup

```powershell
# Allow local scripts (once)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Install dependencies + write openclaw.json defaults
powershell -File .\platform\windows\install.ps1
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

# Re-run LAN discovery
.\platform\windows\start.ps1 --discover

# Validate model↔hardware affinity policy (delegates to Perpetua-Tools CLI)
.\platform\windows\start.ps1 --hardware-policy
```

Same policy as `start.sh --hardware-policy` on Mac/Linux OpenClaw. Hermes agents must
consume PT `model_hardware_policy.yml` — see `hermes-harness` → `pt-hardware-policy`.

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

- Windows GPU loads **ONE model at a time** — never configure parallel inference
- LM Studio on Windows listens on `localhost:1234` (not LAN-exposed by default)
- The Mac machine's LM Studio IP is read from `~/.openclaw/openclaw.json`
- Services log to `../.logs/{pt,orama,portal}.log` (same as macOS)
- `.paths.ps1` caches discovered paths (gitignored, auto-generated)
- **Hermes on Windows** is the local orchestrator counterpart to Mac OpenClaw; `install.ps1`
  writes `lmstudio-win` → `localhost:1234` for `windows_only` GGUF models
