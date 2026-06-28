# Windows Onboarding Configuration Reference

> **Role:** Windows-specific environment variables, paths, and toolchain notes for Hermes on Windows 11.  
> **Hard rule:** references-only — no executable logic in this file. Thin wrappers and `start.ps1` read this.  
> **Paths:** `%USERPROFILE%`-relative or env-var form only. No absolute workstation paths (LINT-006).

---

## Required Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `HERMES_HOME` | `%LOCALAPPDATA%\hermes` | Hermes install root |
| `HERMES_GIT_BASH_PATH` | *(must be set)* | Absolute path to `bash.exe` — full Git for Windows preferred |
| `WIN_IP` | *(fallback in code only — set in `.env`)* | This machine's LAN IP (used by Mac→Win cross-machine calls only) |
| `MAC_IP` | *(fallback in code only — set in `.env`)* | Mac host LAN IP (used by Win→Mac cross-machine calls only) |
| `LM_STUDIO_WIN_ENDPOINTS` | `http://localhost:1234` | LM Studio URL — `localhost` when on Windows |
| `OLLAMA_WINDOWS_ENDPOINT` | `http://localhost:11434` | Ollama URL — `localhost` when on Windows |
| `LM_STUDIO_API_TOKEN` | `lm-studio` | Bearer token for local LM Studio (dev only) |
| `NOUS_API_KEY` | *(must be set for Nous)* | Nous Portal API key — never tracked |

---

## PowerShell UTF-8 Encoding

Always set at the top of any PowerShell script that writes files:

```powershell
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding           = [System.Text.UTF8Encoding]::new($false)
```

---

## Node / npm Toolchain

Use the Node/npm bundled with LM Studio — already on this host:

```powershell
$env:PATH = "$env:USERPROFILE\.lmstudio\.internal\utils;$env:PATH"
node --version   # verify
npm --version    # verify
```

`npm` shims live at `%USERPROFILE%\.lmstudio\bin`. Do **not** add the versioned internal path
(`%USERPROFILE%\.lmstudio\.internal\...`) to a permanent PATH — it changes on LM Studio upgrades.

---

## Git Bash Requirement

Hermes requires a real `bash.exe`. Prefer full Git for Windows.
If reusing GitHub Desktop's bundled Git, create a `bash.exe` hardlink:

```powershell
$gitDir = (Split-Path (Get-Command git.exe).Source)
New-Item -ItemType HardLink `
  -Path "$gitDir\bash.exe" `
  -Target "$gitDir\..\usr\bin\sh.exe"
```

Verify before continuing:

```powershell
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
# Must print: hermes-bash-ok
```

---

## uv (Python environment manager)

Hermes ships its own `uv.exe` at `%HERMES_HOME%\bin\uv.exe`. Do not use system uv for Hermes tasks.

---

## Partner CLI Paths (Windows)

Add these to **User PATH** (idempotent script: `platform/windows/ensure-partner-cli-paths.ps1`):

| CLI | Install location | Verify |
|-----|------------------|--------|
| **Hermes** | `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts` | `hermes --version` |
| **Hermes uv** | `%LOCALAPPDATA%\hermes\bin` | `uv --version` |
| **Codex** | `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin` (WinGet `OpenAI.Codex`) **preferred**; fallback `%USERPROFILE%\.lmstudio\bin` (npm) | `codex --version` |
| **AGY** | `%LOCALAPPDATA%\agy\bin` | `agy --version` |
| **cursor-agent** | `%LOCALAPPDATA%\cursor-agent` | `cursor-agent --version` |

macOS/Linux equivalents:

| CLI | PATH entry |
|-----|------------|
| cursor-agent | `~/.local/bin` |
| codex | npm global or `~/.local/bin` |
| agy | installer default (see Antigravity docs) |
| hermes | `$HERMES_HOME/hermes-agent/venv/bin` |

OpenClaw on Windows is **optional** — Hermes is the primary orchestrator. Partner CLIs above are independent of OpenClaw.

**Codex install (pick one; native preferred):**

```powershell
# Native WinGet CLI (recommended) — installs to %LOCALAPPDATA%\Programs\OpenAI\Codex\bin
winget install OpenAI.Codex

# Or npm global (often lands in %USERPROFILE%\.lmstudio\bin via LM Studio)
npm install -g @openai/codex@latest
```

After install, run `platform/windows/ensure-partner-cli-paths.ps1` so native Codex
precedes the LM Studio npm shim on User PATH.

**Bounded dispatch:** [`bin/orama-system/references/codex-cli-v142-dispatch.md`](../../../references/codex-cli-v142-dispatch.md)
or `dispatch_codex_partner.py` (runtime path resolution).

Session-only (do **not** add permanently — changes on LM Studio upgrade):

```powershell
$env:PATH = "$env:USERPROFILE\.lmstudio\.internal\utils;$env:PATH"
```

---

## Related

- [`../../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../../git-history-surgery/references/safe-cross-host-sync-reference-card.md) — stash-first Mac↔Win `main` sync (before push/pull handoff)
- [`lan-endpoint-contract.md`](lan-endpoint-contract.md) — full IP variable contract
- [`windows-provider-routing.md`](windows-provider-routing.md) — provider fallback stack
- [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md) — canary + readiness matrix
- [`../SKILL.md`](../SKILL.md) § Windows Bring-Up — install + configure procedure
