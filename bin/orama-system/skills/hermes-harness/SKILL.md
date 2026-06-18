---
name: hermes-harness
description: >-
  Onboards Hermes Agent as a cross-harness operator shell for PT-orama and ECC
  workflows. Use when installing Hermes, importing ECC/orama skills into Hermes,
  configuring Nous Portal or LM Studio providers, adding Hermes beside OpenClaw,
  or dispatching Hermes, Gemini, AGY, and Codex CLI coding partners.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, codex, claude-code, windows, openclaw, ecc
parent_skill: orama-system
origin: ECC Hermes setup, Hermes/OpenClaw migration, and cross-harness docs
triggers:
  - hermes setup
  - hermes onboarding
  - nous portal
  - hermes openclaw migration
  - ecc harness
  - cross-harness
  - install codex cli on windows
allowed-tools: bash, file-operations, web-search
---

# Hermes Harness

## Purpose
Use Hermes as an operator shell that consumes durable PT-orama/ECC skills,
prompts, MCP conventions, and cross-harness rules. Keep OpenClaw as the runtime gateway/agent fabric.

## When to Use
- A Windows or Mac operator needs Hermes installed or repaired.
- Hermes must consume orama/OpenClaw/ECC skills without copying private state.
- Nous Portal, LM Studio, OpenRouter, Gemini, AGY, or Codex CLI are being wired as coding partners.
- A Hermes/OpenClaw artifact must become a reusable skill, command, hook, doc, or issue.

## Operating Thesis
1. **Durable source:** orama-system and ECC own reusable skills and rules.
2. **Harness edge:** Hermes and other tools adapt loading/invocation only at the edge.
3. **No private imports:** never ship raw `~/.hermes`, secrets, personal memory, or account tokens.
4. **Parallel to OpenClaw:** `openclaw-skills` owns OpenClaw config; this skill owns Hermes onboarding and partner prompts.

## Windows Bring-Up
Use PowerShell with explicit UTF-8 when writing files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
```

Default `HERMES_HOME` to `$env:LOCALAPPDATA\hermes`; the repo lives at
`$env:HERMES_HOME\hermes-agent`, managed uv at `$env:HERMES_HOME\bin\uv.exe`,
and `HERMES_GIT_BASH_PATH` points at Git Bash.

`HERMES_GIT_BASH_PATH` must point to a literal `bash.exe`. Prefer full Git for
Windows. If reusing GitHub Desktop's bundled Git, a `bash.exe` hardlink beside
`usr\bin\sh.exe` is acceptable only if this passes:

```powershell
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
```

## Procedure

### 1. Clone or Repair Hermes

```powershell
$env:HERMES_HOME = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" }
$target = Join-Path $env:HERMES_HOME "hermes-agent"

if (Test-Path "$target\.git") {
  git -C $target fetch origin --prune
  git -C $target pull --ff-only origin main
} else {
  git clone --branch main https://github.com/NousResearch/hermes-agent.git $target
}
```

Then let the installer validate the checkout:

```powershell
$installer = Join-Path $env:TEMP "hermes-install.ps1"
Invoke-WebRequest -Uri https://hermes-agent.nousresearch.com/install.ps1 -OutFile $installer
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer `
  -Stage repository -NonInteractive -Json -HermesHome $env:HERMES_HOME -InstallDir $target
```

This avoids piping into `Invoke-Expression` when the installer needs parameters.

### 2. Configure Provider Defaults

Recommended default for Nous Portal coding work: `qwen/qwen3-coder:free`.
For local LM Studio, the key is usually a dummy OpenAI-compatible value:

```text
Base URL: http://127.0.0.1:1234/v1
API key: lm-studio
```

Use a real API key only for hosted providers. Never commit keys to Hermes,
orama, Perpetua, OpenClaw, or ECC repos.

### 3. Install Coding Partner CLIs on Windows

Use the LM Studio Node/npm toolchain already present on this host:

```powershell
$env:PATH = "$env:USERPROFILE\.lmstudio\.internal\utils;$env:PATH"
npm install -g @openai/codex@latest
npm install -g @google/gemini-cli
codex --version
gemini --version
agy models
```

If `agy` is absent, skip it and continue with Hermes/Gemini/Codex.

### 4. Import Skills Safely

Import only reusable skill text or thin pointers into Hermes. Do not mirror
private workspace state. If Hermes has a local skill directory, use an `ecc-imports`
style folder and preserve canonical repo paths in comments or metadata.

Source candidates:

- `bin/orama-system/skills/hermes-harness/SKILL.md`
- `bin/orama-system/skills/openclaw-skills/SKILL.md`
- `bin/orama-system/skills/mcp-orchestration/SKILL.md`
- `bin/orama-system/skills/code-review/SKILL.md`
- `bin/orama-system/skills/git-history-surgery/SKILL.md`

### 5. Use Hermes as a Coding Partner

Prompt Hermes with a bounded, evidence-first contract:

```text
You are Hermes acting as a PT-orama coding partner.

Goal: help implement <task> in <repo>.
Boundaries: do not commit, delete, deploy, or reveal secrets. Do not copy
private Hermes/OpenClaw state into the repo. Prefer reusable ECC/orama skills
over one-off prompts.
Context to read:
- bin/orama-system/skills/hermes-harness/SKILL.md
- bin/orama-system/skills/openclaw-skills/SKILL.md
- bin/orama-system/skills/mcp-orchestration/SKILL.md
- docs/LESSONS.md
Return JSON with: assumptions, findings, proposed_edits, tests, risks.
```

Use AGY/Antigravity for general non-interactive Gemini-style partner work. Use
Gemini CLI only when it is authenticated or explicitly needed for Gemini-Analyzer
use-cases. Use Codex CLI for mechanical repo edits when explicitly approved. The
main orama agent keeps judgment.

## Verification

```powershell
Test-Path "$env:HERMES_HOME\hermes-agent\.git"
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
codex --version
gemini --version
git -C "$env:HERMES_HOME\hermes-agent" status --short --branch
```

Pass criteria:

- Hermes repo exists and is on a tracking branch.
- Bash probe prints `hermes-bash-ok`.
- Provider keys are outside git; imported skills are reusable and sanitized.
- OpenClaw operations still route through `openclaw-skills`.

## Boundaries

### Always Do

- Keep Hermes imports sanitized and reproducible.
- Use environment variables for machine-specific paths.
- Treat Hermes and OpenClaw as harnesses that consume canonical skills.
- Verify `bash.exe`, Node/npm, Codex, Gemini, and provider reachability before dispatch.

### Ask First

- Writing Hermes config files that include credentials or provider accounts.
- Starting long-running gateways, cron jobs, or remote dispatch surfaces.
- Letting Hermes, Gemini, AGY, or Codex modify files directly.

### Never Do

- Commit API keys, OAuth tokens, raw `~/.hermes` exports, personal memory, or
  local-only business artifacts.
- Replace OpenClaw procedures with Hermes guesses.
- Let worker agents commit, deploy, delete, or change account settings without
  explicit confirmation.

## References

- [`references/ecc-hermes-cross-harness.md`](references/ecc-hermes-cross-harness.md)
- [`../openclaw-skills/SKILL.md`](../openclaw-skills/SKILL.md)
- [`../mcp-orchestration/SKILL.md`](../mcp-orchestration/SKILL.md)
