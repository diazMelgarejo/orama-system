# Hermes portable brain map

> **Canonical persona staging:** `bin/agents/` + `REGISTRY.yml`  
> **Profile install:** `install_hermes_profiles.py`  
> **Thin skill install:** `install_hermes_thin_skills.py`  
> **Portable archive:** `hermes_portable_brain.py`  
> **OpenClaw overlay sync:** `scripts/sync_openclaw_overlay_from_staging.sh`

This card distinguishes Hermes' **actual local brain** from Orama-managed persona distillates and Perplexity/Perpetua project memory. Do not collapse these into one source of truth.

## Three layers (do not conflate)

| Layer | Purpose | Git? | Canonical storage |
|-------|---------|------|-------------------|
| **L1 Hermes portable brain** | Identity, memories, config, skills, profiles, sessions, scheduler state | No by default | `$HERMES_HOME` |
| **L2 Perplexity-Tools `.agent/`** | Project lessons, episodic memory, semantic lessons, reflection loop | Yes, PT repo | `Perplexity-Tools/.agent/` |
| **L3 orama-system Harness** | Persona distillates, harness ops, install/export/restore scripts, operator references | Yes, orama repo | `bin/agents/` + `bin/orama-system/skills/hermes-harness/` |

## `$HERMES_HOME` layout (Hermes Agent v0.19.x family)

```text
$HERMES_HOME/
├── SOUL.md                 # default brain identity / stable persona
├── config.yaml             # non-secret configuration: model, tools, display, approvals
├── .env                    # secrets only; never tracked
├── auth.json               # OAuth / credential-pool state; private
├── auth/                   # provider auth details; private
├── memories/
│   ├── MEMORY.md           # durable factual memory
│   └── USER.md             # user preferences/profile
├── skills/                 # procedural SKILL.md workflows
├── profiles/<slug>/        # isolated profile brain/config/memory/skills
├── state.db                # canonical session store + FTS
├── sessions/               # transcripts/routing artifacts
├── cron/                   # Hermes scheduler jobs/output
├── kanban/                 # durable multi-agent work board
├── scripts/                # local callable automation helpers
├── migration/openclaw/     # claw migrate gap archives
└── backups/                # restore/snapshot archives
```

Runtime source (`$HERMES_HOME/hermes-agent/`), caches, logs, and `node_modules/` are **not** part of the portable brain and should be regenerated or installed normally.

## Concept map

| Concept | Hermes storage / mechanism |
|---------|----------------------------|
| Soul / identity | `SOUL.md` (root or per-profile) |
| User preferences | `memories/USER.md` |
| Long-term facts | `memories/MEMORY.md` |
| Procedures | `skills/**/SKILL.md` |
| Project instructions | `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` in the workspace |
| Model/provider config | `config.yaml`; private keys in `.env` / `auth.json` |
| Conversations | `state.db` + `sessions/` |
| Durable scheduled work | `cron/` |
| Durable multi-agent board | `kanban/` |
| Orama multi-agent ops | `bin/orama-system/skills/hermes-harness/` |
| PT project lessons | `Perplexity-Tools/.agent/memory/` |

Hermes core system prompt is **not** a single editable soul file. Hermes core supplies runtime/tool/safety behavior; persona layers on top via SOUL, memory, skills, profiles, config, and project context.

## Two portable-brain paths

### A. Orama-managed persona distillates

`bin/agents/REGISTRY.yml` maps:

- `staging_folder` → `openclaw_id` → `hermes_profile` slug → `soul_id`

`install_hermes_profiles.py` materializes **SOUL distillates only** by default. Operator `MEMORY.md` / `USER.md` are stubbed on first create and are never overwritten without `--force-memory`.

Use this when you want a clean, role-based Hermes profile layout derived from Orama's canonical agent roster.

### B. Full current-Hermes portable brain archive

`hermes_portable_brain.py` exports the actual installed Hermes brain to a versioned zip with `manifest.json`:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py \
  export --output "$HOME/hermes-portable-brain.zip" --include-sessions
```

Defaults exclude secrets. Add `--include-secrets` only for trusted private archives. Restore uses `--dry-run` by default in operator examples and refuses overwrites unless `--overwrite` is passed.

Use this when you want a fresh Hermes install to come back like the existing Hermes instance: SOUL, memories, profiles, skills, config, sessions, cron, kanban, and scripts.

## Related cards

- [`hermes-portable-brain-archive.md`](hermes-portable-brain-archive.md) — export/inspect/restore commands
- [`openclaw-to-hermes-migration.md`](openclaw-to-hermes-migration.md) — `hermes claw migrate`
- [`hermes-profile-install.md`](hermes-profile-install.md) — profile installer operator steps
- [`hermes-skill-absorption-map.md`](hermes-skill-absorption-map.md) — thin wrapper inventory

Source distillate: [`docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md`](../../../../../docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md)
(see [`openclaw-workspace-path-doctrine.md`](openclaw-workspace-path-doctrine.md) — not `$OPENCLAW_ROOT`).
