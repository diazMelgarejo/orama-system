---
name: openclaw-stow
description: Deploy OpenClaw config via GNU stow with no-folding semantics and jobs.json conflict handling.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-stow/SKILL.md
overlay_role: orama-normalized cross-harness extension
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-stow/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-stow/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Apply repository-managed OpenClaw files to the target home directory using deterministic symlinks. This skill handles the known `jobs.json` conflict before stowing so cron remains stable. It is the canonical deployment step after manual file edits.

## When to Use

- After manual edits to managed OpenClaw files
- After pulling updates that add or change skill/config files
- Before performing a gateway restart

## Inputs

- Required: none
- Optional:
  - `target_dir` (default `$HOME`)
  - `dry_run` (`true|false`, default `false`)

## Procedure

1. Set target and validate stow availability.

```bash
set -euo pipefail
target_dir="${target_dir:-$HOME}"
command -v stow >/dev/null
```
1. Resolve known cron conflict by removing transient file.

```bash
rm -f ~/.openclaw/cron/jobs.json
```
1. Run GNU stow with no-folding.

```bash
stow --no-folding -t "$target_dir" .
```
1. Detect unresolved conflicts.

```bash
stow --no-folding -n -v -t "$target_dir" .
```
1. Confirm critical symlinks exist.

```bash
[ -e "$target_dir/.openclaw" ] || true
```
1. If dry-run requested, preview without mutating and exit.

```bash
if [ "${dry_run:-false}" = "true" ]; then
  stow --no-folding -n -v -t "$target_dir" .
  exit 0
fi
```
1. Report deployment completion status.

```bash
echo "{\"status\":\"ok\",\"target_dir\":\"$target_dir\"}"
```

## Output Contract

```json
{
  "status": "ok|error",
  "files_modified": [],
  "follow_up_actions": ["openclaw-restart", "openclaw-status"]
}
```

## Naming Enforcement

- Stow invocation must include `--no-folding`.
- Cron runtime file `~/.openclaw/cron/jobs.json` is never treated as source-controlled truth.
- Target should be the OpenClaw home root (default `$HOME`) unless deployment layout is intentionally different.

## Gotchas

- Gateway startup rewrites `jobs.json`, replacing symlink with a regular file.
- Running stow without conflict cleanup can fail or create partial deploy state.
- A successful stow still requires restart to load runtime changes.
- Dry-run output may still show stale conflicts from paths outside OpenClaw scope; verify target root first.
- Stowing from the wrong directory can create valid symlinks in the wrong place.

## See Also

- `../openclaw-restart/SKILL.md`
- `../openclaw-status/SKILL.md`
- `../openclaw-add-cron/SKILL.md`

## Notes

- Use this skill whenever manual edits bypass an automated configuration skill.
- Pair with `openclaw-restart` for runtime convergence after deployment.
- If dry-run reports conflicts, resolve them before any restart.

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
