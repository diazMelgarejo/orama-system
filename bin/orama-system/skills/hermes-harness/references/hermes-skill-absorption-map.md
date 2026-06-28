# Hermes Skill Absorption Map

> **Status:** ✅ Complete on `main` (2026-06-28, audit follow-up). Hermes-local skills
> are thin adapters; durable behavior lives in orama-system canonical cards below.
>
> Inventory audit: [`hermes-ecc-fork-inventory.md`](hermes-ecc-fork-inventory.md)  
> Onboarding plan: [`docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md`](../../../../docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md) § Skill Absorption

## Redirect stubs → canonical supersets

| Hermes / legacy slug | State | Canonical target | Act by loading |
|----------------------|-------|------------------|----------------|
| `hermes-agent` | Redirect | `hermes-harness` | `bin/orama-system/skills/hermes-harness/SKILL.md` |
| `pt-orama-harness-integration` | Redirect | `hermes-harness` | same |
| `perpetua-hardware` | Redirect | `hardware-affinity-gate` | `bin/orama-system/skills/hardware-affinity-gate/SKILL.md` |
| `local-inference` | Redirect | `hardware-affinity-gate` | same (via `perpetua-hardware` stub chain) |

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

`.agents/perpetua-hardware` points at **hardware-affinity-gate**, not `Perpetua-Tools/hardware/`.

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
| Perpetua-Tools runtime SSoT | Policy YAML + Python API | PT `config/model_hardware_policy.yml` (one-way import) |
| Hermes validator fork | Post-edit size guard | `hardware-affinity-gate/SKILL.md` § Post-Edit Validation |

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
