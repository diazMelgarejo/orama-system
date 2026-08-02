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

## 2026-08-02 — PR-body human grant security gap (PR #255) — EXA deep pass

Task: Replace TTY/file-marker grant with non-forgeable human authorization.
Branch: `2026-07-31-010-remediation-doctrine-phase6-sync` (PR #255)
Research: `bin/orama-system/references/pr-body-human-grant-security-gap-research.md`
(EXA 6 queries + Firecrawl 15 scrapes; thorough depth)
Files in scope (next implementation PR):

- `scripts/cursor/grant-pr-body-human-override.sh`
- `scripts/cursor/hooks/pr-body-guard-core.py`
- `.claude/hookify.pr-body-append-only.local.md`
- `.cursor/rules/pr-body-comment-only.mdc`

Tests run: none (research-only commits)

Open risks:

- TTY gate `! -t 0 && ! -t 1` — agent PTY passes; omamori #319 class bypass without `-t`
- Forgeable `~/.cursor/pr-body-human-override-ack` (Vallum PR #32 / hashgate precedent)
- LITL UI deception (OWASP + Checkmarx) separate from forged state

Next (ordered):

1. Phase A — honest docs; strip agent-copyable override from rules (CodeRabbit)
2. Phase B — strict TTY `||` gate + repo/pr/nonce on ack
   (defense-in-depth only)
3. Phase C — pick pattern from EXA catalog:
   - **Vallum** HMAC per-command (hook-minted, machine secret outside agent env)
   - **hashgate** hash-bound integrative body preview
   - **GoodRoom** passkey + Ed25519 JWKS on action hash (rare operator edits)
   - **Invariant** MCP proxy deny on `update_pr` body
   - **HumanLayer** external approval API
   - Cursor/Claude framework approval when
     [#38299](https://github.com/anthropics/claude-code/issues/38299) lands
4. OWASP cheat sheet §4 HITL + tool authorization middleware alignment
5. Phase D tests — prove forge works today; fails after Phase C
Refs: arXiv 2606.02668 consent integrity; AgentPatterns provenance markers;
OWASP AI Agent Security Cheat Sheet; GoodRoom MCP passkey post.
Implementation plan: `docs/plans/2026-08-02-pr-body-grant-security-remediation.md`
(v2.1 sentinel: `docs/v2/51-security-sentinel-orbit-passkey-mcp.md`).
Do not push until operator reviews PR #255 stack.
