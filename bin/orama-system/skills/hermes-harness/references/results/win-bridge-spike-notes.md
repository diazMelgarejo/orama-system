# Win bridge HTTP-local spike notes

**Fan-out:** `2026-06-28-coord-003`  
**Branch:** `subagent/win-coder/bridge-http-local` (Perpetua-Tools)  
**Assignee:** win-coder (Hermes)

## Problem

`autoresearch_bridge.preflight()` always SSH'd to `GPU_BOX` for git sync/bootstrap. On the Win GPU host during LAN co-orchestration, that blocks on SSH timeout even though autoresearch and LM Studio are local.

## Spike (additive, SSH path preserved)

| Trigger | Behavior |
|---------|----------|
| `AUTORESEARCH_PREFLIGHT_MODE=auto` (default) + `GPU_BOX` host is loopback or local IP | **http-local** — local git in `LOCAL_REPO_PATH`, HTTP GET `/v1/models` |
| `AUTORESEARCH_PREFLIGHT_MODE=http-local` | Force http-local |
| `AUTORESEARCH_PREFLIGHT_MODE=ssh` | Force legacy SSH (Mac → Win remote) |

### New helpers (`orchestrator/autoresearch_bridge.py`)

- `is_gpu_runner_local()` — compares `GPU_BOX` host to `_get_local_ips()`
- `use_http_local_preflight()` — mode gate
- `sync_autoresearch_local()` / `bootstrap_autoresearch_local()` — local git + `uv sync --dev`
- `probe_lm_studio_http()` — resolves base from `LLAMA_SERVER_BASE_URL` → `LM_STUDIO_WIN_ENDPOINTS` → `http://localhost:1234`

### `preflight()` return keys (added)

- `gpu_local`, `preflight_mode`, `lm_studio_ok`, `lm_studio_error`, `lm_studio_models`

SSH-only paths (`deploy_train_py`, `run_experiment_on_gpu`, `fetch_run_log`) unchanged — follow-up cycle.

## Tests

`tests/test_autoresearch_bridge.py` — `TestHttpLocalPreflight` (4 cases); SSH tests forced via `use_http_local_preflight → False`.

## Follow-ups (not in spike)

1. Local `train.py` dispatch without SCP when `gpu_local`
2. Promote `_get_local_ips()` to shared PT helper (already in `agent_launcher.py`)
3. Wire `lm_studio_ok` into `control_plane.preflight_autoresearch()` stage report
4. Env doc in `docs/LESSONS.md` co-orchestrator section

## Operator verify (Win host)

```powershell
$env:AUTORESEARCH_PREFLIGHT_MODE = "auto"
python -c "from orchestrator.autoresearch_bridge import preflight; print(preflight())"
# Expect: preflight_mode=http-local, sync_ok=True, lm_studio_ok=True (if LMS up)
```
