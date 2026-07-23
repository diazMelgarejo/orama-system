---
name: windows-hermes-setup
description: >-
  Windows Hermes setup wiring: PATH, partner CLIs (Hermes, Codex, AGY, cursor-agent),
  ECC install/validate idempotency, start.ps1 partner PATH and agent-comms decisions.
  Use when setting up Hermes/ECC on Windows or validating tool wiring.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, windows
parent_skill: hermes-harness
triggers:
  - windows-hermes-setup
  - windows hermes setup
  - hermes windows path
  - ecc doctor hermes
  - ensure-partner-cli-paths
allowed-tools: bash, file-operations
---

# Windows Hermes Setup

> **Canonical operator playbook:**
> [`../../references/windows-hermes-setup.md`](../../references/windows-hermes-setup.md)
>
> Absorbed from Hermes self-improve skill `windows-hermes-setup` (2026-07-23).
> This command card is the SSoT; the Hermes-local thin wrapper in
> `%LOCALAPPDATA%\hermes\skills\pt-orama\windows-hermes-setup\` points here.

## Procedure

1. Load the [operator playbook](../../references/windows-hermes-setup.md).
2. **Probe first** — verify node/npm/git/cursor-agent/Hermes before adding PATH shims.
3. Run `platform/windows/ensure-partner-cli-paths.ps1` (or confirm `start.ps1` sources it).
4. If ECC not validated: `install.ps1 --target hermes --profile minimal` then doctor.
5. Refresh thin wrappers: `install_hermes_thin_skills.py --install --verify`.
6. Return factual status: wired / not wired / already correct per path.

## Envelope

```json
{
  "skill_id": "windows-hermes-setup",
  "args": { "probe": "full", "ecc_doctor": true },
  "agent_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "transport": { "partner": "hermes", "profile": "windows-bring-up" }
}
```

## References

- [`../../references/windows-hermes-setup.md`](../../references/windows-hermes-setup.md) — main playbook
- [`../../references/windows-onboarding-config.md`](../../references/windows-onboarding-config.md) — env vars
- [`../../references/cursor-agent-steering-handoff.md`](../../references/cursor-agent-steering-handoff.md)
- [`../../references/ecc-doctor-and-cursor-smoke-checks.md`](../../references/ecc-doctor-and-cursor-smoke-checks.md)
- [`../../references/hermes-windows-partner-readiness.md`](../../references/hermes-windows-partner-readiness.md)
- [`../../../../../../platform/windows/ensure-partner-cli-paths.ps1`](../../../../../../platform/windows/ensure-partner-cli-paths.ps1)
- [`../../../../../../platform/windows/start.ps1`](../../../../../../platform/windows/start.ps1)
- [`../../scripts/install_hermes_thin_skills.py`](../../scripts/install_hermes_thin_skills.py)
