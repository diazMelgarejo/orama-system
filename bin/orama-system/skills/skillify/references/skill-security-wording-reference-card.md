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
| ------- | ---------- | --------- | -------- |
| **Doctrine** | this reference card | Principles, safe patterns, `aguara explain` pointers | scanned; no literal bad examples |
| **Curriculum** | [`../examples/bad/security-wording-anti-patterns.md`](../examples/bad/security-wording-anti-patterns.md) | Literal bad → good pairs | bad lines use `<!-- aguara-ignore-next-line -->` |
| **Production** | `SKILL.md`, operator references | Good patterns only | must pass `--ci` with 0 gating |

**Meta-lesson:** scanners and naive agents share one constraint — *executable
text is treated as executable*. We do not weaken CI or hide behind euphemism.
We **quarantine** negative examples in the teaching corpus with explicit inline
ignore directives, the same way antivirus uses labeled vaccine samples.

**Do not** copy ignored bad lines from the curriculum into `SKILL.md`.

## How the `--ci` gate actually decides pass/fail

`--ci` is shorthand for `--fail-on high --format terminal --no-color`
(confirmed via `aguara scan --help`, not assumed). **The gate is a
HIGH-severity count, not a raw finding count or a raw gating count.**
`main` routinely carries 100+ MEDIUM/LOW gating findings (not yet
baselined) and still passes CI — do not assume "N gating findings, not
all baselined" means the job will fail. Before touching anything, check
the actual severity breakdown the scan prints (`HIGH`/`MEDIUM`/`LOW`
histogram near the top of the output): if there are zero HIGH findings,
CI is already green regardless of the MEDIUM/LOW count. Chasing MEDIUM/
LOW findings down to zero when only a HIGH finding is actually gating is
wasted, disproportionate effort — fix the HIGH finding(s) first, then
stop and re-check severity before doing anything else.

**Reproducing the exact CI result locally requires a CLEAN tree**, not
your working directory as-is: `aguara scan` walks the real filesystem
and does **not** respect `.gitignore`, so leftover gitignored scratch
directories (e.g. a prior `skillify` dogfood snapshot workspace) silently
inflate the local file/finding count above what CI's fresh checkout
actually sees. Export a clean tree first, then scan that:

```bash
# Any git ref works here -- HEAD, a stash, a branch, another remote's ref.
clean_dir=".aguara-clean-tree"
rm -rf -- "$clean_dir"
mkdir -p -- "$clean_dir"
git archive <ref> | tar -x -C "$clean_dir"
aguara scan "$clean_dir/bin/orama-system/skills" --ci \
  --baseline "$clean_dir/config/agent-security/aguara-skills.baseline.json" \
  --disable-rule TOXIC_CROSS_002
```

`git stash create "label"` (does not touch the working tree or stash
list) is the way to get a scannable ref for *uncommitted* changes.

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
| ----------- | ---- | ------- |
| **Describe, don’t command** | Register server X in the MCP client UI; launch command is a pinned `npx` invocation | Imperative MCP CLI auto-register one-liners in fenced blocks |
| **Env vars, not dotenv paths** | `OPENROUTER_API_KEY` must be set (run setup script) | Sourcing dotenv paths in the same example as HTTP POST |
| **No shell-profile surgery in prose** | Wires into existing login profiles when present | Instructions to append or redirect into zsh/bash rc files |
| **No CI-conditioned danger** | Skip auth-required canaries | CI environment tokens in comments on subprocess-using scripts |
| **No LAN literals in tracked docs** | `$LM_STUDIO_WIN_ENDPOINT`, `<win-host>` | Private LAN octets in markdown |
| **No remote pipe-to-shell** | Link to vetted installer script path; pin versions | Remote download piped straight into a shell |
| **Scope `allowed-tools`** | `Bash(git rev-parse *) Bash(path/to/entry-script.sh *)` — one entry per distinct top-level command the dispatcher body actually runs | Unscoped `bash`/`python`/`Bash` in `allowed-tools` (INDIRECT_010) |

When a real command is necessary, gate it explicitly:
**verify source → pin version → operator approval → then run**.

## Confirmed false positives (pattern-match, not real issues)

Real incidents, not hypotheticals (PT PR#355 review, 2026-09-12) — a bare
substring/word match fired on code and prose that documented *safe*
behavior, not an attack. This is doctrine tier, so the illustrative
before/after text lives in the curriculum, ignore-tagged, not here (an
earlier draft of this section reproduced the trigger text directly and
failed this file's own CI scan):

- [anti-patterns § CRED_021 — accidental substring collision](../examples/bad/security-wording-anti-patterns.md#cred_021--accidental-substring-collision-not-real-dotenv-exposure)
- [anti-patterns § SUPPLY_019 — safe-behavior prose using the trigger adjective](../examples/bad/security-wording-anti-patterns.md#supply_019--safe-behavior-prose-using-the-trigger-adjective)

**Verification discipline for any "false positive" claim**: `aguara
explain <RULE_ID>` prints the exact regex patterns — read them before
asserting a finding is spurious, and confirm the underlying code's real
behavior (grep the actual script), not just the doc's intent. A finding
that looks like noise but whose underlying code is genuinely unsafe is
not a false positive.

## Rule index (detail via `aguara explain`)

| Rule | Topic | Curriculum section |
| ------ | ------- | ------------------- |
| EXTDL_006 | MCP auto-registration | [anti-patterns § EXTDL_006](../examples/bad/security-wording-anti-patterns.md#extdl_006--mcp-auto-registration) |
| CRED_021 | Dotenv + outbound HTTP | [anti-patterns § CRED_021](../examples/bad/security-wording-anti-patterns.md#cred_021--dotenv--outbound-http) |
| EXTDL_005 | Shell profile modification | [anti-patterns § EXTDL_005](../examples/bad/security-wording-anti-patterns.md#extdl_005--shell-profile-modification) |
| SUPPLY_005 | CI token + subprocess | [anti-patterns § SUPPLY_005](../examples/bad/security-wording-anti-patterns.md#supply_005--ci-token--subprocess-file) |
| SUPPLY_003 / EXTDL_013 | curl pipe to shell | [anti-patterns § SUPPLY_003](../examples/bad/security-wording-anti-patterns.md#supply_003--extdl_013--curl-pipe-to-shell) |
| SSRF_002 | LAN literals | [anti-patterns § SSRF_002](../examples/bad/security-wording-anti-patterns.md#ssrf_002--lan-literals-in-tracked-docs) |
| INDIRECT_010 | Unscoped Bash in `allowed-tools` | see "Scope `allowed-tools`" row above and `aguara explain INDIRECT_010` |
| CRED_021 (2nd shape) | Accidental substring collision | [anti-patterns § CRED_021 accidental collision](../examples/bad/security-wording-anti-patterns.md#cred_021--accidental-substring-collision-not-real-dotenv-exposure) |
| SUPPLY_019 | Safe-behavior prose using the trigger word | [anti-patterns § SUPPLY_019](../examples/bad/security-wording-anti-patterns.md#supply_019--safe-behavior-prose-using-the-trigger-adjective) |

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
