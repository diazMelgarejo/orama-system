# Working Memory Template

Use this file only for sanitized, repo-local Antigravity notes. Do not store
secrets, personal memory, raw Hermes exports, or machine-specific absolute
paths here.

Recommended entry shape:

```text
Task:
Branch:
Files in scope:
Tests run:
Open risks:
```

Commit durable lessons to `docs/LESSONS.md` instead.

## 2026-07-08 - Cline Instances (session context)

4 Cline processes active: main (PID 51484, 66.8% CPU), hub daemon (PID 44584),
MCP bridge (PID 71165, from Claude Code 0a13d9d5), CLI launcher (PID 51483, zsh).
cline-agent allowlisted but not dispatched.

## 2026-08-02 — PR-body human grant security gap (PR #255)

Task: Replace TTY/file-marker grant with non-forgeable human authorization.
Branch: `2026-07-31-010-remediation-doctrine-phase6-sync` (PR #255)
Research: `bin/orama-system/references/pr-body-human-grant-security-gap-research.md`
Files in scope (next implementation PR):
- `scripts/cursor/grant-pr-body-human-override.sh`
- `scripts/cursor/hooks/pr-body-guard-core.py`
- `.claude/hookify.pr-body-append-only.local.md`
- `.cursor/rules/pr-body-comment-only.mdc`
Tests run: none (research-only commit)
Open risks:
- Grant script TTY gate uses `! -t 0 && ! -t 1` (agent TTY passes)
- `_human_override_active()` trusts forgeable `~/.cursor/pr-body-human-override-ack`
- LITL class: misleading HITL UI (Checkmarx) + forgeable ack (local)
Next (ordered):
1. Phase A docs — honest grant semantics; strip agent-copyable override commands from rules
2. Phase B — fix TTY logic; bind grant to repo/pr/nonce (defense-in-depth only)
3. Phase C — signed capability OR host-framework approval signal (CodeRabbit 4835288649)
4. Evaluate HumanLayer approval API vs Invariant guardrails proxy for MCP/gh path
5. Phase D tests — agent can forge today; must fail after Phase C
Do not push until operator reviews PR #255 stack.
