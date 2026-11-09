# ClinePass DeepSeek Flash Route

Date: 2026-07-18 (route facts corrected 2026-11-08)

Durable lesson lives in `docs/LESSONS.md`. This working note exists only to
help adapter-based agents find the route quickly.

Summary:

- Route skill: `bin/orama-system/skills/clinepass-deepseek-flash/SKILL.md`
- Wrapper script: `bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh`
- Provider: pin `-P cline-pass` explicitly. The CLI default provider is `cline`,
  which does not carry this model slug.
- Model: `cline-pass/deepseek-v4.1-flash-1017` (the retired
  `cline-pass/deepseek-v4-flash` is not dispatchable)
- Reasoning: medium (`--thinking medium`)
- Default workspace for sensitive fan-out: `/private/tmp`

Observed blocker (root-caused and fixed 2026-11-08):

- Local Cline accepted the command shape but routed the request through another
  provider, which rejected the ClinePass model slug.
- Root cause: the dispatch carried no provider pin, so the request was resolved
  against the CLI default provider (`cline`) instead of ClinePass. The wrapper
  now pins `-P cline-pass` and refuses to dispatch when the CLI cannot pin a
  provider, a reasoning level, or tool auto-approval.
- Do not switch to another model silently; fix ClinePass auth/config first.

Verified on Cline CLI `3.0.74` (2026-11-08):

- One fresh headless dispatch on this route completed: exit 0, JSON output,
  reply text as instructed, 1 iteration, 0 tool calls.
- `--auto-approve` defaults to `true`; the wrapper still passes it explicitly.
- `-p` is `--plan`, not "print". Bare `--thinking` already means `medium`.
- Session resume (`--id`) is not usable headlessly: with `--json` it exits with
  "JSON output mode requires a prompt argument or piped stdin", and without
  `--json` it requires a TTY. Flag presence is not support.

Privacy rule:

- Pass sanitized prompts only.
- Do not include secrets, private identity literals, LAN topology, device names,
  or workstation-specific paths in prompts, logs, memory, or docs.
