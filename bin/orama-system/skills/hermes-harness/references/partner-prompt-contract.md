# Partner Prompt Contract

> **Source:** `ecc-hermes-cross-harness.md` § Partner Prompt Contract  
> **Role:** bounded worker contract for Hermes, AGY, Codex CLI, and LM Studio partners  
> **Size contract:** ≤150 lines.

---

## Prompt Shape (copy-paste template)

```
ROLE: coding partner for PT-orama
GOAL: <specific, single outcome — one task per call>
CONSTRAINTS:
  - do not commit, deploy, delete, or change account settings
  - do not reveal or request secrets
  - do not import raw Hermes / OpenClaw local state
  - do not invent model names — only use IDs returned by /v1/models
  - cite files, tests, and line numbers used as evidence
OUTPUT (structured):
  assumptions:        <what you took as given>
  findings:           <what you observed, with citations>
  proposed_actions:   <specific edits or commands>
  tests:              <how to verify correctness>
  risks:              <what could go wrong>
  handoff_notes:      <what the main agent needs to decide>
```

The main orama agent owns **final synthesis, CIDF write discipline, and merge readiness**.
No partner lane has veto authority or autonomous write access.

---

## Per-Partner Invocation Flags

| Partner | One-shot flag | Non-TTY flag | Notes |
|---|---|---|---|
| Hermes | `--max-turns 1` | `--safe-mode` | Always specify `--provider` + `--model` explicitly |
| AGY | `--print` or `-p` | `--dangerously-skip-permissions` | Required to prevent silent hang in subagent context |
| Codex | `--print` | `--dangerously-skip-permissions` | Non-interactive; no TTY stall |
| LM Studio | HTTP POST to `/v1/chat/completions` | `--no-stream` | Must verify `/v1/models` first |

---

## Readiness Check Before Dispatch

Always run the partner's canary before sending it a bounded task:

```powershell
# Hermes
hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1

# AGY
agy --print "Reply with exactly: AGY_READY"

# Codex
codex --version

# LM Studio
Invoke-RestMethod -Uri "http://localhost:1234/v1/models"
```

If the canary fails → mark lane UNAVAILABLE → continue without it.
See full timeout + degraded-path table in `../SKILL.md` § Verification Gates.

---

## Output Validation

Before accepting a partner's `proposed_actions`:

1. Does every proposed edit cite a specific file + line?
2. Are all tests listed runnable right now (no stubs)?
3. Does the output contain any absolute paths or credentials? If yes, reject.
4. Does it propose a commit, deploy, or account change? If yes, reject.

---

## Related

- [`cross-harness-protocol.md`](cross-harness-protocol.md) — authority and harness boundaries
- [`ecc-migration-rules.md`](ecc-migration-rules.md) — what belongs in canonical vs local
- [`../SKILL.md`](../SKILL.md) § Verification Gates — canary table with timeouts
