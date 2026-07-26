# Hermes + OpenClaw agent staging — review gate (2026-07-26)

> **Status:** 🔍 **REVIEW PENDING** — staged in git for all agents; **no installer execution** until review completes.  
> **Owner:** orama-system `bin/agents` + `docs/plans/`  
> **Supersedes for execution order:** defers implementation until this gate passes.

## Purpose

Commit **today's live fleet reality** (MERGE-10 + EDITED-03, 17 OpenClaw agents) into canonical staging at `bin/agents/`, with plans aligned to Hermes harness thin-wrapper doctrine — **for multi-agent review before** `install_hermes_profiles.py`, `install.ps1` hooks, or `hermes claw migrate` cutover.

## Current reality snapshot (2026-07-26)

### OpenClaw (live Mac operator host)

| Check | State |
|-------|--------|
| Registered agents in `openclaw.json` | **17** (`main` + 16 workers/adapters) |
| Fleet hub | `${HOME}/.alphaclaw/.openclaw/workspace/docs/oramasys/` |
| Machine registry | `docs/oramasys/REGISTRY.yml` (`merge-10-edited03`) |
| Pipeline chain | Cass → Aria → Sena → Rourke → Vera → Crystal |
| Vera invariant | `codex-agent` id (not separate `verifier-agent` OpenClaw id) |
| Relay parity | `cole-agent`, `hermes-agent`, `kimi-agent`, `grok-agent` |
| SOUL overlays | Live under `${HOME}/.openclaw/agents/<id>/SOUL.md` with `## Oramasys role overlay` |

### Hermes (this Mac — staging target)

| Check | State |
|-------|--------|
| `hermes` CLI on PATH | Not verified / not required for this commit |
| `$HERMES_HOME/profiles/` | **Empty / absent** on review host — profiles not yet materialized |
| Thin command wrappers | `install_hermes_thin_skills.py` (skills only — **shipped**) |
| Profile installer | **Planned** — see implementation plan below |

### orama-system (canonical git staging)

| Artifact | State |
|----------|--------|
| `bin/agents/REGISTRY.yml` | **NEW** — maps staging folder ↔ OpenClaw id ↔ Hermes profile |
| `bin/agents/*/SOUL.md` | **UPDATED** — overlay distillates from live OpenClaw SOUL (2026-07-26) |
| `bin/orama-system/config/agent_registry.json` | Existing 7-stage runtime registry (unchanged this commit) |
| `bin/orama-system/skills/hermes-harness/` | Operational harness + thin skill installer (unchanged this commit) |

## Three layers (do not conflate)

```text
L3  orama-system/bin/agents/     ← persona distillates (THIS COMMIT)
L1  $HERMES_HOME/profiles/        ← materialized by future installer
L2  Perpetua-Tools/.agent/       ← project lessons only (not persona SSoT)
```

Harness ops (LAN, coord pulse, peer inbox) remain in `hermes-harness/` — not duplicated into `bin/agents/`.

## Plan index (canonical `docs/plans/`)

| Plan | Role |
|------|------|
| **This file** | Review gate + live snapshot |
| [`2026-07-26-hermes-agent-canonical-staging-and-profile-install.md`](2026-07-26-hermes-agent-canonical-staging-and-profile-install.md) | Implementation: `install_hermes_profiles.py`, install hooks, reference cards |
| [`2026-06-24-hermes-harness-canonical-onboarding.md`](2026-06-24-hermes-harness-canonical-onboarding.md) | Harness absorption + thin-wrapper doctrine (IN PROGRESS) |
| [`2026-06-28-hermes-integration-authority.md`](2026-06-28-hermes-integration-authority.md) | Envelope protocol + thin wrapper inventory |
| [`2026-07-26-hermes-openclaw-migration-operator.md`](2026-07-26-hermes-openclaw-migration-operator.md) | `hermes claw migrate` operator sequence (env-var safe) |

OpenClaw-side drafts (navigation only, not SSoT):

- `OpenClaw/references/Hermes-Harness-Guide-for-Orama+Perpetua.md`
- `OpenClaw/references/2026-07-26_111557-hermes-openclaw-migration-cross-repo-plan.md`
- `OpenClaw/references/raft-Hermes-Plan-09c.md` — adopt thin-wrapper pattern; **defer** PT `hermes_harness.py` until profile install stable

## Review checklist (all agents / operators)

Before approving **Phase 3+ execution** (`install_hermes_profiles.py`, install.ps1 hooks):

- [ ] `bin/agents/REGISTRY.yml` matches live `docs/oramasys/REGISTRY.yml` agent ids and display names
- [ ] Each pipeline role has `SOUL.md` distillate consistent with live OpenClaw overlay
- [ ] `codex-agent` ↔ `verifier/` staging mapping accepted (Vera universal gate)
- [ ] `coder` ↔ `executor/` dual-folder mapping accepted (OpenClaw id vs orama registry id)
- [ ] `openclaw_only` rows (Atlas, relay-parity) — persona_ref paths on hub, not yet in `bin/agents/`
- [ ] No secrets, workstation paths, or private literals in staged files
- [ ] Hermes Win operator confirms `%LOCALAPPDATA%\hermes` profile layout matches planned slugs
- [ ] PT operator confirms lessons recorded after migration (Phase 6 — not this commit)

**Approve execution:** comment `approve staging` on PR or reply to operator with explicit go-ahead.

## Explicit non-actions (this commit)

- No `install_hermes_profiles.py` implementation
- No `hermes claw migrate` or `hermes claw cleanup` on operator hosts
- No overwrite of live OpenClaw SOUL files from git (one-way: live → staging distillate)
- No changes to `orama-system/` or `Perpetua-Tools/` runtime code beyond `bin/agents` staging docs

## Validation commands

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 -c "import yaml; yaml.safe_load(open('bin/agents/REGISTRY.yml'))"
for d in orchestrator context architect refiner executor verifier crystallizer coder mac-researcher win-researcher autoresearcher; do
  test -f "bin/agents/$d/SOUL.md"
done
python3 scripts/review/repo_hygiene.py .
```

## After review — execution order

1. Merge this PR (staging + plans).
2. Implement `install_hermes_profiles.py` per implementation plan.
3. Wire `platform/windows/install.ps1` + mac install hook.
4. Win operator: `hermes backup` → `hermes claw migrate --dry-run` → profile install → verify → optional cleanup.
5. PT: `learn.py` migration lessons.
