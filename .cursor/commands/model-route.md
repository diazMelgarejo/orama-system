---
description: Recommend the harness default or an allowed alternative for the current task. Do not self-escalate.
---

# Model Route Command

Recommend a launch that follows
[Alexandria model-governance](https://github.com/oramasys/alexandria/blob/docs/mig-pack-ingest-20260925/docs/standards/model-governance.md)
(PR #1, tip `e7ee9db6`). Local pin: `docs/standards/model-governance.md`.

The harness decides the path. Do not assume Claude-only routing.

## Usage

`/model-route [task-description] [--budget low|med|high]`

`--budget` never authorizes Fable, high effort, fast mode, or non-planning
Opus. Those need an escalation token (S-AuthZ bearer + fresh signed HITL, ≤24h).
A harness-classified planning task may use Opus at medium or high without
per-use approval. Config flags and env vars are not a token.

## Routing Heuristic

- **Cursor / Grok Bot:** default `grok-4.7` at medium with fast off.
  Allowed: `composer-2.5` or `gpt-5.6-terra` (medium) with fast off. Never `auto` for agents.
  Never `grok-4.5` or `grok-4.6`.
- **Anthropic:** default `claude-sonnet-5-5` at medium.
  Planning Opus may use medium or high with harness classification.
  Non-planning Opus and Fable 5.1 need an escalation token
  (Fable also needs a hard budget cap).
- Fallback if the default cannot run: stay on the same path's
  allowed-ungated model, or report the gap. Do not escalate.

## Required Output

- recommended launch id + effort/fast
- harness path
- confidence level
- why this launch fits
- allowed-ungated fallback (not an escalated model)

## Arguments

$ARGUMENTS:

- `[task-description]` optional free-text
- `--budget low|med|high` optional (informational only; does not gate escalation)
