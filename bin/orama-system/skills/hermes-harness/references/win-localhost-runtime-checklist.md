# Win localhost runtime checklist (Hermes Phase 6+9)

> **When to run:** Win Coder is online on the **local** Windows host (localhost probes only —
> not remote-only RDP). Execute after Phases 1–8 land; defers live validation until hardware is up.

## Pre-flight

1. PowerShell UTF-8 bootstrap: `bin/orama-system/skills/git-history-surgery/references/windows-powershell-runtime-bootstrap.md`
2. `$env:PERPETUA_TOOLS_PATH` and `$env:ORAMA_SYSTEM_PATH` resolve to real dirs
3. LM Studio listening on **`http://localhost:1234`** (own-machine locality rule — not LAN IP when on Win)

## Canary table (live)

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py `
  --lm-studio-url http://localhost:1234/v1
```

Optional skips when a lane is intentionally absent:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py `
  --lm-studio-url http://localhost:1234/v1 --skip-hermes --skip-agy
```

Offline prep (no probes — prints this checklist):

```powershell
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --prepare
```

## Thin wrappers (Phase 9)

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --verify
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --test
```

Expected slash commands: `/pt-hardware-policy`, `/pt-orama-council`, `/pt-orama-review`, `/pt-orama-delegate`.

## Pass criteria

| Lane | Exact marker | Timeout |
|------|--------------|---------|
| LM Studio | `LM_READY` in chat completion | 15 s (fast path) |
| Hermes | `HERMES_READY` | 15 s |
| AGY | `AGY_READY` | 10 s (optional) |
| Codex | version string | 5 s (optional) |
| Git Bash | `hermes-bash-ok` | 5 s |

27B reasoning models may need up to **180 s** — document UNAVAILABLE for fast dispatch, not a gate failure for slow-path lanes.

## References

- [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md)
- [`lan-endpoint-contract.md`](lan-endpoint-contract.md)
- Plan: `docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md` Phases 6+9
