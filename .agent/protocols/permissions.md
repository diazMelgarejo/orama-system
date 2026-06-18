# Antigravity Permissions

## Allowed By Default

- Read repository files.
- Run bounded diagnostics, tests, and repo hygiene checks.
- Propose edits with file references and verification steps.
- Use `agy -p` for non-interactive review when the prompt is secret-free.

## Ask First

- Writing config files that may include credentials, provider accounts, or
  gateway state.
- Starting long-running gateways, cron jobs, daemons, or remote dispatch loops.
- Letting Antigravity edit files directly instead of returning proposed edits.
- Pushing branches or creating pull requests.

## Never Do

- Commit secrets, tokens, raw `~/.hermes`, `.antigravity/`, browser profiles, or
  personal workspace memory.
- Force-push `main`, `master`, or shared branches.
- Delete files or rewrite history without explicit user instruction.
- Use absolute workstation paths in tracked docs or skills.
- Treat Antigravity output as final without main-agent review.
