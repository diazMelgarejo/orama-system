# Codex CLI v0.142.x — dispatch profiles and path contract

**Canonical reference for all orama-system skills that invoke OpenAI Codex CLI.**
Cite this card; do not fork flag tables into skill bodies.

**Applies to:** Codex CLI **≥ 0.140** (WinGet `OpenAI.Codex`, npm `@openai/codex@latest`).
**Removed:** legacy `--approval-mode` (do not use in prompts, docs, or fanout scripts).

## Path contract (never hardcode host paths)

| Resolve at runtime | Source |
|--------------------|--------|
| Codex binary | Native `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin` **before** `%USERPROFILE%\.lmstudio\bin`; see `platform/windows/ensure-partner-cli-paths.ps1` |
| Repo root (`-C`) | `$ORAMA_SYSTEM_PATH` / `$ORAMA_SYSTEM_ROOT` / `$ORAMA_REPO_ROOT`, else `git rev-parse --show-toplevel` |
| Test/script paths in prompt | **Repo-relative** (`tests/foo.py`) — never `C:\Users\…` or `/Users/…` in committed examples |
| Python for pytest | `python` on PATH inside `-C` repo root, or Hermes venv when harness docs say so |

Preferred launcher (resolves Codex + repo root):

```bash
python bin/orama-system/skills/hermes-harness/scripts/dispatch_codex_partner.py \
  --pytest tests/test_verify_partner_canaries.py
```

```powershell
python bin\orama-system\skills\hermes-harness\scripts\dispatch_codex_partner.py `
  --pytest tests\test_verify_partner_canaries.py
```

Dry-run: add `--dry-run` (prints resolved `codex` path and full argv).

## Flag mapping (v0.142.x)

| Profile | When | Command shape |
|---------|------|----------------|
| **fanout** | Non-interactive orchestrators (Hermes, Cursor fanout, CI) | `codex exec -C <repo-root> -s workspace-write --dangerously-bypass-approvals-and-sandbox "<bounded prompt>"` |
| **bounded** | Safer mechanical edits (sandbox, no bypass) | `codex exec -C <repo-root> -s workspace-write "<bounded prompt>"` |
| **interactive** | TTY / human-present sessions | `codex --sandbox danger-full-access --ask-for-approval never -C <repo-root> "<bounded prompt>"` |

`dispatch_codex_partner.py --profile` accepts `fanout` (default), `bounded`, `interactive`.

### Sandbox values (`-s` / `--sandbox`)

| Value | Use |
|-------|-----|
| `read-only` | Inspection only |
| `workspace-write` | Default for bounded repo edits |
| `danger-full-access` | Interactive profile; full disk (human present) |

### Approval (`--ask-for-approval` / `-a`) — top-level only

Available on **interactive** top-level `codex`, not on all `codex exec` subcommands:

| Value | Meaning |
|-------|---------|
| `never` | No per-command approval prompts (orchestrator fanout) |
| `on-request` | Model asks when unsure |
| `on-failure` | Deprecated — prefer `on-request` or `never` |

For **exec** fanout, use `--dangerously-bypass-approvals-and-sandbox` only when scope is
pre-verified by the main agent — never for open-ended exploration.

## Manual examples (parametric)

Bash — repo root from git:

```bash
ROOT="$(git rev-parse --show-toplevel)"
codex exec -C "$ROOT" -s workspace-write \
  --dangerously-bypass-approvals-and-sandbox \
  "Run only: python -m pytest tests/test_verify_partner_canaries.py -q. Report pass count only."
```

PowerShell — repo root from env or git:

```powershell
$root = if ($env:ORAMA_SYSTEM_PATH) { $env:ORAMA_SYSTEM_PATH } else {
  git -C $PWD rev-parse --show-toplevel
}
codex exec -C $root -s workspace-write --dangerously-bypass-approvals-and-sandbox `
  "Run only: python -m pytest tests/test_verify_partner_canaries.py -q. Report pass count only."
```

Interactive TTY:

```bash
codex --sandbox danger-full-access --ask-for-approval never \
  -C "$(git rev-parse --show-toplevel)" "<bounded task>"
```

## Install (Windows)

```powershell
winget install OpenAI.Codex   # preferred → %LOCALAPPDATA%\Programs\OpenAI\Codex\bin
# fallback:
npm install -g @openai/codex@latest
.\platform\windows\ensure-partner-cli-paths.ps1
codex --version
```

## Related cards

- [`hermes-harness/references/partner-prompt-contract.md`](../skills/hermes-harness/references/partner-prompt-contract.md) — full partner dispatch contract
- [`hermes-harness/references/workspace-path-resolution.md`](../skills/hermes-harness/references/workspace-path-resolution.md) — cross-repo env vars
- [`skillify/references/codex-thin-wrapper-installs.md`](../skills/skillify/references/codex-thin-wrapper-installs.md) — Codex skill wrapper policy

## Anti-patterns

- `--approval-mode approve-all` (removed in 0.140+)
- Absolute workstation paths in prompts or tracked docs (LINT-006 / CIDF)
- `codex exec` without `-C <repo-root>` when the task references repo-relative paths
- Assuming npm global and WinGet native are different major versions — check `codex --version` on PATH after `ensure-partner-cli-paths.ps1`
