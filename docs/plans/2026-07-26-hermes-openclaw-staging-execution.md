# Hermes + OpenClaw staging — OpenClaw execution log (2026-07-26)

> **Status:** ✅ **OpenClaw flesh-out complete** — Win `install.ps1` hooks **deferred**  
> **Parent:** [`2026-07-26-hermes-openclaw-staging-review-gate.md`](2026-07-26-hermes-openclaw-staging-review-gate.md)

## Scope of this execution

Completed on Mac operator host per user request:

1. Flesh out merged OpenClaw personalities into deduplicated `bin/agents/` counterparts
2. Add persona YAML catalog under `bin/agents/personas/`
3. Ship `install_hermes_profiles.py` (ready for Win; not hooked in `install.ps1` yet)
4. Ship `sync_openclaw_overlay_from_staging.sh` and run on live fleet
5. Add hermes-harness reference cards (portable brain map, migration, profile install)
6. Update `REGISTRY.yml` — all 17 agents mapped; `openclaw_only` emptied

**Deferred:** Windows RTX 3080/5080 `install.ps1` profile hook, `hermes claw migrate` cutover, PT lesson ledger Phase 6.

## Delivered artifacts

| Path | Action |
|------|--------|
| `bin/agents/cole/`, `hermes-monitor/`, `sage/`, `relay/`, `nova/`, `rex/` | NEW — SOUL + agent.md |
| `bin/agents/lifecycle/` | NEW — Atlas distillate (no Hermes profile) |
| `bin/agents/personas/` | NEW — tracked persona YAML catalog |
| `bin/agents/templates/` | NEW — profile stubs + delegation snippet |
| `bin/agents/mac-researcher/SOUL.md` | UPDATED — Arthur persona merge |
| `bin/agents/executor/SOUL.md` | UPDATED — Penn alias note |
| `bin/agents/REGISTRY.yml` | UPDATED — adapter + lifecycle rows |
| `scripts/sync_openclaw_overlay_from_staging.sh` | NEW |
| `bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py` | NEW |
| `hermes-harness/references/hermes-portable-brain-map.md` | NEW |
| `hermes-harness/references/openclaw-to-hermes-migration.md` | NEW |
| `hermes-harness/references/hermes-profile-install.md` | NEW |

## Operator verification

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 -c "import yaml; yaml.safe_load(open('bin/agents/REGISTRY.yml'))"
./scripts/sync_openclaw_overlay_from_staging.sh --dry-run
pytest tests/test_hermes_profiles.py -q
```

On Win (after push):

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_profiles.py --install --verify
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install --verify
```

## Next (Win Hermes phase)

1. Wire `install_hermes_profiles.py` into `platform/windows/install.ps1`
2. Run on RTX 3080 and 5080 after `git pull`
3. `hermes claw migrate` dry-run on Win OpenClaw roots
4. Reconcile gap archive vs `REGISTRY.yml`
5. PT `.agent` lesson entries (Phase 6)
