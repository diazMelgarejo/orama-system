# Hermes + OpenClaw agent staging — review gate (2026-07-26)

> **Reality checkpoint — verified 2026-07-27:** On the review host, Hermes **v0.19.0 (2026.7.20)** runs at `$HERMES_HOME`; `default` is the only active profile and `$HERMES_HOME/profiles/` remains absent. Staged `bin/agents/` records are not live profile evidence. Any install/cutover must first run the installer in dry-run/verify mode, then confirm with `hermes profile list`; retain native `hermes backup` / `hermes import` as the recovery baseline. Use `$ORAMA_SYSTEM_PATH` in portable commands. See [official CLI docs](https://hermes-agent.nousresearch.com/docs/reference/cli-commands).
> **Status:** ✅ **SHIPPED** (2026-07-26) with security hardening follow-up (`cursor/hermes-staging-security-hardening-f559`)  
> **Owner:** orama-system `bin/agents` + `docs/plans/`  
> **Supersedes for execution order:** install hooks are live; residual checklist items tracked below.

## Autoplan security review (Gstack-aligned, 2026-07-26)

**AFRP:** Type C | Practitioner | Mode 2  
**Scope:** Close Hermes/OpenClaw staging review gate vs shipped install hooks without losing operator content.

| Layer | Prevent | Runtime guard | Verify |
|-------|---------|---------------|--------|
| LAN topology | `repo_hygiene` LINT-013 on config + docs | `${env:LM_STUDIO_*}` in `agent_registry.json` | pre-commit `repo_hygiene.py` |
| Overlay writes | REGISTRY allowlist (`~/.openclaw/agents`, `~/.alphaclaw/.../workspace`) | `sync_openclaw_overlay_from_staging.sh` path check | manual `--dry-run` |
| Profile install | slug regex + profiles-root containment | `verify_trusted_install.py` before sync | `tests/test_hermes_profiles.py` |
| Memory stubs | harmonize + `.orama-profile-backup-*` | never blind `--force-memory` overwrite | harmonize test |
| Install hooks | `ORAMA_SKIP_HERMES_SYNC` / `ORAMA_TRUST_HERMES_SYNC` | `install.sh` trusted-checkout gate | operator Win 3080/5080 smoke |

**Security invariants (non-negotiable):**

1. Private RFC1918 / link-local IPs are **never committed** — affinity slugs (`win-rtx3080`, `win-rtx5080`) only.
2. Hermes/OpenClaw materialization requires **trusted main** or explicit `ORAMA_TRUST_HERMES_SYNC=1`.
3. Operator-owned SOUL/memory files are **never replaced** — integrative merge + backup only.
4. OpenClaw overlay sync writes **only** under allowlisted workspace roots.

**Residual operator actions (3080 / 5080):**

- [ ] RTX 5080 fresh: `git fetch origin main && git pull --ff-only` → `install.ps1` → `hermes doctor`
- [ ] RTX 3080 existing: `install-hermes-harness.ps1` (expect "already synced"; use `-TrustHermesSync` on feature branches)
- [ ] `bin/agents/REGISTRY.yml` ↔ live `docs/oramasys/REGISTRY.yml` parity check
- [ ] Optional: `ORAMA_VERIFY_COMMIT_SIG=1` + `ORAMA_ALLOWED_GPG_FINGERPRINTS` when GPG-signed `origin/main` is policy

**Pre-commit / CI gates (3080 / 5080 / LAN):**

- `scripts/hooks/no_committed_lan_topology.py` — blocks RFC1918 literals in `config/` and `bin/*/config/` JSON/YAML
- Affinity slugs `win-rtx3080` / `win-rtx5080` remain valid in tracked config; endpoint URLs use `${env:LM_STUDIO_*_ENDPOINTS}`

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
| [`2026-07-26-hermes-openclaw-staging-execution.md`](2026-07-26-hermes-openclaw-staging-execution.md) | OpenClaw flesh-out execution log (2026-07-26) |
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

- [x] Relay-parity adapters staged in `bin/agents/` (cole, hermes-monitor, sage, relay, nova, rex)
- [x] Atlas lifecycle distillate at `bin/agents/lifecycle/` (no Hermes profile)
- [x] Win `install.ps1` + `install-hermes-harness.ps1` wired (2026-07-26)
- [x] OpenClaw overlay sync script shipped; run on Mac operator host
- [ ] `bin/agents/REGISTRY.yml` matches live `docs/oramasys/REGISTRY.yml` agent ids and display names
- [ ] Each pipeline role has `SOUL.md` distillate consistent with live OpenClaw overlay
- [ ] `codex-agent` ↔ `verifier/` staging mapping accepted (Vera universal gate)
- [ ] `coder` ↔ `executor/` dual-folder mapping accepted (OpenClaw id vs orama registry id)
- [ ] No secrets, workstation paths, or private literals in staged files
- [ ] Hermes Win operator confirms `%LOCALAPPDATA%\hermes` profile layout matches planned slugs
- [ ] PT operator confirms lessons recorded after migration (Phase 6 — not this commit)

**Approve execution:** comment `approve staging` on PR or reply to operator with explicit go-ahead.

## Explicit non-actions (Win phase — still pending)

- No `hermes claw migrate` or `hermes claw cleanup` on Win hosts until operator dry-run + backup
- No PT lesson ledger Phase 6 entries until Win validation green

## Shipped with security hardening (2026-07-26)

- Win `install.ps1` + `install-hermes-harness.ps1` — wired with trusted-checkout gate (`-SkipHermesSync` / `-TrustHermesSync`)
- `verify_trusted_install.py` + `ORAMA_SKIP_HERMES_SYNC` / `ORAMA_TRUST_HERMES_SYNC` / optional `ORAMA_VERIFY_COMMIT_SIG`
- `repo_hygiene` LINT-013 extended to JSON/config (private IPs blocked; affinity slugs OK)
- `scripts/hooks/no_committed_lan_topology.py` — dedicated pre-commit hook for config LAN topology
- `config/mac-orchestrator.json` — Win LMS `baseUrl` uses `${env:LM_STUDIO_WIN_ENDPOINTS}/v1` (no committed IP)
- Overlay + profile installers: path allowlist / slug validation / memory harmonize

## Completed in OpenClaw flesh-out (2026-07-26)

- `install_hermes_profiles.py` — wired in `install.sh` + Win harness (trusted gate)
- `sync_openclaw_overlay_from_staging.sh` — integrative merge live → staging overlays applied to operator OpenClaw SOUL files
- Adapter + lifecycle `bin/agents/` folders and persona YAML catalog

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
