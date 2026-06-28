# Workspace-agnostic path resolution (skills + harnesses)

Skills and thin wrappers must **never** hardcode sibling checkout paths such as
`../Perpetua-Tools` or `..\Perpetua-Tools`. Use env vars, launcher discovery, or
git toplevel — same order as `start.sh` / `platform/windows/start.ps1`.

## Resolution order (Perpetua-Tools root)

| Priority | Source | When |
|----------|--------|------|
| 1 | `$PERPETUA_TOOLS_PATH` / `%PERPETUA_TOOLS_PATH%` | Explicit operator override |
| 2 | `$PT_HOME` / `%PT_HOME%` | Legacy alias (same semantics) |
| 3 | `$PERPETUA_TOOLS_ROOT` / `%PERPETUA_TOOLS_ROOT%` | orama canonical (also `PERPETUATOOLSROOT`) |
| 4 | `.paths` / `.paths.ps1` → `PT_DIR` | Written by `start.sh` / `start.ps1 --discover` |
| 5 | `$OPENCLAW_HOME/Perpetua-Tools` | Cloud / stack layout |
| 6 | Sibling discovery | Walk parent of orama repo root for `orchestrator/fastapi_app.py` |
| 7 | Legacy default | `../perplexity-api/Perpetua-Tools` (may be absent) |

**Validate:** `orchestrator/fastapi_app.py` exists under the resolved root.

## orama-system repo root

| Platform | Command (run from any checkout) |
|----------|----------------------------------|
| Bash | `git -C "$PWD" rev-parse --show-toplevel` |
| PowerShell | `git -C $PWD rev-parse --show-toplevel` |

Fallback when not in a git worktree: use the directory that contains `start.sh`
(macOS/Linux) or `platform/windows/start.ps1` (Windows).

## Hardware policy — preferred entry points

Always prefer **launcher gates** (they resolve PT and invoke the canonical CLI):

| Host | Command (from **orama-system repo root**) |
|------|-------------------------------------------|
| macOS / Linux | `./start.sh --hardware-policy` |
| Windows | `.\platform\windows\start.ps1 --hardware-policy` |

Direct PT CLI (only when launcher is unavailable):

| Platform | Snippet |
|----------|---------|
| Bash (Mac OpenClaw) | `"${PERPETUA_TOOLS_ROOT:-${PERPETUA_TOOLS_PATH:?set PT root}}/scripts/hardware_policy_cli.py" --check-openclaw` |
| PowerShell (Windows Hermes) | `python (Join-Path $env:PERPETUA_TOOLS_ROOT 'scripts\hardware_policy_cli.py') --list` then `--validate <model> win` — **do not** use `--check-openclaw` on Windows |

## Windows script paths (repo-root relative)

All examples assume **current working directory = orama-system repository root**:

| Script | Path |
|--------|------|
| `start.ps1` | `.\platform\windows\start.ps1` |
| `install.ps1` | `.\platform\windows\install.ps1` |
| `ensure-partner-cli-paths.ps1` | `.\platform\windows\ensure-partner-cli-paths.ps1` |

## Partner CLI dirs (parametric — never hardcode `%USERPROFILE%\<name>`)

| CLI | Windows (User PATH) | macOS/Linux |
|-----|---------------------|-------------|
| Hermes | `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts` | `$HERMES_HOME/hermes-agent/venv/bin` |
| Codex | `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin` (WinGet) **preferred**; fallback `%USERPROFILE%\.lmstudio\bin` | npm global / `~/.local/bin` |
| AGY | `%LOCALAPPDATA%\agy\bin` | Antigravity installer default |
| cursor-agent | `%LOCALAPPDATA%\cursor-agent` | `~/.local/bin` |

Bootstrap: `.\platform\windows\ensure-partner-cli-paths.ps1` (idempotent).

## Hermes installer (orama repo root)

```bash
python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install
```

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
```

## Anti-patterns (do not use in skills)

- `../Perpetua-Tools/scripts/...` — breaks multi-repo worktrees and cloud layouts
- `../../../../../../../Perpetua-Tools/...` — fragile relative depth in command cards
- Inferring NEVER_MAC from `/v1/models` list membership
- Duplicating `model_hardware_policy.yml` lists in markdown

## Canonical policy (always cite, never copy lists)

- PT `config/model_hardware_policy.yml`
- PT `src/utils/hardware_policy.py`
- PT `.claude/skills/hardware-policy/SKILL.md`
