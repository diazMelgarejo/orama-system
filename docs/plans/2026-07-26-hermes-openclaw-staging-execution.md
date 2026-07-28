# Hermes + OpenClaw staging — OpenClaw execution log (2026-07-26)

> **Reality checkpoint — verified 2026-07-27:** This is an execution log for staged content, not proof that the described profiles are installed on this Windows Hermes host. The current instance is Hermes **v0.19.0 (2026.7.20)** at `$HERMES_HOME`; `hermes profile list` reports `default` only and `$HERMES_HOME/profiles/` is absent. Subsequent work must verify staging, installation, and local Hermes runtime state separately. Use `$ORAMA_SYSTEM_PATH` in portable commands and refer to [Hermes configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) for current configuration semantics.
> **Status:** ✅ OpenClaw flesh-out + Win idempotent harness sync wired (2026-07-26)  
> **Security hardening:** ✅ `cursor/hermes-staging-security-hardening-f559` (2026-07-26)  
> **Parent:** [`2026-07-26-hermes-openclaw-staging-review-gate.md`](2026-07-26-hermes-openclaw-staging-review-gate.md)

## Gstack / AutoPlan cross-review (2026-07-26)

Method: CEO → Engineering → DX → Final gate (per `garrytan/gstack/autoplan/SKILL.md`; applied from canonical text — Gstack not installed in agent shell).

| Review lens | Verdict | Evidence |
|-------------|---------|----------|
| **CEO / premise** | Approve hardening scope; defer `hermes claw migrate` until operator smoke on 3080/5080 | Review gate §Explicit non-actions; no fleet cutover in this PR |
| **Engineering** | Findings 1–3 closed in code; 4+6 closed via integrative merge + trust gate | `repo_hygiene` LINT-013 config scan; overlay allowlist; slug validation; `harmonize-memory`; `verify_trusted_install.py` |
| **DX** | Env contract documented; Win PS1 mirrors `install.sh` skip/trust flags | `ORAMA_SKIP_HERMES_SYNC`, `ORAMA_TRUST_HERMES_SYNC`, `ORAMA_VERIFY_COMMIT_SIG`, `ORAMA_ALLOWED_GPG_FINGERPRINTS` |
| **Final gate** | **Ship** security PR; operator checklist remains open | RTX 5080 fresh + 3080 re-sync smoke still manual |

### Security invariants (call-out — both docs must agree)

1. **Never commit LAN IPs** — affinity slugs (`win-rtx3080`, `win-rtx5080`) only; endpoints via `${env:LM_STUDIO_*}` or `last_discovery.json`.
2. **Never blind-overwrite operator content** — SOUL overlays integrative-merge; memory stubs harmonize + `.orama-profile-backup-*`.
3. **Trusted checkout before materialization** — `origin/main` SHA match on `main`, or `ORAMA_TRUST_HERMES_SYNC=1` after human review.
4. **Overlay writes allowlisted** — `~/.openclaw/agents`, `~/.alphaclaw/.openclaw/workspace` only.

### Integrative merge doctrine (Finding 4+6)

Per `bin/orama-system/skills/oramasys-method/references/integrative-merge.md` (CIDF rank-1):

| Surface | Canon (git) | Runtime (operator) | Merge rule |
|---------|-------------|-------------------|------------|
| `bin/agents/*/SOUL.md` | L3 staging distillates | OpenClaw `## Oramasys role overlay` | Overlay script **replaces overlay section only** — Core Truths preserved |
| `$HERMES_HOME/profiles/*/SOUL.md` | Same distillates | Hermes profile trees | Managed marker + skip unmanaged |
| `USER.md` / `MEMORY.md` stubs | `templates/profile/` | Operator memories | `--harmonize-memory` append + backup; no `--force-memory` blind write |
| `agent_registry.json` gateways | Env placeholders | `discover.py` / `start.sh` | Never commit `192.168.*` literals |

**Conflict policy:** If harmonize would drop operator prose, installer skips (user-owned marker) or operator sets `ORAMA_TRUST_HERMES_SYNC=1` after manual diff review.

### AI security scanner

