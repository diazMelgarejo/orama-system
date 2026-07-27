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

**Do not** “fix” CI by weakening the scanner. **Do** fix wording.

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
| **Describe, don’t command** | “Register server X in the MCP client UI with command `npx …`” | `claude mcp add X -- npx …` in a fenced block |
| **Env vars, not dotenv paths** | “`OPENROUTER_API_KEY` must be set (run setup script)” | `source ~/.openclaw/.env.openrouter` next to `curl -X POST` |
| **No shell-profile surgery in prose** | “Wires into existing login profiles when present” | “Append to `~/.zshrc`” / `>> ~/.bashrc` |
| **No CI-conditioned danger** | “Skip auth-required canaries” | `# CI / no-auth` in a file that imports `subprocess` |
| **No LAN literals in tracked docs** | `$LM_STUDIO_WIN_ENDPOINT`, `<win-host>` | `192.168.x.x` in markdown |
| **No remote pipe-to-shell** | Link to vetted installer script path; pin versions | `curl … \| bash` |

When a real command is necessary, gate it explicitly in the skill body:
**verify source → pin version → operator approval → then run**.

## Rule-specific wording patterns

Patterns below come from **orama PR #222 / agent-security CI** (2026-07-27).
Use `aguara explain <RULE_ID>` if the rule text drifts.

### EXTDL_006 — MCP server auto-registration (HIGH, non-baselineable)

**Trigger:** `claude mcp add …`, `cline mcp install … -- npx`, etc.

```text
# Bad — reads as auto-register instruction
cline mcp install openclaw -- npx -y openclaw mcp serve

# Good — prose + separated launch command
# In Cline MCP client UI: server "openclaw", launch command `npx -y openclaw mcp serve`
```

### CRED_021 — Dotenv file exposure (HIGH, non-baselineable)

**Trigger:** `.env` substring (including `process.env`) **near** send/post/upload/forward.

```text
# Bad — .env + POST in same example block
source ~/.openclaw/.env.openrouter
curl -X POST "$OPENROUTER_ENDPOINT" ...

# Good — env var names only; validate before HTTP
if [ -z "${OPENROUTER_API_KEY:-}" ]; then exit 1; fi
curl -X POST "$OPENROUTER_ENDPOINT" ...
```

```javascript
// Bad
const k = process.env.OPENROUTER_API_KEY;
await fetch(url, { method: 'POST', ... });

// Good — bracket access avoids .env token; still validate
const env = process['env'];
const k = env.OPENROUTER_API_KEY;
```

In numbered lists, refer to “runtime env file under `~/.openclaw/`” instead of
filenames containing `.env`.

### EXTDL_005 — Shell profile modification (MEDIUM, non-baselineable)

**Trigger:** add/append/write + `~/.zshrc` / `~/.bashrc`.

```text
# Bad
4. Add sourcing to `~/.zshrc` and `~/.bashrc`

# Good
4. Wires env config into existing zsh/bash login profiles when those files exist
```

Keep real profile writes inside **reviewed setup scripts**, not skill markdown.

### SUPPLY_005 — Conditional CI execution (HIGH, non-baselineable)

**Trigger:** `CI` / `GITHUB_ACTIONS` tokens in comments/docstrings combined with
`subprocess` / `os.system` patterns in the same file.

```text
# Bad (docstring line in a subprocess-using script)
python verify_partner_canaries.py --skip-hermes  # CI / no-auth

# Good
python verify_partner_canaries.py --skip-hermes  # skip auth-required canaries
```

### SUPPLY_003 / EXTDL_013 — curl | bash (HIGH)

**Trigger:** remote download piped to shell.

Prefer: named repo script, checksum, version pin, or “download and inspect
before run.” Never document one-liner pipe-to-shell in skills.

### SSRF_002 / SSRF_008 — LAN and rebinding literals (HIGH)

Use env vars and redacted placeholders in tracked markdown. Real topology
belongs in gitignored local caches (`.env.local`, `.local/lan-topology.json`).

## Anti-pattern: “literal command hoarding”

Strong imperatives in skills (`Run this now:`, `Always execute:`,
`You MUST run:`) increase the chance that:

- A smaller or less-aligned model executes without context.
- A scanner flags the text as supply-chain instruction.
- The baseline cannot separate **malicious** from **poorly worded benign** content.

Prefer:

- **Capability description** — what the operator achieves.
- **Guarded example** — preconditions, validation, failure modes.
- **Pointer to script** — `bash $ORAMA_ROOT/.../setup-foo.sh` with “review first.”

## Related

- [`modular-skill-authoring.md`](modular-skill-authoring.md) — workflow and validation
- [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md) — LINT-013/014/015
- `config/agent-security/aguara-skills.baseline.json` — baselined legacy findings
- `scripts/ci/run_agent_security_scans.sh` — full CI bundle
