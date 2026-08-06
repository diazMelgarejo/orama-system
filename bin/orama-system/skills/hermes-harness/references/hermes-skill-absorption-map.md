# Hermes Skill Absorption Map

> **Status:** ✅ Complete on `main` (2026-06-28, audit follow-up). Hermes-local skills
> are thin adapters; durable behavior lives in orama-system canonical cards below.
>
> Inventory audit: [`hermes-ecc-fork-inventory.md`](hermes-ecc-fork-inventory.md)  
> Onboarding plan: [`docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md`](../../../../../docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md) § Skill Absorption

## Redirect stubs → canonical supersets

| Hermes / legacy slug | State | Canonical target | Act by loading |
|----------------------|-------|------------------|----------------|
| `hermes-agent` | Symlink | `hermes-harness` | `bin/orama-system/skills/hermes-harness/SKILL.md` |
| `pt-orama-harness-integration` | Symlink | `hermes-harness` | same |
| `perpetua-hardware` | Symlink | `hardware-affinity-gate` | `bin/orama-system/skills/hardware-affinity-gate/SKILL.md` |
| `local-inference` | Symlink | `hardware-affinity-gate` | same (via `perpetua-hardware` chain) |
| `no-sleep-chains` | Symlink | `shell-hygiene` | `bin/orama-system/skills/shell-hygiene/SKILL.md` |
| `perpetua-tools` | Redirect stub (cross-repo) | [`SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/SKILL.md) | GitHub `main`; local agents resolve to checkout |
| `perpetua-config` | Redirect stub (cross-repo) | [`config/SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md) | GitHub `main`; local agents resolve to checkout |
| `perpetua-startup-intelligence` | Redirect stub (cross-repo) | [`hardware/startup-intelligence/SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/hardware/startup-intelligence/SKILL.md) | GitHub `main`; local agents resolve to checkout |
| `windows-hermes-setup` | Redirect | `commands/windows-hermes-setup` + `references/windows-hermes-setup.md` | `bin/orama-system/skills/hermes-harness/commands/windows-hermes-setup/SKILL.md` |
| `hermes-harness` (Hermes-local fork) | Redirect | `hermes-harness/SKILL.md` + references below | `install_hermes_thin_skills.py` replaces `~/.hermes/skills/hermes-harness/` with redirect stub |
| `hermes-harness` (Hermes-local fork) | Redirect | `hermes-harness/SKILL.md` | `bin/orama-system/skills/hermes-harness/SKILL.md` — `install_hermes_thin_skills.py` replaces forked `~/.hermes/skills/hermes-harness/` |

## Superseded archive (do not use)

| Archive slug | State | Superseded by | Win LM Studio coder (canonical) |
|--------------|-------|---------------|----------------------------------|
| `archive/llm-council-orchestration-absorbed` | **SUPERSEDED** | `commands/pt-orama-council` + `references/hermes-council-review-gates.md` | `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` (not invented "Qwen 3.6 Coder") |

Archive path: `bin/orama-system/skills/archive/llm-council-orchestration-absorbed/SKILL.md` — pointer only.

## `.agents` thin wrappers (Codex / repo skills)

| Slug | `.agents` path | Canonical target |
|------|----------------|------------------|
| `hermes-agent` | `.agents/skills/hermes-agent/SKILL.md` | `hermes-harness` |
| `pt-orama-harness-integration` | `.agents/skills/pt-orama-harness-integration/SKILL.md` | `hermes-harness` |
| `local-inference` | `.agents/skills/local-inference/SKILL.md` | `hardware-affinity-gate` |
| `perpetua-hardware` | `.agents/skills/perpetua-hardware/SKILL.md` | `hardware-affinity-gate` (orama methodology) |
| `hermes-harness` | `.agents/skills/hermes-harness/SKILL.md` | `hermes-harness` |

**Dual-layer hardware routing:**

| Layer | Where | Role |
|-------|-------|------|
| orama methodology | `hardware-affinity-gate` | PREFER/ALLOW/NEVER, canaries, Hermes launchers |
| PT runtime SSoT | `$PERPETUA_TOOLS_PATH` policy YAML + `hardware_policy_cli.py` | Enforcement at dispatch |
| Hermes edge | `commands/pt-hardware-policy` | Windows Hermes → PT CLI |

`.agents/perpetua-hardware` points at **hardware-affinity-gate**, not the PT
[`hardware/`](https://github.com/diazMelgarejo/Perpetua-Tools/tree/main/hardware) skill tree.

## Absorbed into `hermes-harness` (superset)

| Source | Absorbed content | Canonical location |
|--------|------------------|-------------------|
| Hermes Agent onboarding | Install, providers, thin wrappers, Windows bring-up | `hermes-harness/SKILL.md` |
| `pt-orama-harness-integration` | Cross-harness protocol, partner dispatch | `references/cross-harness-protocol.md`, `references/partner-prompt-contract.md` |
| `llm-council-orchestration` (archive) | Council gates + protocol | `commands/pt-orama-council/SKILL.md`, `references/hermes-council-review-gates.md` |
| `pt-orama-council` (fork) | Council safety gates | same |
| `pt-orama-review` | Review command | `commands/pt-orama-review/SKILL.md` |
| `pt-orama-delegate` | Delegate command | `commands/pt-orama-delegate/SKILL.md` |
| Windows harness | Install, canaries, PATH, OpenClaw optional | `platform/windows/*`, `references/win-localhost-runtime-checklist.md` |
| `windows-hermes-setup` (Hermes self-improve) | PATH, ECC doctor, partner CLI, start.ps1 comms | `commands/windows-hermes-setup/SKILL.md`, `references/windows-hermes-setup.md` |
| `hermes-harness` (Hermes-local fork, 2026-07-23) | Plan integration rules, LAN coord ops, board-update comms stub | `references/plan-integration.md`, `references/lan-peer-coordination.md`, `references/update-all-agents-comms.md`, `SKILL.md` § Plan integration |
| Hardware policy (Hermes edge) | PT one-way import, Win role reversal | `commands/pt-hardware-policy/SKILL.md` |
| Codex dispatch | v0.142 profiles, runtime paths | [`../../../references/codex-cli-v142-dispatch.md`](../../../references/codex-cli-v142-dispatch.md) |

## Absorbed into `skillify` (superset)

| Source | Absorbed content | Canonical location |
|--------|------------------|-------------------|
| `hermes-agent-skill-authoring` | ECC cross-harness authoring | `skillify/references/ecc-cross-harness-authoring.md` |
| ECC skill template | Harness adapter checklist | same |
| Hermes validator fork | Post-create YAML/size guards | `skillify/SKILL.md` § Validator constraints |
| Codex thin installs | Wrapper-only policy | `skillify/references/codex-thin-wrapper-installs.md` |

## Absorbed into `hardware-affinity-gate` (superset)

| Source | Absorbed content | Canonical location |
|--------|------------------|-------------------|
| `local-inference` | LM Studio/Ollama affinity, canary thresholds | `hardware-affinity-gate/SKILL.md` |
| `perpetua-hardware` (orama redirect) | PREFER/ALLOW/NEVER semantics | same |
| Perpetua-Tools runtime SSoT | Policy YAML + Python API | [`config/model_hardware_policy.yml`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/model_hardware_policy.yml) (one-way import) |
| Hermes validator fork | Post-edit size guard | `hardware-affinity-gate/SKILL.md` § Post-Edit Validation |

## bin/agents persona staging (2026-07-26)

| Source | Absorbed content | Canonical location |
|--------|------------------|-------------------|
| OpenClaw live SOUL overlays | Oramasys overlay distillates | `bin/agents/*/SOUL.md` |
| Raft persona YAML (EDITED-03) | Persona catalog | `bin/agents/personas/*.yaml` |
| OpenClaw graft audit (2026-08-04) | Dispatch taxonomy + lane tags + path doctrine | `references/hermes-dispatch-taxonomy.md`, `references/openclaw-workspace-path-doctrine.md`, `references/openclaw-pattern-graft-registry.md`, `bin/agents/REGISTRY.yml` `dispatch_lane` |
| Hermes profile materialization | Profile SOUL + memory stubs | `scripts/install_hermes_profiles.py` |
| OpenClaw overlay refresh | Integrative merge from staging | `scripts/sync_openclaw_overlay_from_staging.sh` |

Reference cards: `references/hermes-portable-brain-map.md`, `references/openclaw-to-hermes-migration.md`, `references/hermes-profile-install.md`

## Keep separate (not absorbed)

| Skill | Reason |
|-------|--------|
| `pt-orama-council` / `review` / `delegate` **commands** | User-facing slash commands — bodies under `hermes-harness/commands/` |
| `codex-openclaw-agent` | OpenClaw-specific Codex sub-agent binding |
| `plan`, `systematic-debugging`, `requesting-code-review` | Adjacent ECC skills, not Hermes harness |
| PT `.claude/skills/hardware-policy` | Runtime SSoT in Perpetua-Tools (orama references, never copies) |

## Local Hermes install (thin only)

Regenerate — never hand-edit canonical bodies in `~/.hermes/skills/pt-orama/`:

```bash
python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
```

Wrappers must contain `created_by: agent` marker; user wrappers are never clobbered.

**Curator pin (agent-created skills):** After absorbing a Hermes self-improve skill into
canonical orama, pin the local copy so background self-improve does not re-patch it:

```powershell
hermes curator pin windows-hermes-setup
hermes curator pin hermes-harness
```

Local `~/.hermes/skills/software-development/windows-hermes-setup/` should be a
`status: absorbed` redirect only — never a second skill body.

Local `~/.hermes/skills/hermes-harness/SKILL.md` must be a redirect stub after
`install_hermes_thin_skills.py --install`. Orphaned local `references/*.md` copies
are removed when canonical orama paths exist (see script `HARNESS_ORPHAN_REFERENCES`).

## Codex / `.agents` policy

- **Canonical:** `bin/orama-system/skills/<name>/SKILL.md`
- **Repo wrapper:** `.agents/skills/<name>/SKILL.md` — thin pointer only
- **Never** paste full canonical bodies into `.agents/` or `~/.codex/skills/`

## Verification

```bash
# Redirect stubs have no procedure beyond pointer
grep -l "REDIRECT\|SUPERSEDED" bin/orama-system/skills/*/SKILL.md bin/orama-system/skills/archive/*/SKILL.md

# Thin Hermes wrappers
python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify

# Hardware policy one-way import (from orama root)
./start.sh --hardware-policy          # Mac
.\platform\windows\start.ps1 --hardware-policy   # Windows
```
