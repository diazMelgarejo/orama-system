---
name: windows-hermes-setup
description: >-
  Windows Hermes setup wiring: PATH, partner CLIs (Hermes, Codex, AGY, cursor-agent),
  ECC install/validate idempotency, start.ps1 partner PATH and agent-comms decisions.
  Use when setting up Hermes/ECC on Windows or validating tool wiring.
version: 1.1.0
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
>
> Git workflow patterns and the archive delivery rule added 2026-11-04 from a Hermes
> self-improve patch (v1.1.0). The local wrapper stays an adapter; its patched copy of these
> sections is superseded by this card.

## When to Use

- Setting up or repairing Hermes, ECC and partner CLIs on a Windows host.
- Validating `start.ps1` partner PATH and agent-comms wiring.
- Syncing a dirty checkout or resolving ECC submodule conflicts on Windows.
- Packaging a Hermes brain for a new machine.

## Procedure

1. Load the [operator playbook](../../references/windows-hermes-setup.md).
2. **Probe first** — verify node/npm/git/cursor-agent/Hermes before adding PATH shims.
3. Run `platform/windows/ensure-partner-cli-paths.ps1` (or confirm `start.ps1` sources it).
4. If ECC not validated: `install.ps1 --target hermes --profile minimal` then doctor.
5. Refresh thin wrappers: `install_hermes_thin_skills.py --install --verify`.
6. Materialize personas: `install_hermes_profiles.py --install --verify` (see [`hermes-profile-install.md`](../../references/hermes-profile-install.md) + [`bin/agents/REGISTRY.yml`](../../../../agents/REGISTRY.yml)).
7. **CRG / Cursor MCP:** `bash bin/orama-system/scripts/sync-cursor-mcp.sh` (Windows → `:1234`).
8. Return factual status: wired / not wired / already correct per path.
9. Git sync and ECC submodule conflicts: follow the playbook's
   [Git Workflow Patterns](../../references/windows-hermes-setup.md#git-workflow-patterns).
   Archives for a new machine: follow the size and delivery rules in
   [`hermes-portable-brain-archive.md`](../../references/hermes-portable-brain-archive.md).

## Related reference cards

- [`hermes-portable-brain-map.md`](../../references/hermes-portable-brain-map.md)
- [`hermes-portable-brain-archive.md`](../../references/hermes-portable-brain-archive.md)
- [`openclaw-to-hermes-migration.md`](../../references/openclaw-to-hermes-migration.md)
- [`hermes-profile-install.md`](../../references/hermes-profile-install.md)

## Boundaries

### Always Do

- Probe before adding PATH shims or reinstalling, and report wired / not wired / already correct.
- Read this card from a current orama-system checkout; if the checkout is dirty or behind remote,
  report drift instead of overwriting.
- Use the playbook's merge-only git patterns: tagged stash, `git switch -c ... origin/main`,
  merge commits only.

### Ask First

- Switching branches or syncing on a checkout that has uncommitted changes.
- Creating an archive with `--include-secrets` or `--include-sessions`.
- Changing account or provider settings, deploying, or deleting anything.

### Never Do

- Copy raw `%LOCALAPPDATA%\hermes`, secrets, OAuth tokens or personal memory into tracked files.
- Attach a private archive to an agent inbox card, GossipBus log, email, chat or Git.
- Run `git clean -fd` or `-fdx` without explicit approval and a backup of the working tree.
- Rebase or force-push.

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
- [`../../references/update-all-agents-comms.md`](../../references/update-all-agents-comms.md) — comms recipe + 5-minute recurring comms board
- [`../../../../../../platform/windows/ensure-partner-cli-paths.ps1`](../../../../../../platform/windows/ensure-partner-cli-paths.ps1)
- [`../../../../../../platform/windows/start.ps1`](../../../../../../platform/windows/start.ps1)
- [`../../scripts/install_hermes_thin_skills.py`](../../scripts/install_hermes_thin_skills.py)
- [`../../scripts/coord_comms_board.ps1`](../../scripts/coord_comms_board.ps1) — 5-minute recurring full-comm tick wrapper