No dedicated AI-agent security scanner is installed in this environment (see [awesome-ai-security-tools](https://github.com/scadastrangelove/awesome-ai-security-tools)). Gates in this PR substitute: `repo_hygiene`, `verify_trusted_install`, pre-commit `no_committed_lan_topology.py`, pytest contract tests.

### Residual risks (honest)

| Risk | Severity | Mitigation shipped | Operator action |
|------|----------|-------------------|-----------------|
| REGISTRY.yml ↔ live `docs/oramasys/REGISTRY.yml` drift | Low | Review checklist open | Manual parity pass |
| `config/mac-orchestrator.json` env expansion depends on OpenClaw `${env:}` support | Low | Placeholder + comment | Verify on Mac operator host |
| Feature-branch install blocked by trust gate | By design | `ORAMA_TRUST_HERMES_SYNC=1` | Use only after reviewing `bin/agents` diff |

## Scope of this execution

Completed on Mac operator host per user request:

1. Flesh out merged OpenClaw personalities into deduplicated `bin/agents/` counterparts
2. Add persona YAML catalog under `bin/agents/personas/`
3. Ship `install_hermes_profiles.py` (ready for Win; hooked in `install.ps1` / `install.sh`)
4. Ship `sync_openclaw_overlay_from_staging.sh` and run on live fleet
5. Add hermes-harness reference cards (portable brain map, migration, profile install)
6. Update `REGISTRY.yml` — all 17 agents mapped; `openclaw_only` emptied

**Deferred:** `hermes claw migrate` cutover, PT lesson ledger Phase 6 (operator validation first).

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
| `scripts/sync_openclaw_overlay_from_staging.sh` | NEW + allowlist + trust gate |
| `bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py` | NEW + slug/harmonize/trust |
| `scripts/review/verify_trusted_install.py` | NEW — SHA-aligned main + optional GPG |
| `scripts/hooks/no_committed_lan_topology.py` | NEW — pre-commit 3080/5080 IP gate |
| `hermes-harness/references/hermes-portable-brain-map.md` | NEW |
| `hermes-harness/references/openclaw-to-hermes-migration.md` | NEW |
| `hermes-harness/references/hermes-profile-install.md` | NEW + harmonize docs |

## Idempotent sync (2026-07-26)

- `install_hermes_profiles.py --sync` — verify distillate body first; skip when profiles already match `bin/agents`
- `install-hermes-harness.ps1` — Hermes detected → wire/sync only; thin wrappers verify-first; `-SkipHermesSync` / `-TrustHermesSync`
- Re-run on RTX 3080 with existing profiles: expect `already synced` / `profiles already synced with bin/agents staging`

## Operator verification

On **trusted `main`** (all three fleet nodes after `git pull --ff-only`):

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 -c "import yaml; yaml.safe_load(open('bin/agents/REGISTRY.yml'))"
python3 scripts/hooks/no_committed_lan_topology.py
python3 scripts/review/verify_trusted_install.py
./scripts/sync_openclaw_overlay_from_staging.sh --dry-run
pytest tests/test_hermes_profiles.py tests/test_verify_trusted_install.py -q
bash install.sh   # Hermes sync runs when verify_trusted_install passes
```

On a **feature branch** (e.g. PR #222 stack before merge): verifier fails by design — review `bin/agents`, then either skip materialization or override:

```bash
# skip Hermes profile/thin-wrapper sync (skill install still runs)
export ORAMA_SKIP_HERMES_SYNC=1
bash install.sh

# or after human review of bin/agents diff:
export ORAMA_TRUST_HERMES_SYNC=1
bash install.sh
```

On Win (after `git pull --ff-only` on `main`):

```powershell
powershell -File .\platform\windows\install-hermes-harness.ps1 -RunDoctor
# feature branch after reviewing bin/agents:
powershell -File .\platform\windows\install-hermes-harness.ps1 -TrustHermesSync
```

## Pre-merge checklist (single-operator, 3-node LAN)

Run on **Mac orchestrator**, **RTX 3080**, and **RTX 5080** before merging PR #222:

| Step | Mac | Win 3080 / 5080 |
|------|-----|-----------------|
| Mesh Phase A backup | `bash scripts/mesh/backup-mesh-local-cache.sh` (or Win mesh script) | same via harness |
| Pull trusted main | `git pull --ff-only` | `git pull --ff-only` |
| Trust gate | `python3 scripts/review/verify_trusted_install.py` → pass | same on Win with Python |
| Hermes smoke | `bash install.sh` or harness PS1 | `install-hermes-harness.ps1 -RunDoctor` |
| Expect | `profiles already synced` / thin wrappers verified | same |
| CI parity (optional local) | `bash scripts/ci/run_agent_security_scans.sh` | skip or run in WSL |

GitHub PR #222 must show **agent-security** workflow green on the PR head commit before merge-last.


## Next (Win Hermes phase)

1. ~~Wire `install_hermes_profiles.py` into `platform/windows/install.ps1`~~ ✅ 2026-07-26
2. On RTX 3080 + 5080 after `git pull`: `install.ps1` or `install-hermes-harness.ps1`
3. `hermes claw migrate` dry-run on Win OpenClaw roots (if applicable)
4. Reconcile gap archive vs `REGISTRY.yml`
5. PT `.agent` lesson entries (Phase 6)
