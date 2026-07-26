# Hermes portable brain map (distilled)

> **Canonical persona staging:** `bin/agents/` + `REGISTRY.yml`  
> **Install:** `install_hermes_profiles.py` (profiles) + `install_hermes_thin_skills.py` (command wrappers)  
> **OpenClaw overlay sync:** `scripts/sync_openclaw_overlay_from_staging.sh`

## Three layers (do not conflate)

| Layer | Purpose | Git? |
|-------|---------|------|
| **L3 orama-system** | Persona distillates, harness ops, install scripts | Yes — `bin/agents/`, `hermes-harness/` |
| **L1 Hermes portable brain** | Identity, memories, skills, sessions, profiles | No — `$HERMES_HOME` only |
| **L2 Perpetua-Tools `.agent/`** | Project lessons, episodic memory | PT repo — not persona SSoT |

## `$HERMES_HOME` layout (Hermes Agent v0.19.x family)

```text
$HERMES_HOME/
├── SOUL.md                 # default brain identity
├── config.yaml             # non-secret configuration
├── .env                    # secrets only
├── memories/
│   ├── MEMORY.md           # durable factual memory
│   └── USER.md             # user preferences
├── skills/                 # procedural SKILL.md workflows
├── state.db                # session store
├── sessions/
├── profiles/<slug>/        # isolated profile brains
│   ├── SOUL.md
│   └── memories/
│       ├── MEMORY.md
│       └── USER.md
└── migration/openclaw/     # claw migrate gap archives
```

## Concept map

| Concept | Hermes storage |
|---------|----------------|
| Soul / identity | `SOUL.md` (root or per-profile) |
| User preferences | `memories/USER.md` |
| Long-term facts | `memories/MEMORY.md` |
| Procedures | `skills/**/SKILL.md` |
| Project instructions | `.hermes.md`, `AGENTS.md`, workspace context |
| Multi-agent ops | `bin/orama-system/skills/hermes-harness/` (canonical) |

Hermes core system prompt is **not** a single editable soul file — persona layers on top via SOUL, memory, skills, profiles, and project context.

## Profile slug authority

`bin/agents/REGISTRY.yml` maps:

- `staging_folder` → `openclaw_id` → `hermes_profile` slug → `soul_id`

Installers materialize **SOUL distillates only** by default. Operator `MEMORY.md` / `USER.md` are stubbed on first create — never overwritten without `--force-memory`.

## Related cards

- [`openclaw-to-hermes-migration.md`](openclaw-to-hermes-migration.md) — `hermes claw migrate`
- [`hermes-profile-install.md`](hermes-profile-install.md) — profile installer operator steps
- [`hermes-skill-absorption-map.md`](hermes-skill-absorption-map.md) — thin wrapper inventory

Source distillate: `OpenClaw/references/Hermes-Harness-Guide-for-Orama+Perpetua.md` (workstation paths stripped).
