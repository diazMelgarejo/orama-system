# `bin/agents` — canonical persona staging (OpenClaw + Hermes)

> **Status:** Staging for review (2026-07-26). **Do not** treat live OpenClaw or Hermes homes as SSoT — this tree is the auditable distillate installers copy into Hermes profiles and Claude/OpenClaw subagent cards.

## What lives here

| Artifact | Purpose | Consumed by |
|----------|---------|-------------|
| `REGISTRY.yml` | Maps staging folder ↔ OpenClaw id ↔ Hermes profile slug ↔ orama `soul_id` | `install_hermes_profiles.py` (planned), humans, agents |
| `{role}/SOUL.md` | Persona overlay distillate (no OpenClaw Core Truths block) | Hermes `$HERMES_HOME/profiles/<slug>/SOUL.md` |
| `{role}/agent.md` | Claude Code / OpenClaw subagent card (YAML frontmatter) | `install-multi-agent.sh`, `.claude/agents/` |
| `{role}/README.md` | Stage contract notes | Docs + orchestrator |
| `orchestrator/*.py`, `dispatcher.py` | L3 planning/dispatch code | Python runtime (not copied to Hermes) |

## Live sources (read-only, not git)

| Layer | Authoritative live map | Notes |
|-------|------------------------|-------|
| OpenClaw fleet (17 agents) | `${HOME}/.alphaclaw/.openclaw/workspace/docs/oramasys/REGISTRY.yml` | MERGE-10 + EDITED-03; synced with `openclaw.json` |
| OpenClaw per-agent SOUL | `${HOME}/.openclaw/agents/<id>/SOUL.md` | Core Truths + `## Oramasys role overlay` |
| Atlas hub | `${HOME}/.alphaclaw/.openclaw/workspace` | `main` agent; not a Hermes profile |
| Hermes portable brain | `$HERMES_HOME/` (Win: `%LOCALAPPDATA%\hermes`) | Profiles, memories, skills — **local only** |
| Orama runtime registry | `bin/orama-system/config/agent_registry.json` | 7-stage pipeline + OpenClaw SOUL paths |

## Staging rules

1. **Integrative merge:** `bin/agents/*/SOUL.md` holds the **Oramasys overlay distillate** extracted from live OpenClaw SOUL files — not a full copy of OpenClaw template prose.
2. **Hermes install:** Future `install_hermes_profiles.py` syncs **SOUL only** by default; never overwrite operator `MEMORY.md` / `USER.md` without `--force-memory`.
3. **Harness separation:** LAN/coord/queue scripts stay in `bin/orama-system/skills/hermes-harness/`; do not duplicate persona bodies into harness references.
4. **Path hygiene:** Tracked files use `$ORAMA_SYSTEM_PATH`, `$PERPETUA_TOOLS_PATH`, `$HERMES_HOME`, `${HOME}` — no workstation-specific absolute paths.

## Plans

- [`docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md`](../../docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md) — review gate before execution
- [`docs/plans/2026-07-26-hermes-agent-canonical-staging-and-profile-install.md`](../../docs/plans/2026-07-26-hermes-agent-canonical-staging-and-profile-install.md) — installer implementation plan

## Validation (staging only)

```bash
cd "$ORAMA_SYSTEM_PATH"
test -f bin/agents/REGISTRY.yml
python3 -c "import yaml; yaml.safe_load(open('bin/agents/REGISTRY.yml'))"
for d in orchestrator context architect refiner executor verifier crystallizer coder mac-researcher win-researcher autoresearcher; do
  test -f "bin/agents/$d/SOUL.md" || echo "MISSING SOUL: $d"
done
```
