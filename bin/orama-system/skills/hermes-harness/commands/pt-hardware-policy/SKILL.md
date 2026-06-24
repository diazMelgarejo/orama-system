---
name: pt-hardware-policy
description: >-
  Validate model↔hardware affinity using Perpetua-Tools canonical policy before
  Hermes dispatches to LM Studio on Windows. Never infer NEVER_MAC/NEVER_WIN
  rules independently — consume PT policy only.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, windows, openclaw
parent_skill: hermes-harness
triggers:
  - pt-hardware-policy
  - hardware policy
  - NEVER_MAC
  - check-openclaw
allowed-tools: bash, file-operations
---

# PT Hardware Policy (Hermes / Windows)

Hermes on Windows is the **local orchestrator counterpart** to Mac OpenClaw.
Both harnesses consume the **same** Perpetua-Tools policy — they must not
invent affinity rules at runtime.

## Canonical sources (one-way import)

| Layer | Path (Perpetua-Tools) |
|-------|------------------------|
| Policy SSoT | `config/model_hardware_policy.yml` |
| Canonical API | `src/utils/hardware_policy.py` |
| CLI validation | `scripts/hardware_policy_cli.py` |
| Agent playbook | `.claude/skills/hardware-policy/SKILL.md` |

orama-system **references** PT; it never re-declares NEVER lists in Hermes skills.

## Windows role reversal

On the Windows 11 Hermes host:

- **LM Studio** is `http://localhost:1234` (`lmstudio-win` in `openclaw.json`)
- **windows_only** models (27B GGUF, gemma quant) are **allowed here** — this is their physical home
- **mac_only** / MLX models are **NEVER_WIN** on this host
- Hermes acts as de facto local orchestrator and/or autoresearcher parallel to Mac orchestrator

On Mac/Linux OpenClaw hosts the mirror applies: Mac MLX safe, Win GGUF is NEVER_MAC.

## Procedure (run before LM Studio dispatch)

From **orama-system repository root** on Windows. Path resolution order:
[`../../references/workspace-path-resolution.md`](../../references/workspace-path-resolution.md).

```powershell
# Preferred — full gate (list + openclaw.json check)
.\platform\windows\start.ps1 --hardware-policy

# Direct PT CLI only when launcher unavailable (PERPETUA_TOOLS_PATH or PT_HOME)
$PtDir = if ($env:PERPETUA_TOOLS_PATH) { $env:PERPETUA_TOOLS_PATH } else { $env:PT_HOME }
python (Join-Path $PtDir 'scripts\hardware_policy_cli.py') --check-openclaw
python (Join-Path $PtDir 'scripts\hardware_policy_cli.py') --validate "gemma-4-26B-A4B-it-Q4_K_M" win
```

After `.\platform\windows\install.ps1` writes `openclaw.json` defaults (`lmstudio-win` → localhost:1234),
always run `--check-openclaw` before trusting model assignments.

## Rules for Hermes agents

1. **Never infer** NEVER_MAC / NEVER_WIN from `/v1/models` list membership alone.
2. **Never duplicate** YAML parsers or affinity logic in Hermes local skills.
3. **Always delegate** to `utils.hardware_policy` via CLI or Python import from PT.
4. When editing `openclaw.json` on Windows, assign heavy GGUF models to `lmstudio-win` only.
5. For autoresearcher on Windows: PT `autoresearch_bridge` + hardware policy must pass before GPU dispatch.

## Related

- [`../../references/workspace-path-resolution.md`](../../references/workspace-path-resolution.md)
- [`../../SKILL.md`](../../SKILL.md) § Platform Harness Model
- [`../../../../../../docs/wiki/15-hermes-windows-harness.md`](../../../../../../docs/wiki/15-hermes-windows-harness.md)
- PT [`hardware-policy`](../../../../../../../Perpetua-Tools/.claude/skills/hardware-policy/SKILL.md) skill (sibling repo)
