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
| Test/script paths in prompt | **Repo-relative** (`tests/foo.py`) — never `C:\<user>\…` or `/<user>/…` absolute host paths in committed examples |
| Python for pytest | `uv run --no-sync -m pytest`, **never** bare `python`/`pytest` on PATH — see "Python interpreter resolution" below |
| Codex process stdin (non-interactive dispatch) | Always closed/`DEVNULL` — see "Stdin hygiene" below |

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

## Stdin hygiene (mandatory for non-interactive dispatch)

**Always dispatch `codex exec` with stdin explicitly closed** when running
detached/backgrounded/non-interactive (fanout, CI, a subprocess launched by
another script). `dispatch_codex_partner.py` and `dual_path_dispatch.py` both
do this internally (`stdin=subprocess.DEVNULL`) — prefer those launchers over
a raw manual `codex exec` invocation so this is handled for you. This does
**not** apply to the top-level interactive `codex` profile (a human present
at a TTY) — `dispatch_codex_partner.py --profile interactive` keeps real
stdin (`stdin=None`) since Codex needs to read actual keystrokes there. If
you must invoke `codex exec` directly in a script or one-off command, close
stdin yourself:

```bash
codex exec -C "$ROOT" -s workspace-write \
  --dangerously-bypass-approvals-and-sandbox \
  "<prompt>" < /dev/null
```

```powershell
cmd /c "codex exec -C `"$root`" -s workspace-write --dangerously-bypass-approvals-and-sandbox `"<prompt>`" < NUL"
```

**Why:** an inherited-but-unfed stdin (common when a caller backgrounds/detaches
the process) leaves Codex CLI printing `Reading additional input from
stdin...` and hanging indefinitely — even when the prompt was already passed
correctly as a positional argument. Confirmed live 2026-08-08 dispatching
orama PR #289's fix: `ps aux` showed the full prompt text present in the
process's own argv, proving the hang was purely stdin-related, not a failed
argument pass. Killing the process and re-running with `< /dev/null` fixed it
immediately. This is not a Codex CLI bug report — it is a caller-hygiene rule:
always close stdin on any dispatch you don't intend to feed interactively.

## Python interpreter resolution

**Always `uv run --no-sync -m pytest`, never bare `python`/`pytest`
on PATH**, in prompts, scripts, and manual commands alike. A bare `python`/
`pytest` resolves via `$PATH` search order, which can silently land on a
stray interpreter with the wrong (or entirely absent) dependency set instead
of this repo's `uv.lock`-pinned versions — e.g. an old Xcode Command Line
Tools Python or a `pip install --user` script sitting ahead of the project's
own `.venv` in `$PATH`. Symptoms are misleading collection-time errors that
look like real code bugs (e.g. `TypeError: Router.__init__() got an
unexpected keyword argument 'on_startup'` from a stale, incompatible
FastAPI/Starlette pairing) rather than an obvious "wrong interpreter" message.

```bash
uv sync --frozen --extra test   # once per fresh worktree/checkout
uv run --no-sync -m pytest tests/ -q
```

```powershell
uv sync --frozen --extra test
uv run --no-sync -m pytest tests\ -q
```

If a `.venv` doesn't exist yet, `uv sync --frozen --extra test` builds it from
the repo's own lockfile (production deps + the `test` extra, which carries
`pytest`/`pytest-asyncio` — not part of the base dependency set). `--no-sync`
on the `run` step skips re-resolving on every invocation once the venv is
current.

## Manual examples (parametric)

Bash — repo root from git:

```bash
ROOT="$(git rev-parse --show-toplevel)"
codex exec -C "$ROOT" -s workspace-write \
  --dangerously-bypass-approvals-and-sandbox \
  "Run only: uv run --no-sync -m pytest tests/test_verify_partner_canaries.py -q. Report pass count only." \
  < /dev/null
```

PowerShell — repo root from env or git:

```powershell
$root = if ($env:ORAMA_SYSTEM_PATH) { $env:ORAMA_SYSTEM_PATH } else {
  git -C $PWD rev-parse --show-toplevel
}
cmd /c "codex exec -C `"$root`" -s workspace-write --dangerously-bypass-approvals-and-sandbox `"Run only: uv run --no-sync -m pytest tests\test_verify_partner_canaries.py -q. Report pass count only.`" < NUL"
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
- **`codex exec` dispatched detached/backgrounded/non-interactively without closing stdin** (`< /dev/null` / `< NUL`) — hangs on "Reading additional input from stdin..." even with a correctly-passed prompt argument. Use `dispatch_codex_partner.py`/`dual_path_dispatch.py`, both of which set `stdin=subprocess.DEVNULL` internally.
- **Bare `python`/`pytest` on PATH** in a prompt, script, or manual command instead of `uv run --no-sync -m pytest` — silently resolves to whatever interpreter happens to be first on `$PATH`, not this repo's `uv.lock`-pinned dependency set. Produces misleading collection-time errors, not an obvious "wrong interpreter" message.
