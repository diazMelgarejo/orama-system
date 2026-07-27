# Skill Security Wording — Reference Card

> **Load when:** authoring or revising any `SKILL.md`, `references/*.md`, or
> skill script docstrings that will be scanned by CI (`aguara`) or read by
> other agents.

## Why this exists

Skill docs are **executable supply-chain material**, not passive documentation.

1. **Security scanners** (`aguara` in `agent-security` CI) pattern-match skill
   text for agent-hacking and supply-chain abuse. Some rules are
   **non-baselineable** — they always gate even when older findings are
   baselined.
2. **Naive agents** may treat strongly worded imperative commands in skill
   files as **literal runbook steps** and execute them without the human
   judgment the author assumed. That is an unintentional prompt-injection path:
   the skill becomes a remote-control script for whichever model reads it.

We deliberately **word skills so scanners can distinguish real attacks from
doc examples**, and so models are steered toward **review-before-run** instead
of copy-paste execution. The aguara baseline then filters legacy noise while
**new** gating patterns still fail CI.

**Do not** weaken the scanner to pass CI. **Do** fix wording — including in
this reference card (it is scanned too).

## Pre-flight (after edits)

```bash
aguara scan bin/orama-system/skills \
  --ci \
  --baseline config/agent-security/aguara-skills.baseline.json \
  --disable-rule TOXIC_CROSS_002

# Explain any new gating rule:
aguara explain <RULE_ID>
```

Regenerate baseline only after intentional, reviewed changes:

```bash
aguara scan bin/orama-system/skills \
  --write-baseline config/agent-security/aguara-skills.baseline.json \
  --disable-rule TOXIC_CROSS_002
```

## Core doctrine

| Principle | Do | Avoid |
|-----------|----|-------|
| **Describe, don’t command** | Register server X in the MCP client UI; launch command is a pinned `npx` invocation | Imperative MCP CLI auto-register one-liners in fenced blocks |
| **Env vars, not dotenv paths** | `OPENROUTER_API_KEY` must be set (run setup script) | Sourcing dotenv paths in the same example as HTTP POST |
| **No shell-profile surgery in prose** | Wires into existing login profiles when present | Instructions to append or redirect into zsh/bash rc files |
| **No CI-conditioned danger** | Skip auth-required canaries | CI environment tokens in comments on subprocess-using scripts |
| **No LAN literals in tracked docs** | `$LM_STUDIO_WIN_ENDPOINT`, `<win-host>` | Private LAN octets in markdown |
| **No remote pipe-to-shell** | Link to vetted installer script path; pin versions | Remote download piped straight into a shell |

When a real command is necessary, gate it explicitly in the skill body:
**verify source → pin version → operator approval → then run**.

## Rule-specific wording patterns

Patterns below come from **orama PR #222 / agent-security CI** (2026-07-27).
Use `aguara explain <RULE_ID>` for live regex detail.

### EXTDL_006 — MCP server auto-registration (HIGH, non-baselineable)

**Anti-pattern:** fenced blocks that tell the reader to run an MCP client's
`add`/`install` subcommand with an `npx`/`node` launch line.

**Instead:** prose — “In the MCP client UI, register server *openclaw* with
launch command `npx -y openclaw mcp serve` (review package source first).”

### CRED_021 — Dotenv file exposure (HIGH, non-baselineable)

**Anti-pattern:** dotenv path literals in the same example block as HTTP POST,
upload, or forward language; JavaScript examples that use the dotted runtime-env
property token adjacent to `fetch` POST.

**Instead:** validate exported env var names only before HTTP; in JS examples
use bracket property access on the runtime env object (avoid the dotted env
token) and still validate keys before network I/O.

### EXTDL_005 — Shell profile modification (MEDIUM, non-baselineable)

**Anti-pattern:** “add/append/write” language paired with zshrc/bashrc paths.

**Instead:** “Wires env config into existing zsh/bash login profiles when those
files already exist.” Keep actual profile mutations inside reviewed setup scripts.

### SUPPLY_005 — Conditional CI execution (HIGH, non-baselineable)

**Anti-pattern:** `CI`, `GITHUB_ACTIONS`, or similar tokens in docstrings or
comments on Python files that import `subprocess`.

**Instead:** describe the flag purpose (“skip auth-required canaries”) without
naming CI environment variables.

### SUPPLY_003 / EXTDL_013 — remote pipe-to-shell (HIGH)

**Anti-pattern:** documenting remote curl (or wget) output piped into bash/sh.

**Instead:** named repo script, checksum, version pin, operator review.

### SSRF_002 / SSRF_008 — LAN and rebinding literals (HIGH)

Use env vars and redacted placeholders in tracked markdown. Real topology
belongs in gitignored local caches (local env files, `.local/lan-topology.json`).

## Anti-pattern: “literal command hoarding”

Strong imperatives in skills (`Run this now:`, `Always execute:`,
`You MUST run:`) increase the chance that:

- A smaller or less-aligned model executes without context.
- A scanner flags the text as supply-chain instruction.
- The baseline cannot separate **malicious** from **poorly worded benign** content.

Prefer:

- **Capability description** — what the operator achieves.
- **Guarded example** — preconditions, validation, failure modes.
- **Pointer to script** — setup script under `$ORAMA_ROOT` with “review first.”

## Worked example (CRED_021-safe curl block)

```bash
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "ERROR: OPENROUTER_API_KEY is unset; run setup-openrouter.sh" >&2
  exit 1
fi

curl -sS -X POST "${OPENROUTER_ENDPOINT}" \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-4o","messages":[{"role":"user","content":"ping"}]}'
```

## Related

- [`modular-skill-authoring.md`](modular-skill-authoring.md) — workflow and validation
- [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md) — LINT-013/014/015/016
- `config/agent-security/aguara-skills.baseline.json` — baselined legacy findings
- `scripts/ci/run_agent_security_scans.sh` — full CI bundle
