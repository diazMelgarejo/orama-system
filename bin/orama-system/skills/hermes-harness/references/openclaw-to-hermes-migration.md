# OpenClaw → Hermes migration (operator card)

> **Review gate:** [`docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md`](../../../../docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md)  
> **Full operator sequence:** [`docs/plans/2026-07-26-hermes-openclaw-migration-operator.md`](../../../../docs/plans/2026-07-26-hermes-openclaw-migration-operator.md)

## When to use

- First-time OpenClaw brain import into Hermes
- Reconcile profiles after `git pull` on `bin/agents/`

## OpenClaw overlay sync (Mac operator — no Hermes required)

Integrative merge from canonical staging — preserves OpenClaw Core Truths, refreshes overlay:

```bash
cd "$ORAMA_SYSTEM_PATH"
./scripts/sync_openclaw_overlay_from_staging.sh
./scripts/sync_openclaw_overlay_from_staging.sh --dry-run   # preview
```

Uses `bin/agents/REGISTRY.yml` + `bin/agents/*/SOUL.md`.

## Hermes `claw migrate` sequence (summary)

```bash
hermes backup -o "${HOME}/hermes-pre-openclaw-migration.zip"
hermes claw migrate --source "${HOME}/.openclaw" --dry-run
hermes claw migrate \
  --source "${HOME}/.openclaw" \
  --preset full \
  --skill-conflict rename \
  --workspace-target "${OPENCLAW_WORKSPACE:-$ORAMA_SYSTEM_PATH/../OpenClaw}"
```

Secrets: add `--migrate-secrets` only after dry-run review.

## Reconcile canonical personas (after migrate or on fresh Win install)

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --install --verify
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
```

Canonical templates win over imported OpenClaw copies for **managed** profile SOUL files (`created_by: agent` marker).

## Export/restore the actual Hermes portable brain

When the goal is to move the **current Hermes instance itself** to a fresh install, use the Orama Harness portable-brain archive wrapper:

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  export --output "$HOME/hermes-portable-brain.zip" --include-sessions
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  inspect "$HOME/hermes-portable-brain.zip" --summary
```

Restore on a fresh Hermes install, dry-run first:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  restore "$HOME/hermes-portable-brain.zip" --include-sessions --dry-run
```

Secrets (`.env`, `auth.json`, `auth/`) are excluded unless `--include-secrets` is explicitly used for a trusted private archive. Full reference: [`hermes-portable-brain-archive.md`](hermes-portable-brain-archive.md).

## Verify before cleanup

```bash
hermes doctor
hermes config check
hermes profile list
hermes skills list
```

Gap archive: `$HERMES_HOME/migration/openclaw/<timestamp>/archive/`

## Atlas / lifecycle hub

`main` (Atlas) is **not** a Hermes profile. Lifecycle binding stays on hub workspace + `bin/agents/lifecycle/SOUL.md` distillate.

## Persona YAML

Tracked catalog: `bin/agents/personas/` (SSoT). Runtime hub mirror: `${HOME}/.alphaclaw/.openclaw/workspace/docs/oramasys/personas/`.
