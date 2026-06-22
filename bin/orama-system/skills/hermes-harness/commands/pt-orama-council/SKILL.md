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
for roles, review gates, and review package shape. Treat that file as support
for this command, not a separate subskill or activation surface.

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
- LM Studio: usable only after a fast `/v1/chat/completions` canary.
- AGY native Windows install: `irm https://antigravity.google/cli/install.ps1 | iex`.
- AGY usability: `agy --print "Reply with exactly: AGY_READY"` must print visible stdout.
- Exact Qwen names must come from live `/v1/models`; never invent model IDs.
- Hermes one-shot: prefer `--quiet --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free`.
- LM Studio on Windows: target `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` via `/v1/chat/completions`. Use up to a 180s timeout; tested completion time in this environment is ~28s when `max_tokens` is generous (≥2048). Do not list or rely on `qwen3.5-9b-mlx` as a Windows fast path — it is macOS/MLX-only.
- `max_tokens` must account for reasoning tokens. A 64-token budget on a reasoning model can finish with `finish_reason=length` and empty visible output even though the call succeeded.
- LM Studio: usable only after a fast `/v1/chat/completions` canary passes.
- AGY native Windows install: save installer first — see `docs/wiki/15-hermes-windows-harness.md`.
- AGY usability: `agy --print "Reply with exactly: AGY_READY"` must print visible stdout. (Note: quota exhaustion is observed; retry after June 28, 2026 or when hosted quota resets).
- Exact model names must come from live `/v1/models`; never invent model IDs.

## Lane Availability & Degraded Operations

### Readiness Matrix (check before dispatch)

| Lane | Canary | Current State | Degraded Path |
|------|--------|---------------|---------------|
| Codex | `codex --version` | ✅ Installed | None (host live) |
| AGY/Antigravity | `agy --print "AGY_READY"` | ❌ Quota exhausted / empty stdout (Retry +7 days, Jun 28 2026) | Use Codex as reviewer; skip Antigravity gate |
| LM Studio | `/v1/chat/completions` up to 180s | ⚠️ Heavy model loading; ~28s tested with generous max_tokens | Use Hermes + Nous provider; skip local delegation |

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

## References

- Perpetua-Tools hardware profiles (canonical hardware routing source):
  - `Profile A — mac-studio`: `Qwen3.5-9B-MLX-4bit` via LM Studio on Metal (macOS/MLX-only).
  - `Profile B — win-rtx3080`: `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2` via LM Studio with `gpu_offload=40`, `context 16384`.
  - These hardware profiles are the authoritative reason `qwen3.5-9b-mlx`/MLX models must not be listed for Windows lanes.
- Canonical skill source: `bin/orama-system/skills/hermes-harness/commands/pt-orama-council/SKILL.md` (this file)
- Hermes Windows harness: `docs/wiki/15-hermes-windows-harness.md`
