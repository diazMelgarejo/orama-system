# Append-Only PR Body — Reference Card

> **Layer 0 first:** `.cursor/rules/pr-body-comment-only.mdc` — agents **comment only** by default.
> Load this card after the operator minted **operator-grant-v2** via `grant-pr-body-human-override.sh`.

## Layer 0 — comment only (default)

| Do | Never (automatic) |
| -- | ----------------- |
| `ManagePullRequest post_comment` | `update_pr` with `body=` |
| `gh pr comment` | `gh pr edit`, `append-pr-body.sh` without grant v2 |

Hooks: `pr-body-guard-core.py` + `beforeSubmitPrompt` reminder.

## Operator grant v2 (before append)

| Step | Command / artifact |
| ---- | ------------------ |
| Mint (operator TTY) | `bash scripts/cursor/grant-pr-body-human-override.sh owner/repo N --file follow.md` |
| Ack file | `~/.cursor/pr-body-human-override-ack` — `operator-grant-v2` + HMAC `token` |
| Digest bind | Same `--file` or `--message` for mint and append |
| Reject | `operator-grant-v1`, `CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK` env |

**Not human identity:** same-user Keychain HMAC is escalation control; agents with PTY can
still read secrets. v2.1: security-sentinel passkey orbit.

### Append replay state machine

```text
append-pr-body.sh:
  verify → reconcile? → reserve → READ BACKUP MERGE → gh pr edit → mark-applied → consume
```

Grant lib CLI: `mint | verify | reserve | mark-applied | consume | reconcile | release`

Canonical payload bytes:

```text
grant-v2|repo|pr|nonce|issued_at|action|content_digest
```

Tests: `GH_BIN` points to fake `gh` in `tests/test_append_pr_body_grant_flow.py`.

## Delimiters (do not put in append content)

| Marker | Role |
| ------ | ---- |
| `<!-- CURSOR_AGENT_PR_BODY_BEGIN -->` | Start of Cursor agent summary zone |
| `<!-- CURSOR_AGENT_PR_BODY_END -->` | Insertion point for new follow-ups (preferred) |
| `<!-- This is an auto-generated comment: release notes by coderabbit.ai -->` | Fallback insertion point — preserve block below |

## Backup path convention

```text
.git/pr-body-backups/<owner>-<repo>-pr<N>-<YYYYMMDD>T<HHMMSS>Z.<random>
```

Example: `.git/pr-body-backups/diazMelgarejo-orama-system-pr245-20260730T150925Z.O4vNyK`

If `gh pr edit` fails with `Resource not accessible by integration`, save merged body as:

```text
.git/pr-body-backups/pr<N>-merged-pending.md
```

and hand off to the operator or retry with a token that has `updatePullRequest`.

## Layer 7 — Cursor runtime hooks (agents only)

Installed by `bash scripts/cursor/install-user-git-environment.sh` into `~/.cursor/hooks.json`:

| Event | Script | Blocks |
| ----- | ------ | ------ |
| `beforeMCPExecution` | `before-mcp-pr-body-guard.sh` | `ManagePullRequest update_pr` with `body=` |
| `beforeShellExecution` | `before-shell-pr-body-guard.sh` | `gh pr edit --body` (inline; `--body-file` OK) |

Both hooks use `pr_body_run_guard()` → verify grant + emit `BACKUP|repo|pr` on valid append segment.

## Worked example — stack harmonization follow-up

**follow-up.md** (content only — no delimiters):

```markdown
**Stack harmonization (rebased onto #244 @ `4b6e5493`):**

- Branch rebased onto `cursor/aguara-cred021-fleet-docs-f559` so CI inherits upstream fixes.
- Unique commit preserved: `check_no_pending_merge.sh` pre-push guard.

**Verified locally:** aguara `--ci` reports `0 gating` on rebased tip.
```

**Operator mint** then **append** (matching `--file`):

```bash
bash scripts/cursor/grant-pr-body-human-override.sh diazMelgarejo/orama-system 245 \
  --file follow-up.md
bash scripts/cursor/append-pr-body.sh diazMelgarejo/orama-system 245 \
  --title "Follow-up: harmonized onto #244" \
  --file follow-up.md
```

## ManagePullRequest update_pr (agent-managed PRs)

Pass the **full merged body** as raw markdown:

- Include original Summary
- Include all `## Follow-up:` blocks
- Include CodeRabbit release notes section unchanged
- **Exclude** `CURSOR_AGENT_PR_BODY_BEGIN/END` — the tool adds agent zone wrappers
- **Exclude** Open-in-Web / Open-in-Cursor footer HTML — tool rejects managed images

## Manual merge (when script unavailable)

1. Copy current body from `gh pr view` into backup file
2. Insert before `CURSOR_AGENT_PR_BODY_END` or CodeRabbit marker:

```markdown

## Follow-up: <title>

<append content>
```

1. Operator mints grant; operator or agent runs `append-pr-body.sh` (not raw `gh pr edit` from agents)

## Failure modes

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| Original Summary gone | Delta-only `body=` write | Restore from `.git/pr-body-backups/`; re-append correctly |
| `operator-grant-v1` rejected | Stale ack | Re-mint v2 with same append bytes |
| `content-digest mismatch` | Changed follow-up after mint | Re-grant with current file/message |
| `grant consume blocked` | Consume before remote success | Re-run append; reconcile if body already updated |
| `not agent-managed` | Human-authored PR body | Operator runs `append-pr-body.sh` locally |
| `Resource not accessible by integration` | Token lacks GraphQL update | Operator runs `append-pr-body.sh` locally |
| `body changed since initial read` | Concurrent edit | Re-fetch, re-merge, retry |
| CodeRabbit section duplicated | Inserted below CodeRabbit marker | Move follow-up above marker; restore bot section once |

## Cross-references

- `scripts/cursor/pr-body-grant-lib.py` — HMAC mint/verify/replay ledger
- `scripts/cursor/append-pr-body.sh` — implementation
- `.cursor/rules/append-only-pr-body.mdc` — always-on Cursor rule
- `.cursor/commands/pr.md` § Phase 4 — create vs update
- `bin/orama-system/cidf/references/integrative-editing-examples.md` §1 — good/bad table
- `docs/wiki/12-cursor-cloud-commit-attribution.md` § PR body updates
- `docs/plans/2026-08-02-pr-body-grant-security-remediation.md` — remediation record
