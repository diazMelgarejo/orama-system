# Project Instructions (Antigravity)

This project uses the orama-system canonical brain. `.agent/` is a thin
Antigravity adapter that points back to repo-owned skills, lessons, and
permissions. Do not fork the operating knowledge into `.agent/`.

## Before Doing Anything

1. Read `AGENTS.md` for the repo-wide agent contract.
2. Read `.agent/AGENTS.md` for the Antigravity adapter map.
3. Read `docs/LESSONS.md` and `docs/wiki/README.md` before guidance or docs edits.
4. Read `.agent/protocols/permissions.md` before tool use.
5. Load the relevant canonical skill from `bin/orama-system/skills/`.

## Recall First

Before any non-trivial task involving deploy, migration, failing tests, debug,
refactor, history surgery, Hermes, OpenClaw, or Antigravity dispatch, inspect the
memory pointers under `.agent/memory/` and the canonical `docs/LESSONS.md`.

If a surfaced lesson conflicts with the intended action, stop and explain the
conflict before editing.

## While Working

- Prefer `agy -p "<bounded prompt>"` for non-interactive review or delegation.
- Keep Antigravity as a coding partner, not the final decider.
- Do not let Antigravity commit, delete, deploy, or change account settings
  unless the user explicitly asks for that exact operation.
- Keep prompts repo-relative and secret-free.
- Record durable lessons in `docs/LESSONS.md`, not in private `.agent` memory.

## Hard Rules

- Never commit API keys, OAuth tokens, raw `~/.hermes`, `.antigravity/`, or
  personal workspace memory.
- Never force-push `main` or any shared branch.
- Never write absolute workstation paths into tracked files.
- Keep OpenClaw configuration work on `openclaw-skills`; keep Hermes onboarding
  on `hermes-harness`.
