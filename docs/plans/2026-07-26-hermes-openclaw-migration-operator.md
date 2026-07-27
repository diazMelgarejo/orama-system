# Hermes OpenClaw migration — operator sequence (orama canonical)

> **Reality checkpoint — verified 2026-07-27:** This is a migration runbook, not evidence that a migration has already occurred. On this host, Hermes **v0.19.0 (2026.7.20)** is rooted at `$HERMES_HOME`; only `default` is active and `$HERMES_HOME/profiles/` is absent. Use `hermes claw migrate --dry-run` before any import, preserve a native `hermes backup`, and regard imported OpenClaw content as source material until it is classified into local Hermes state, an Orama staged profile, PT memory, or archive-only provenance. Keep credentials out of tracked files. Official references: [CLI migration commands](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) and [configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration).

> **Date:** 2026-07-26  
> **Status:** Operator reference — **review with** [`2026-07-26-hermes-openclaw-staging-review-gate.md`](2026-07-26-hermes-openclaw-staging-review-gate.md) before running  
> **Env contract:** `$ORAMA_SYSTEM_PATH`, `$HERMES_HOME`, `$PERPETUA_TOOLS_PATH`, `${HOME}` only — no workstation literals in tracked docs.

## When to use

- First-time OpenClaw → Hermes brain import on Win/Mac
- Reinstall Hermes profiles from canonical `bin/agents/` after `git pull`

Hermes first-party command: `hermes claw migrate` (OpenClaw / Clawdbot / Moltbot).

## Safe sequence

### 1. Preserve restore point

```bash
hermes backup -o "${HOME}/hermes-pre-openclaw-migration.zip"
```

### 2. Preview import (no mutations)

```bash
hermes claw migrate --source "${HOME}/.openclaw" --dry-run
```

Windows: pass actual OpenClaw root if not default.

### 3. Choose workspace target for AGENTS.md

```bash
hermes claw migrate \
  --source "${HOME}/.openclaw" \
  --workspace-target "${OPENCLAW_WORKSPACE:-$ORAMA_SYSTEM_PATH/../OpenClaw}"
```

### 4. Full import **without secrets first**

```bash
hermes claw migrate \
  --source "${HOME}/.openclaw" \
  --preset full \
  --skill-conflict rename \
  --workspace-target "${OPENCLAW_WORKSPACE:-$ORAMA_SYSTEM_PATH/../OpenClaw}"
```

Imported skills land under `$HERMES_HOME/skills/openclaw-imports/`.

### 5. Reconcile canonical personas (after implementation plan lands)

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --install --verify
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
```

Uses `bin/agents/REGISTRY.yml` + `bin/agents/*/SOUL.md` — **SOUL sync only** by default.

### 6. Secrets (opt-in only)

```bash
hermes claw migrate --source "${HOME}/.openclaw" --preset full --migrate-secrets
```

Only after reviewing dry-run and operator approval.

### 7. Verify before cleanup

```bash
hermes doctor
hermes config check
hermes profile list
hermes skills list
```

Review gap archive: `$HERMES_HOME/migration/openclaw/<timestamp>/archive/`

### 8. Cleanup (only after gates pass)

```bash
hermes claw cleanup
```

## What maps where

| OpenClaw | Hermes destination |
|----------|-------------------|
| `workspace/SOUL.md` | `$HERMES_HOME/SOUL.md` |
| `workspace/MEMORY.md` | `$HERMES_HOME/memories/MEMORY.md` |
| `workspace/USER.md` | `$HERMES_HOME/memories/USER.md` |
| `workspace/AGENTS.md` | `--workspace-target` |
| Workspace skills | `$HERMES_HOME/skills/openclaw-imports/` |
| Multi-agent roster | Hermes **profiles** (see `bin/agents/REGISTRY.yml`) |
| `HEARTBEAT.md` / cron | Hermes cron or harness `coord_pulse.*` |

## Multi-agent → profiles

OpenClaw agent ids become Hermes profiles (not one overloaded default):

```bash
hermes profile create orchestrator --clone --description "Glen — routes pipeline work"
hermes profile create coder --clone --description "Rourke — Win LM Studio execution"
```

Canonical SOUL distillates: `bin/agents/<role>/SOUL.md`.

## Cross-references

- Portable brain map: `bin/orama-system/skills/hermes-harness/references/` (add `hermes-portable-brain-map.md` in implementation phase)
- Staging registry: `bin/agents/REGISTRY.yml`
- Live fleet hub: `${HOME}/.alphaclaw/.openclaw/workspace/docs/oramasys/REGISTRY.yml`
- Harness installer: `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py`
