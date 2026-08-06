# `bin/agents` — canonical persona staging (OpenClaw + Hermes)

> **Status:** OpenClaw flesh-out complete (2026-07-26). Win `install.ps1` profile hooks **deferred** until RTX 3080/5080 push.

## What lives here

| Artifact | Purpose | Consumed by |
|----------|---------|-------------|
| `REGISTRY.yml` | Maps staging folder ↔ OpenClaw id ↔ Hermes profile slug ↔ orama `soul_id` | `install_hermes_profiles.py`, overlay sync, humans |
| `{role}/SOUL.md` | Persona overlay distillate (no OpenClaw Core Truths block) | Hermes profiles, OpenClaw overlay sync |
| `{role}/agent.md` | Claude Code / OpenClaw subagent card (YAML frontmatter) | `install-multi-agent.sh`, `.claude/agents/` |
| `personas/*.yaml` | Raft persona catalog (git SSoT) | Hub mirror + docs |
| `templates/profile/` | Hermes profile USER/MEMORY stubs | `install_hermes_profiles.py` |
| `orchestrator/*.py`, `dispatcher.py` | L3 planning/dispatch code | Python runtime (not copied to Hermes) |

## Staged roles (2026-07-26)

**Pipeline:** orchestrator, context, architect, refiner, executor, verifier, crystallizer  
**Research:** mac-researcher, win-researcher, autoresearcher  
**Win LM path:** coder (`coder-win` profile)  
**Adapters:** cole, hermes-monitor, sage, relay-cursor, relay, nova, rex
**Lifecycle:** lifecycle (Atlas / `main` — no Hermes profile)

## Live sources (read-only, not git)

| Layer | Authoritative live map | Notes |
|-------|------------------------|-------|
| OpenClaw fleet (17 agents) | `${HOME}/.alphaclaw/.openclaw/workspace/docs/oramasys/REGISTRY.yml` | MERGE-10 + EDITED-03 |
| OpenClaw per-agent SOUL | `${HOME}/.openclaw/agents/<id>/SOUL.md` | Core Truths + overlay section |
| Atlas hub | `${HOME}/.alphaclaw/.openclaw/workspace` | `main` agent |
| Hermes portable brain | `$HERMES_HOME/` | Profiles — **local only** |
| Orama runtime registry | `bin/orama-system/config/agent_registry.json` | 7-stage pipeline |

## Operator commands

```bash
# Refresh OpenClaw overlays from staging (integrative merge)
./scripts/sync_openclaw_overlay_from_staging.sh

# Hermes profiles (when HERMES_HOME exists)
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --install --verify
```

## Staging rules

1. **Integrative merge:** `bin/agents/*/SOUL.md` holds overlay distillates — not full OpenClaw template prose.
2. **Hermes install:** `install_hermes_profiles.py` syncs SOUL by default; never overwrite operator MEMORY/USER without `--force-memory`.
3. **Harness separation:** LAN/coord scripts stay in `hermes-harness/`; persona bodies do not duplicate into harness references.
4. **Path hygiene:** `$ORAMA_SYSTEM_PATH`, `$PERPETUA_TOOLS_PATH`, `$HERMES_HOME`, `${HOME}` — no workstation literals.

## Plans

- [`docs/plans/2026-07-26-hermes-openclaw-staging-execution.md`](../../docs/plans/2026-07-26-hermes-openclaw-staging-execution.md) — OpenClaw phase log
- [`docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md`](../../docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md) — review gate
- [`docs/plans/2026-07-26-hermes-agent-canonical-staging-and-profile-install.md`](../../docs/plans/2026-07-26-hermes-agent-canonical-staging-and-profile-install.md) — Win install hooks (deferred)

## Validation

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 -c "import yaml; yaml.safe_load(open('bin/agents/REGISTRY.yml'))"
for d in orchestrator context architect refiner executor verifier crystallizer coder \
  mac-researcher win-researcher autoresearcher cole hermes-monitor sage relay-cursor relay nova rex lifecycle; do
  test -f "bin/agents/$d/SOUL.md" || echo "MISSING SOUL: $d"
done
```
