# Atlas (lifecycle hub)

**OpenClaw id:** `main`  
**Workspace:** `${HOME}/.alphaclaw/.openclaw/workspace`

Atlas is the lifecycle hub — not a Hermes profile and not a pipeline stage.

## What lives on the hub (not duplicated here)

| Artifact | Location |
|----------|----------|
| Fleet registry | `docs/oramasys/REGISTRY.yml` |
| Persona YAML (runtime mirror) | `docs/oramasys/personas/` |
| Cross-ref | `docs/oramasys/CROSSREF.md` |

## Canonical staging (git)

| Artifact | Location |
|----------|----------|
| Lifecycle SOUL distillate | `bin/agents/lifecycle/SOUL.md` |
| Persona catalog (SSoT) | `bin/agents/personas/` |
| Fleet registry staging map | `bin/agents/REGISTRY.yml` |

## Install note

`install_hermes_profiles.py` skips roles with `hermes_profile: null`. OpenClaw overlay sync uses `scripts/sync_openclaw_overlay_from_staging.sh` for `main` workspace when operator opts in.
