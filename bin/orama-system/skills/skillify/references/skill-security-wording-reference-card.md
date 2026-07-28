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

We deliberately **word production skills safely** so scanners can baseline
legacy noise while **new** attack-shaped text still fails CI — and so models
are steered toward **review-before-run** instead of copy-paste execution.

## The teaching paradox (and how we resolve it)

You **can** teach the negative rule. You **cannot** embed literal attack-shaped
commands in production skill files without the same risks you are warning about.

| Layer | Location | Content | aguara |
|-------|----------|---------|--------|
| **Doctrine** | this reference card | Principles, safe patterns, `aguara explain` pointers | scanned; no literal bad examples |
| **Curriculum** | [`../examples/bad/security-wording-anti-patterns.md`](../examples/bad/security-wording-anti-patterns.md) | Literal bad → good pairs | bad lines use `<!-- aguara-ignore-next-line -->` |
| **Production** | `SKILL.md`, operator references | Good patterns only | must pass `--ci` with 0 gating |

**Meta-lesson:** scanners and naive agents share one constraint — *executable
text is treated as executable*. We do not weaken CI or hide behind euphemism.
We **quarantine** negative examples in the teaching corpus with explicit inline
ignore directives, the same way antivirus uses labeled vaccine samples.

**Do not** copy ignored bad lines from the curriculum into `SKILL.md`.

## Pre-flight (after edits)

```bash
aguara scan bin/orama-system/skills \
  --ci \
  --baseline config/agent-security/aguara-skills.baseline.json \
  --disable-rule TOXIC_CROSS_002

aguara explain <RULE_ID>
```

Regenerate baseline only after intentional, reviewed changes:

```bash
aguara scan bin/orama-system/skills \
  --write-baseline config/agent-security/aguara-skills.baseline.json \
  --disable-rule TOXIC_CROSS_002
```

## Core doctrine (production skills)

| Principle | Do | Avoid |
|-----------|----|-------|
| **Describe, don’t command** | Register server X in the MCP client UI; launch command is a pinned `npx` invocation | Imperative MCP CLI auto-register one-liners in fenced blocks |
| **Env vars, not dotenv paths** | `OPENROUTER_API_KEY` must be set (run setup script) | Sourcing dotenv paths in the same example as HTTP POST |
| **No shell-profile surgery in prose** | Wires into existing login profiles when present | Instructions to append or redirect into zsh/bash rc files |
| **No CI-conditioned danger** | Skip auth-required canaries | CI environment tokens in comments on subprocess-using scripts |
| **No LAN literals in tracked docs** | `$LM_STUDIO_WIN_ENDPOINT`, `<win-host>` | Private LAN octets in markdown |
| **No remote pipe-to-shell** | Link to vetted installer script path; pin versions | Remote download piped straight into a shell |

When a real command is necessary, gate it explicitly:
**verify source → pin version → operator approval → then run**.

## Rule index (detail via `aguara explain`)

| Rule | Topic | Curriculum section |
|------|-------|-------------------|
| EXTDL_006 | MCP auto-registration | [anti-patterns § EXTDL_006](../examples/bad/security-wording-anti-patterns.md#extdl_006--mcp-auto-registration) |
| CRED_021 | Dotenv + outbound HTTP | [anti-patterns § CRED_021](../examples/bad/security-wording-anti-patterns.md#cred_021--dotenv--outbound-http) |
| EXTDL_005 | Shell profile modification | [anti-patterns § EXTDL_005](../examples/bad/security-wording-anti-patterns.md#extdl_005--shell-profile-modification) |
| SUPPLY_005 | CI token + subprocess | [anti-patterns § SUPPLY_005](../examples/bad/security-wording-anti-patterns.md#supply_005--ci-token--subprocess-file) |
| SUPPLY_003 / EXTDL_013 | curl pipe to shell | [anti-patterns § SUPPLY_003](../examples/bad/security-wording-anti-patterns.md#supply_003--extdl_013--curl-pipe-to-shell) |
| SSRF_002 | LAN literals | [anti-patterns § SSRF_002](../examples/bad/security-wording-anti-patterns.md#ssrf_002--lan-literals-in-tracked-docs) |

## Anti-pattern: “literal command hoarding”

Strong imperatives (`Run this now:`, `Always execute:`, `You MUST run:`) increase
the chance that a smaller model executes without context and that scanners flag
the text as supply-chain instruction.

Prefer capability description, guarded examples, and pointers to reviewed scripts.

## Worked example (production-safe curl block)

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
- [`../examples/bad/security-wording-anti-patterns.md`](../examples/bad/security-wording-anti-patterns.md) — literal bad/good curriculum
- [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md) — LINT-013/014/015/016
- `config/agent-security/aguara-skills.baseline.json` — baselined legacy findings
- `scripts/ci/run_agent_security_scans.sh` — full CI bundle
