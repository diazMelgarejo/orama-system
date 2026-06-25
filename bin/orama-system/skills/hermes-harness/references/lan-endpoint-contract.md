# LAN Endpoint Contract

**Locality rule (non-negotiable):** When code runs on a machine, reach that
machine's own services via `localhost`. Use `$WIN_IP`/`$MAC_IP` only for
cross-machine calls from a *different* host.

## Endpoint Variable Registry

| Variable | Default | Scope |
|---|---|---|
| `LLAMA_SERVER_BASE_URL` | `http://localhost:1234/v1` | LM Studio base URL on whichever host the code runs |
| `LM_STUDIO_WIN_ENDPOINT` | `$WIN_IP:1234` | Mac→Win cross-machine only |
| `LM_STUDIO_MAC_ENDPOINT` | `$MAC_IP:11434` | Win→Mac cross-machine only |
| `WIN_CODER_ENDPOINTS` | `$WIN_IP:1234` | Mac-side pool of Windows coders |
| `MAC_IP` | Set in `.env` / `start.ps1` | Machine-specific; never hardcode |
| `WIN_IP` | Set in `.env` / `start.ps1` | Machine-specific; never hardcode |

## Per-Host Rules

### On Windows (Hermes or any process)

LM Studio is local:

```bash
# Correct — LM Studio is local
export LLAMA_SERVER_BASE_URL="http://localhost:1234/v1"

# Wrong — this is a cross-machine address for Mac→Win calls only
# export LLAMA_SERVER_BASE_URL="http://192.168.254.103:1234/v1"
```

`windows_only` models are **allowed** from Windows — the hardware policy yields
an inverted verdict for the local host vs. a remote dispatcher.

### On Mac (OpenClaw or any process)

Ollama and Mac LM Studio are local:

```bash
# Correct — Ollama is local on Mac
OLLAMA_BASE_URL="http://localhost:11434"

# For Win LM Studio from Mac — cross-machine is correct here
WIN_LM_STUDIO_URL="http://${WIN_IP:-192.168.254.x}:1234/v1"
```

### In Shared Config / Docs

Never write a literal workstation IP in tracked files. Use the variable:

```yaml
# Wrong
lmstudio_win: http://192.168.254.103:1234

# Correct
lmstudio_win: http://${LM_STUDIO_WIN_ENDPOINT}
```

## Hardware Policy Interaction

The PT hardware policy (`config/model_hardware_policy.yml`) classifies models as
`windows_only`, `mac_only`, or `any`. When running on Windows, `windows_only`
models are ALLOWED via `localhost:1234`. The policy verdict is relative to the
executing host — a model that is `NEVER_MAC` is not `NEVER_WIN`.

**Never dispatch a `windows_only` model over `$WIN_IP` from Windows itself —
that is double-crossing the LAN for no reason and introduces latency.**

## LM Studio Cross-Platform Model Listing

LM Studio's `/v1/models` endpoint lists ALL models known to LM Studio,
regardless of whether they are compatible with the current hardware.

Example: A Windows LM Studio instance may list `qwen3.5-9b-mlx` (Apple Silicon
MLX format) alongside GGUF models. The MLX model cannot run on Windows — it
will fail silently or produce garbage output.

**Always enforce hardware policy before dispatch. Never trust `/v1/models`
presence as a load-ready signal for cross-platform models.**

See: [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md)
for the live `/v1/models` probe that filters by `windows_only` before dispatch.
