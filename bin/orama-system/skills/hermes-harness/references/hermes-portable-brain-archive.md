# Hermes portable brain archive — export / inspect / restore

> **Script:** [`../scripts/hermes_portable_brain.py`](../scripts/hermes_portable_brain.py)  
> **Purpose:** make a new Hermes installation restorable to the same layered brain state without committing private state to git.

## What this solves

Hermes' portable brain is not one file. It is a layered runtime home under `$HERMES_HOME`:

- identity/persona: `SOUL.md`
- user preferences: `memories/USER.md`
- durable facts: `memories/MEMORY.md`
- procedures: `skills/**/SKILL.md`
- profiles: `profiles/<slug>/...`
- non-secret config/models/tools: `config.yaml`
- optional sessions: `state.db` + `sessions/`
- optional secrets: `.env`, `auth.json`, `auth/`

`hermes_portable_brain.py` creates a versioned zip archive with a `manifest.json` so the archive can be inspected and restored safely.

## Safety defaults

| Category | Default export | Restore requirement | Notes |
|---|---:|---:|---|
| `SOUL.md` | yes | normal | identity layer |
| `memories/` | yes | normal | USER/MEMORY facts |
| `skills/` | yes | normal | procedure layer |
| `profiles/` | yes | normal | role brains |
| `config.yaml` | yes | normal | non-secret config only |
| `cron/`, `kanban/`, `scripts/` | yes | normal | automation state |
| `state.db`, `sessions/` | no | `--include-sessions` | can be large / personal |
| `.env`, `auth.json`, `auth/` | no | `--include-secrets` | credentials; never commit |
| `logs/`, `cache/`, `hermes-agent/`, `node_modules/` | no | n/a | regenerated or runtime source |

## Export from an existing Hermes install

Preview first:

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  export \
  --output "$HOME/hermes-portable-brain.zip" \
  --dry-run
```

Create a non-secret archive:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  export \
  --output "$HOME/hermes-portable-brain.zip" \
  --include-sessions
```

Create a full private archive, only when the operator explicitly wants credentials included:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  export \
  --output "$HOME/hermes-portable-brain-private.zip" \
  --include-sessions \
  --include-secrets
```

## Inspect before restore

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  inspect "$HOME/hermes-portable-brain.zip" --summary
```

## Restore onto a fresh Hermes install

Dry-run first:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  restore "$HOME/hermes-portable-brain.zip" \
  --include-sessions \
  --dry-run
```

Apply, preserving existing files unless `--overwrite` is supplied:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  restore "$HOME/hermes-portable-brain.zip" \
  --include-sessions
```

Overwrite mode creates a pre-restore zip under `$HERMES_HOME/backups/` unless `--no-backup` is passed:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  restore "$HOME/hermes-portable-brain.zip" \
  --include-sessions \
  --overwrite
```

Restore secrets only from a trusted private archive:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  restore "$HOME/hermes-portable-brain-private.zip" \
  --include-sessions \
  --include-secrets \
  --overwrite
```

## Relation to Hermes-native commands

Use the right layer:

| Need | Prefer |
|---|---|
| Whole current Hermes home snapshot | `hermes backup` |
| One Hermes profile transfer | `hermes profile export` / `hermes profile import` |
| OpenClaw import | `hermes claw migrate` |
| Orama-managed personas | `install_hermes_profiles.py` |
| Orama thin command wrappers | `install_hermes_thin_skills.py` |
| Auditable portable brain archive controlled by Orama Harness | `hermes_portable_brain.py` |

## Post-restore verification

```bash
hermes doctor
hermes config check
hermes profile list
hermes skills list
```

Then start a fresh Hermes session so memory, skills, and project context are reloaded from disk.
