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

- Hermes one-shot: prefer `--safe-mode --provider nous --model nvidia/nemotron-3-ultra:free`.
- LM Studio first fast path: target `qwen3.5-9b-mlx` with `/v1/chat/completions` and generous `max_tokens` (≥2048); canary typically completes under 10s.
- LM Studio fallback: `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` is valid but slower (~6s–90s depending on reuse and token budget). Use up to a 90s timeout for the first request after load; if it still times out, fall back to the 9B lane or Hermes+Nous.
- `max_tokens` must account for reasoning tokens. A 64-token budget on a reasoning model can finish with `finish_reason=length` and empty visible output even though the call succeeded.
- AGY native Windows install: `irm https://antigravity.google/cli/install.ps1 | iex`.
- AGY usability: `agy --print "Reply with exactly: AGY_READY"` must print visible stdout. (Note: quota exhaustion is observed; retry after June 28, 2026 or when hosted quota resets).
- Exact Qwen names must come from live `/v1/models`; never invent model IDs.

## Lane Availability & Degraded Operations

### Readiness Matrix (check before dispatch)

| Lane | Canary | Current State | Degraded Path |
|------|--------|---------------|---------------|
| Codex | `codex --version` | ✅ Installed | None (host live) |
| AGY/Antigravity | `agy --print "AGY_READY"` | ❌ Quota exhausted / empty stdout (Retry +7 days, Jun 28 2026) | Use Codex as reviewer; skip Antigravity gate |
| LM Studio | `/v1/chat/completions` up to 45s | ⚠️ Heavy model loading | Use Hermes + Nous provider; skip local delegation |

### Degraded Fallback Rules

When a lane fails its canary:
1. **AGY unavailable** → Reviewer role falls back to Codex (main orama agent retains judgment). Check quota status weekly.
2. **LM Studio unavailable** → Local specialist falls back to Hermes + Nous provider, or the host executes inline.
3. **Codex unavailable** → Pause; host cannot execute. Alert user.

Never block a task solely because a non-host lane failed its canary.

## Output Format

```text
ASSUMPTIONS:
FINDINGS:
PROPOSED ACTIONS:
TESTS / VERIFICATION:
RISKS:
HANDOFF NOTES:
```
