---
title: Platform Affinity Routing
description: Canonical harness bias table — Mac/Linux prefers AlphaClaw/OpenClaw, Windows prefers Hermes; ECC bridges both.
status: active
---

# Platform Affinity Routing

## The Rule

**Pick the harness the platform was built for, then let ECC bridge the gap.**

| Platform | Preferred harness | Entry point | Why |
|----------|------------------|-------------|-----|
| **macOS** | AlphaClaw + OpenClaw | `start.sh` | MLX inference, bge-m3 embeddings, LM Studio Mac port; OpenClaw is the primary runtime gateway |
| **Linux** | AlphaClaw + OpenClaw | `start.sh` | Same binary as macOS; CUDA/ROCm GPU optional; full hardware matrix from PT `hardware/SKILL.md` |
| **Windows 11** | Hermes Harness | `start.ps1` | GGUF LM Studio localhost, Git Bash, PowerShell toolchain; Hermes is native Windows operator shell |

## ECC Interoperability Contract

ECC (`vendor/ecc-tools`, canonical: `affaan-m/ECC`) ensures that orama-system skills work
in **both** harness environments without modification — now (v1) and in the future (v2/oramasys).

```
orama-system skill
       │
       ├─ consumed by OpenClaw (Mac/Linux)  ──► AlphaClaw dispatch
       └─ consumed by Hermes (Windows)      ──► Hermes one-shot / agent mode
```

ECC migration rules: [`ecc-migration-rules.md`](ecc-migration-rules.md)
Cross-harness protocol: [`cross-harness-protocol.md`](cross-harness-protocol.md)

## Harness Selection Algorithm

```
1. Determine host OS: sys.platform == "win32" → Windows; otherwise → Mac/Linux
2. Windows?
   └─ YES: activate Hermes (start.ps1 → HERMES_HOME)
           use LM Studio at localhost:1234 as inference backend
           call PT hardware policy via Hermes one-shot provider route
   └─ NO:  activate OpenClaw (start.sh → ~/.openclaw)
           use Ollama localhost:11434 (mandatory) + optional LM Studio Mac port
           call PT hardware policy via openclaw_chat/openclaw_orchestrate
3. Skill execution: load from orama-system/bin/ via ECC import rules regardless of harness
4. Cross-platform tasks: use Win LAN IP from ~/.openclaw/state/last_discovery.json (never hardcode)
```

## Hardware Policy SSoT

Perpetua-Tools `config/model_hardware_policy.yml` + `src/utils/hardware_policy.py` are the
**only** model affinity source of truth. Neither harness infers `NEVER_MAC`/`NEVER_WIN`
independently — they query the policy layer.

- `NEVER_MAC` models: Win-only GGUF, served from Windows LM Studio
- `NEVER_WIN` models: Mac-only MLX, served from Mac LM Studio / Ollama
- `PREFERRED_WIN` / `PREFERRED_MAC`: harness picks first, falls back if unavailable

## v2 / oramasys Forward Compatibility

The same routing table applies in v2. oramasys will maintain the `win → Hermes`,
`mac/linux → OpenClaw` harness split. ECC v2 will deliver cross-harness skill portability
via a structured manifest format (planned in D17 / orama `docs/v2/30`).

## Anti-Patterns

- DO NOT run Hermes-specific PowerShell automation on Mac (use `start.sh` equivalents)
- DO NOT run OpenClaw Mac MLX models on Windows (`NEVER_MAC` policy blocks this at PT layer)
- DO NOT hardcode platform detection — always use `sys.platform` or `$env:OS` at runtime
- DO NOT duplicate skill YAML between harnesses — one source in orama-system, ECC syncs both
