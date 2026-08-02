---
name: cursor-pr-body
description: >-
  Layer 0 comment-only PR updates for Cursor agents — post_comment/gh pr comment
  only, never auto-change PR descriptions. After operator mints operator-grant-v2
  (HMAC + digest binding), append-pr-body.sh is the only allowed write path.
  Triggers on: update PR body, ManagePullRequest update_pr, gh pr edit, append-pr-body,
  PR summary, post_comment, PR harmonization notes, operator grant, grant replay.
version: 1.3.0
license: Apache 2.0
compatibility: cursor, claude-code, codex, openclaw, hermes-harness, orama-system
parent_skill: orama-system
triggers:
  - update pr body
  - append pr body
  - post_comment
  - pr comment only
  - ManagePullRequest update_pr
  - gh pr edit
  - harmonize pr
  - append-pr-body
  - operator grant
  - operator-grant-v2
  - pr-body-grant
allowed-tools: Bash(gh pr comment *), Bash(gh pr view *)
---

# Cursor PR Body — Comment-Only + Append-Only

> **Layer 0 rule:** `.cursor/rules/pr-body-comment-only.mdc` (alwaysApply)  
> **Layers 1–6:** `.cursor/rules/append-only-pr-body.mdc` (operator grant only)  
> **Grant lib:** `scripts/cursor/pr-body-grant-lib.py` (mint, verify, reserve, mark-applied, consume, reconcile)  
> **Operator mint:** `scripts/cursor/grant-pr-body-human-override.sh` (TTY + not agent/CI)  
> **Write:** `scripts/cursor/append-pr-body.sh` (only authorized body-write path; `GH_BIN` for tests)

## Layer 0 — Default for Cursor agents

**Do not change PR descriptions automatically.** Use comments only:

| Tool | Action |
| ---- | ------ |
| `ManagePullRequest` | `post_comment` only — never `update_pr` with `body=` |
| `gh` | `gh pr comment` only — never `gh pr edit` or direct body API calls |

Hooks enforce this at `preToolUse`, `beforeMCPExecution`, `beforeShellExecution`, and
`beforeSubmitPrompt`. You cannot bypass by choosing a different tool.

## Operator grant v2 (explicit authorization)

`operator-grant-v1` plaintext ack and `CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK` env exports are
**rejected**. Authorization is an **HMAC-authenticated capability** in
`~/.cursor/pr-body-human-override-ack` (`operator-grant-v2`), not proof that a human is
present.

**Same-user residual risk:** Keychain HMAC on macOS is **escalation control** — an agent
shell running as the operator user can still read the secret or ack file. WebAuthn/MCP
approval is deferred to v2.1 security-sentinel ([`docs/v2/51-security-sentinel-orbit-passkey-mcp.md`](../../../../docs/v2/51-security-sentinel-orbit-passkey-mcp.md)).

### Operator workflow

```bash
# Operator terminal only (strict TTY; denies CURSOR_AGENT and CI)
bash scripts/cursor/grant-pr-body-human-override.sh owner/repo N --file follow-up.md
```

Grant and append must use the **same** `--file` or `--message` (content-digest binding).

### Agent workflow (after operator mint)

```bash
bash scripts/cursor/append-pr-body.sh owner/repo N \
  --title "Follow-up: <short title>" \
  --file follow-up.md
```

Direct `update_pr`, `gh pr edit --body-file`, and `gh api` body mutations remain
**denied** even with a grant.

### Replay state machine (append-pr-body.sh)

```text
verify grant → reconcile? (crash recovery) → reserve nonce
  → READ → BACKUP → MERGE → gh pr edit → mark-applied → consume
```

- **Never** consume the nonce before remote `gh pr edit` succeeds.
- On edit failure after `reserve`, reservation is **released**.
- **Reconcile:** if follow-up block is already on remote, `reconcile` consumes without duplicate edit.

Canonical HMAC payload (fixed UTF-8 field order, pipe-delimited, no trailing newline):

```text
grant-v2|{repo}|{pr_number}|{nonce}|{issued_at}|{action}|{content_digest}
```

Hooks call `pr-body-guard-core.py` to verify grant per append segment and emit
`BACKUP|repo|pr` for preflight READ snapshots (`pr_body_run_guard` in backup-lib).

## Append-only workflow (Layers 1–6)

```text
READ  →  BACKUP  →  MERGE (append-only)  →  WRITE (full merged body)
```

## Forbidden (always)

| Bad | Why |
| --- | --- |
| Turn-end `update_pr` with latest delta | Clobbered 5+ PRs — comment instead |
| Any automatic body edit without operator grant v2 | Layer 0 violation |
| `gh pr edit` / `gh api` after grant | Grant permits append-pr-body.sh only |
| Delta-only body even with grant | Layers 1–6 violation |
| Forge v1 ack or env override exports | Fail-closed; use operator-grant-v2 |
| Run grant script from agent shell | Operator mint only |

## Verification

```bash
python3 -m pytest tests/test_pr_body_grant_lib.py \
  tests/test_append_pr_body_grant_flow.py tests/test_pr_body_guard_core.py -q
```

## References

- [`references/append-only-workflow-reference-card.md`](references/append-only-workflow-reference-card.md)
- [`../../references/pr-body-anti-clobber-incident-ledger.md`](../../references/pr-body-anti-clobber-incident-ledger.md)
- [`../../references/pr-body-human-grant-security-gap-research.md`](../../references/pr-body-human-grant-security-gap-research.md)
- [`../../../../docs/plans/2026-08-02-pr-body-grant-security-remediation.md`](../../../../docs/plans/2026-08-02-pr-body-grant-security-remediation.md)
