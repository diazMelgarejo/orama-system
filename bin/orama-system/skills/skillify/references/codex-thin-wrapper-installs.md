# Codex Thin Wrapper Skill Installs

Local Codex skill installs must be wrappers, not forks.

## Rule

Install only a small wrapper under Codex-discovered skill roots that points to the canonical in-repo skill card. Current Codex docs use `$HOME/.agents/skills/<name>/SKILL.md` for personal skills and `.agents/skills/<name>/SKILL.md` for repo skills. This repository may also write `~/.codex/skills/<name>/SKILL.md` for compatibility with Codex Desktop sessions that still expose that legacy root. Do not copy the canonical skill body, references, scripts, or assets into a Codex skill directory.

## Why

- Canonical skill behavior stays in git and updates with `origin`.
- Local Codex installs stay small enough for reliable trigger matching.
- There is no stale second copy of Claude-only frontmatter, references, or scripts.
- Windows encoding failures stay easier to isolate because generated wrapper files are tiny.

## Wrapper Requirements

Each wrapper must include:

- Codex-valid frontmatter only: `name` and `description`.
- The canonical repo root.
- The canonical `SKILL.md` path.
- A safe origin-sync rule.
- A Windows UTF-8 note.

## Required Origin Sync Before Use

Before relying on the canonical card:

```bash
git fetch origin --prune
git status --short --branch
```

If the repo is on a tracking branch and the worktree is clean:

```bash
git pull --ff-only
```

If the worktree is dirty, the branch is not tracking origin, or fast-forward is impossible, do not overwrite local work. Report the drift and read the current canonical card with that caveat.

## Windows Encoding Requirements

On Windows PowerShell, set UTF-8 explicitly before reading or writing skill files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```

When generating files from PowerShell, prefer .NET UTF-8 without BOM:

```powershell
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
```

Avoid `Set-Content -Encoding utf8` in Windows PowerShell 5.1 for generated skill roots because it can write a BOM that breaks strict frontmatter readers.

## Validation Gates

Run all of these before declaring a local install done:

- `quick_validate.py <skill-dir>` with `PYTHONUTF8=1`.
- Verify the canonical card path exists.
- Verify the wrapper contains `git fetch origin --prune` and `git pull --ff-only`.
- Verify the wrapper directory contains only `SKILL.md`.
- Scan wrapper roots for mojibake markers such as `Ã`, `Â`, `â`, and `�`.

## Local Model Smoke Test

For Qwen reasoning models in LM Studio, keep prompts compact:

- Use `/no_think`.
- Ask for minified JSON.
- Prefer deterministic file/path audits first, then ask the model to review the compact manifest.
- Save raw API responses and parsed summaries under `~/.codex/skill-test-results/`.
- Avoid feeding large canonical excerpts in one request; long reasoning prompts can time out.
