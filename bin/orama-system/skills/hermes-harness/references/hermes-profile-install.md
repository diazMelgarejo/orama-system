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
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --dry-run --install
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --install --verify
```

Windows PowerShell:

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_profiles.py --install --verify
```

## What gets written

| Target | Source | Overwrite policy |
|--------|--------|------------------|
| `profiles/<slug>/SOUL.md` | `bin/agents/<folder>/SOUL.md` | Refresh if managed (`created_by: agent`) |
| `profiles/<slug>/memories/USER.md` | `bin/agents/templates/profile/USER.md` | Create only unless `--force-memory` |
| `profiles/<slug>/memories/MEMORY.md` | `bin/agents/templates/profile/MEMORY.md` | Create only unless `--force-memory` |

Skipped roles: `hermes_profile: null` (e.g. Atlas lifecycle hub).

## Pair with thin command wrappers

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
```

## Delegation config snippet

Non-secret defaults: `bin/agents/templates/config-delegation-snippet.yaml` — merge manually into Hermes `config.yaml` after profiles exist.

## Win `install.ps1` hook (deferred)

Windows RTX 3080/5080 fleet install should call profile installer after orama clone — tracked in [`docs/plans/2026-07-26-hermes-agent-canonical-staging-and-profile-install.md`](../../../../docs/plans/2026-07-26-hermes-agent-canonical-staging-and-profile-install.md). **Not wired in this OpenClaw flesh-out commit.**

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `missing staged SOUL` | Ensure `git pull` and role folder exists in `bin/agents/` |
| `skipped unmanaged profile SOUL` | Operator edited profile SOUL — reconcile manually or backup then delete marker block |
| Profile list empty after install | Confirm `HERMES_HOME` and write permissions |
| Slug mismatch | Fix `REGISTRY.yml` then re-run `--install --verify` |
