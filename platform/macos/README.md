# orama-system — macOS

macOS counterpart to `platform/windows/`. Portal co-orchestration skins and `start.sh` live here.

**Working directory:** examples assume **orama-system repository root**.

## Files

| File | Purpose |
|------|---------|
| `../start.sh` | Full macOS stack — PT `:8000`, orama `:8001`, Portal `:8002` |
| `../src/orama_system/portals/co_orchestration_macos.py` | **OpenClaw** co-orchestration inbox skin |
| `../src/orama_system/portals/co_orchestration_windows.py` | Hermes skin (Win parallel branch) |

## Portal — co-orchestration inbox monitor

| URL | Skin |
|-----|------|
| `http://localhost:8002/co-orchestration/macos` | **macOS / OpenClaw** (use on Mac) |
| `http://localhost:8002/co-orchestration/windows` | Windows / Hermes (preview or Win host) |
| `http://localhost:8002/co-orchestration` | Auto-detect from host platform |

Shows bidirectional file inbox (local + peer), fan-out filter, click-to-preview markdown.

## Usage

```bash
git pull --rebase origin main
./start.sh --stop && ./start.sh --lan-peer --no-open
open http://localhost:8002/co-orchestration/macos
```

## Platform affinity (co-orchestrator)

- **Harness:** OpenClaw + AlphaClaw (`start.sh`)
- **Inference:** Ollama `:11434` warm; LM Studio `:1234` passive
- **Subagents:** mac-researcher, orchestrator, cursor-agent (local only)
- **PT memory:** `Perpetua-Tools/.agent/memory/working/MAC_CO_ORCHESTRATOR_WHERE_TO_LOOK_2026-06-28.md`

## Git branch

Parallel portal work: `platform/macos-portal` (Mac) vs Win `platform/windows-portal` when present.
