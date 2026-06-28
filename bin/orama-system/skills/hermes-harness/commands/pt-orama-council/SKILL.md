---
name: pt-orama-council
description: >-
  Coordinate PT-orama council work with Codex, Hermes, AGY, and local model
  partners only after readiness checks.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, codex, windows
parent_skill: hermes-harness
triggers:
  - pt-orama-council
  - hermes council
  - cross-harness council
allowed-tools: bash, file-operations
---

# PT-orama Council

Use this command when Hermes is asked to help with PT-orama, ECC, OpenClaw,
Antigravity, Codex, or cross-harness work.

## Council Protocol

Use [`../../references/hermes-council-review-gates.md`](../../references/hermes-council-review-gates.md)
for roles, review gates, and review package shape.

## Canonical Sources

Read relevant excerpts from:

- [`../../SKILL.md`](../../SKILL.md)
- [`../../references/hermes-council-review-gates.md`](../../references/hermes-council-review-gates.md)
- [`../../references/hermes-windows-partner-readiness.md`](../../references/hermes-windows-partner-readiness.md)
- [`../../../../../../docs/wiki/15-hermes-windows-harness.md`](../../../../../../docs/wiki/15-hermes-windows-harness.md)
- [`../../../../../../ANTIGRAVITY.md`](../../../../../../ANTIGRAVITY.md)
- [`../../../../../../docs/LESSONS.md`](../../../../../../docs/LESSONS.md)

## Corrections To Internalize

1. Treat earlier Hermes drafts as brainstorms, not source of truth.
2. Canonical behavior lives in `orama-system`; local Hermes files are adapters.
3. Do not claim upstream branches, commits, or PRs exist unless verified.
4. Do not copy raw Hermes home state, secrets, OAuth tokens, or personal memory
   into tracked files.
5. Do not let workers commit, delete, deploy, or change accounts without
   explicit instruction.

## Readiness Rules

- Hermes one-shot: prefer `--safe-mode --provider nous --model stepfun/step-3.7-flash:free`.
- LM Studio: usable only after a fast `/v1/chat/completions` canary.
- AGY native Windows install: `irm https://antigravity.google/cli/install.ps1 | iex`.
- AGY usability: `agy --print "Reply with exactly: AGY_READY"` must print visible stdout.
- Exact Qwen names must come from live `/v1/models`; never invent model IDs.

## Output Format

```text
ASSUMPTIONS:
FINDINGS:
PROPOSED ACTIONS:
TESTS / VERIFICATION:
RISKS:
HANDOFF NOTES:
```
