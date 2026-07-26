# Hermes profile install (operator card)

> **Installer:** `bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py`  
> **Registry:** `bin/agents/REGISTRY.yml`

## Purpose

Materialize `bin/agents/*/SOUL.md` distillates into `$HERMES_HOME/profiles/<slug>/SOUL.md` with managed provenance — same non-clobber doctrine as `install_hermes_thin_skills.py`.

## Prerequisites

- `ORAMA_SYSTEM_PATH` points at orama-system checkout
- `HERMES_HOME` set (default: `%LOCALAPPDATA%\hermes` on Windows, override on Mac)
- Python 3 with PyYAML

## Install

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --sync
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify \
  || python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
```

`--sync` verifies first and installs only when profile SOUL bodies drift from `bin/agents/*/SOUL.md`. Re-runs print `already synced` when nothing changed.

Windows:

```powershell
powershell -File .\platform\windows\install-hermes-harness.ps1
```

Same idempotent behavior: profiles use `--sync`; thin wrappers verify-first.

## What gets written

| Target | Source | Overwrite policy |
|--------|--------|------------------|
| `profiles/<slug>/SOUL.md` | `bin/agents/<folder>/SOUL.md` | Refresh if managed (`created_by: agent`) |
| `profiles/<slug>/memories/USER.md` | `bin/agents/templates/profile/USER.md` | Create if missing; `--harmonize-memory` appends template under managed section (backup first) |
| `profiles/<slug>/memories/MEMORY.md` | `bin/agents/templates/profile/MEMORY.md` | Create if missing; `--harmonize-memory` integrative merge — never blind overwrite |

Skipped roles: `hermes_profile: null` (e.g. Atlas lifecycle hub).

## Pair with thin command wrappers

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
```

## Delegation config snippet

Non-secret defaults: `bin/agents/templates/config-delegation-snippet.yaml` — merge manually into Hermes `config.yaml` after profiles exist.

## Win `install.ps1` hook (wired 2026-07-26)

`platform/windows/install.ps1` calls `install-hermes-harness.ps1` by default (skip with `-SkipHermesHarness`).

Fresh RTX 5080 or existing RTX 3080 after `git pull`:

```powershell
cd $env:ORAMA_SYSTEM_PATH
powershell -ExecutionPolicy Bypass -File .\platform\windows\install.ps1
```

Profiles-only re-sync:

```powershell
powershell -File .\platform\windows\install-hermes-harness.ps1
```

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `missing staged SOUL` | Ensure `git pull` and role folder exists in `bin/agents/` |
| `skipped unmanaged profile SOUL` | Operator edited profile SOUL — reconcile manually or backup then delete marker block |
| Profile list empty after install | Confirm `HERMES_HOME` and write permissions |
| Slug mismatch | Fix `REGISTRY.yml` then re-run `--install --verify` |
