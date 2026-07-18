# ClinePass DeepSeek Flash Route

Date: 2026-07-18

Durable lesson lives in `docs/LESSONS.md`. This working note exists only to
help adapter-based agents find the route quickly.

Summary:

- New route skill: `bin/orama-system/skills/clinepass-deepseek-flash/SKILL.md`
- Wrapper script: `bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh`
- Model: `cline-pass/deepseek-v4-flash`
- Reasoning: high
- Default workspace for sensitive fan-out: `/private/tmp`

Observed blocker:

- Local Cline accepted the command shape but routed the request through another
  provider, which rejected the ClinePass model slug.
- Treat this as a provider-auth/config blocker.
- Do not switch to another model silently; fix ClinePass auth/config first.

Privacy rule:

- Pass sanitized prompts only.
- Do not include secrets, private identity literals, LAN topology, device names,
  or workstation-specific paths in prompts, logs, memory, or docs.
