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
5. **Shared hardware policy:** Perpetua-Tools `config/model_hardware_policy.yml` + `src/utils/hardware_policy.py` are the **only** affinity SSoT. Hermes must **consume** PT policy via CLI/API — never infer NEVER_MAC/NEVER_WIN independently at runtime.

## Platform Harness Model

| Host OS | Primary harness | LM Studio role | Orchestrator role |
|---------|-----------------|----------------|-------------------|
| **macOS** | OpenClaw (`start.sh`) | Mac MLX home (`lmstudio-mac`); Win GGUF = NEVER_MAC | Mac orchestrator / thin orchestrator |
| **Linux** | OpenClaw (`start.sh`) | Same software as macOS; can host **any** documented profile from PT `hardware/SKILL.md` | Dev/CI orchestrator; full hardware matrix |
| **Windows 11** | Hermes + `start.ps1` | Win GGUF home (`lmstudio-win` → `localhost:1234`) | Hermes = local orchestrator / autoresearcher counterpart |

**Role reversal on Windows:** Mac orchestrator historically reached Win LM Studio over LAN
(`192.168.x.x:1234`). On the Windows Hermes host, LM Studio is **localhost** and
`windows_only` models are **allowed** — the same YAML policy, inverted platform verdict.

**Linux note:** Linux runs the same OpenClaw harness binary as macOS (`start.sh`). It is not
a second-class consumer — it may run Mac profiles, Win profiles, or both per `hardware/SKILL.md`
and `model_hardware_policy.yml`, subject to what physical GPUs/backends are present.

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

Before using one-shot or agent modes, put the installed venv launcher on
`PATH` and set `HERMES_GIT_BASH_PATH` to a literal `bash.exe`. Detailed Windows
recipe: `docs/wiki/15-hermes-windows-harness.md`.

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
NousResearch does not publish a hash or Authenticode signature for this
installer (confirmed against their docs and FAQ as of 2026-06-19) -- saving
the script to a file first is the most practical integrity step actually
available here, not a placeholder for a stronger check we skipped.

### 2. Configure Provider Defaults

Recommended Nous Portal default for coding work: `qwen/qwen3-coder:free`.
For local LM Studio, use OpenAI-compatible local settings:

```text
Base URL: http://127.0.0.1:1234/v1
API key: lm-studio
```

Use a real API key only for hosted providers. Never commit keys.

**Hardware policy (mandatory before LM Studio dispatch):** Hermes must not guess
affinity from `/v1/models`. Run the PT canonical gate:

```powershell
# From orama-system repo root on Windows
.\platform\windows\start.ps1 --hardware-policy

# Or direct PT CLI (same enforcement)
python ..\Perpetua-Tools\scripts\hardware_policy_cli.py --check-openclaw
```

After `install.ps1` writes `openclaw.json` (`lmstudio-win` → `http://localhost:1234`),
verify assignments against `config/model_hardware_policy.yml`. Load
`commands/pt-hardware-policy/SKILL.md` or install `/pt-hardware-policy` via step 4.

### 3. Install Coding Partner CLIs on Windows

Use the LM Studio Node/npm toolchain already present on this host:

```powershell
$env:PATH = "$env:USERPROFILE\.lmstudio\.internal\utils;$env:PATH"
npm install -g @openai/codex@latest --audit=moderate
npm install -g @google/gemini-cli --audit=moderate
```

`--audit=moderate` flags known-vulnerable transitive packages at install time
without pinning to a version number that will immediately go stale in this
doc. If `npm audit` reports a moderate-or-higher finding, stop and review
before continuing.

Install Antigravity CLI by saving the installer first rather than piping
directly into `Invoke-Expression` -- consistent with the Hermes installer
pattern above:

```powershell
$agyInstaller = Join-Path $env:TEMP "antigravity-install.ps1"
Invoke-WebRequest -Uri https://antigravity.google/cli/install.ps1 -OutFile $agyInstaller
Get-Content $agyInstaller | Select-Object -First 40   # eyeball it before running
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $agyInstaller
codex --version; gemini --version; agy --version
```

The Antigravity installer itself downloads the `agy` binary and verifies a
SHA-512 checksum against its release manifest before extracting it -- the
binary is checksummed, but the bootstrap script that does that checking is
not independently signed, which is the same residual trust step as any
`curl|bash`-style installer. Saving and skimming the script first closes
that one remaining gap cheaply.

If `agy` is absent, or if `agy --print "Reply with exactly: AGY_READY"`
exits with empty stdout, skip it and continue with Hermes/Gemini/Codex. To
differentiate a shell problem from a hosted-model problem, rerun once with
`--log-file <path>`; silent auth followed by quota exhaustion means AGY is
installed but not dispatchable.

### 4. Import Skills Safely

Import only reusable skill text or thin pointers into Hermes. Do not mirror
private workspace state. Hermes local commands must be thin wrappers that point
back to canonical command cards under `commands/<slug>/SKILL.md`.

Create or refresh Hermes local commands from the canonical repo:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
```

The expected slash commands are `/pt-hardware-policy`, `/pt-orama-council`,
`/pt-orama-review`, and `/pt-orama-delegate`; never paste a full canonical skill body into Hermes.

### 5. Use Hermes as a Coding Partner

For bounded non-interactive review on this Windows host, prefer explicit
provider/model routing because the default LM Studio model can be reachable but
slow enough for `hermes chat` to appear hung.

```powershell
hermes chat --query "Reply with exactly: HERMES_READY" --quiet --safe-mode `
  --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1
```

Prompt Hermes with a bounded, evidence-first contract: state the goal, forbid
commits/deletes/deploys/secrets, forbid copying private harness state, cite the
canonical skills to inspect, and request JSON with assumptions, findings,
proposed edits, tests, and risks.

Use AGY for non-interactive Gemini-style partner work only after the visible
canary passes, Gemini CLI only for authenticated Gemini-Analyzer use-cases, and
Codex CLI for approved mechanical repo edits. The main orama agent keeps
judgment.

## Verification

```powershell
# Hardware affinity (PT canonical — must pass before LM Studio orchestration)
.\platform\windows\start.ps1 --hardware-policy

Test-Path "$env:HERMES_HOME\hermes-agent\.git"
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
hermes chat --query 'Reply with exactly: HERMES_READY' --quiet --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1
codex --version
gemini --version
git -C "$env:HERMES_HOME\hermes-agent" status --short --branch
```

Pass criteria: **hardware policy check passes**, Hermes repo exists, Bash prints `hermes-bash-ok`, one-shot
prints `HERMES_READY`, provider keys stay outside git, imported skills are
sanitized, and OpenClaw operations still route through `openclaw-skills`.

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

- [`commands/pt-hardware-policy/SKILL.md`](commands/pt-hardware-policy/SKILL.md)
- [`../hardware-affinity-gate/SKILL.md`](../hardware-affinity-gate/SKILL.md) (pointer only — PT is SSoT)
- [`references/ecc-hermes-cross-harness.md`](references/ecc-hermes-cross-harness.md)
- [`references/hermes-ecc-fork-inventory.md`](references/hermes-ecc-fork-inventory.md)
- [`../openclaw-skills/SKILL.md`](../openclaw-skills/SKILL.md)
- [`../mcp-orchestration/SKILL.md`](../mcp-orchestration/SKILL.md)
