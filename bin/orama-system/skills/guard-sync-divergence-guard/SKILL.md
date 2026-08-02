---
name: guard-sync-divergence-guard
description: >-
  Fail-closed pre-sync guard for attribution-guard distribution. Scans workspace
  siblings before sync-attribution-guard-scripts.sh runs; aborts when a sibling
  carries guard mutations absent from orama canonical history. Safe when
  byte-identical or sibling only lags a canonical blob. Triggers on: guard sync,
  sync-attribution-guard-scripts, verify-guard-parity drift, sibling ahead of
  canonical, anti-clobber sync, GUARD_SYNC_E_DIVERGENCE, promote upstream before
  sync.
version: 1.0.0
license: Apache 2.0
compatibility: orama-system, cursor, claude-code, codex, openclaw
parent_skill: git-history-surgery
allowed-tools: bash, file-operations
---

# Guard Sync Divergence Guard

Internal orama development helper. Prevents the guard-sync epic failure mode:
blind `sync-attribution-guard-scripts.sh` overwriting a sibling's more advanced
mutations.

## When to load

- Before any `sync-attribution-guard-scripts.sh` invocation
- When `verify-guard-parity.sh` reports DRIFTED but sync "fixes" feel wrong
- When PT/AlphaClaw improved guards before orama absorbed them
- Pre-push on orama when manifest paths change (hook runs automatically)

## Quick check

```bash
bash scripts/git/check-guard-sync-divergence.sh --workspace
```

Optional explicit workspace (defaults to parent of repo root):

```bash
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$REPO_ROOT/..}" \
  bash scripts/git/check-guard-sync-divergence.sh --workspace
```

| Exit | Meaning |
| ---- | ------- |
| 0 | Safe to sync |
| 1 | `GUARD_SYNC_E_DIVERGENCE` — HITL required |
| 2 | Usage error |

## Safe vs blocked

| Sibling file vs canonical HEAD | Verdict |
| ------------------------------ | ------- |
| Byte-identical | Safe |
| Differs, sibling blob exists in canonical history | Safe (upgrade lagging copy) |
| Differs, sibling blob absent from canonical history | **Block** — promote sibling first |
| Canonical blob only in sibling history | **Block** — canonical is behind |

## HITL workflow (AskUserQuestions)

1. Identify failing `repo/path` from checker output.
2. Ask: commit sibling work? promote to orama canonical on the **one open PR**?
3. Merge/push orama canonical, then sync downstream — **never** open parallel guard PRs.
4. Re-run checker until PASS, then sync.

## Boundaries

Manifest includes the full `scripts/cursor/` grant stack (`pr-body-grant-lib.py`,
`append-pr-body.sh`, guard hooks, `pr-body-guard-core.py`) — sync after every orama
canonical grant remediation commit.

### Always Do

- Run divergence check before sync and after harmonizing guard edits.
- Reuse the single open PR per repo until the wave completes.
- Promote advanced sibling → orama before orama → downstream sync.

### Ask First

- `GUARD_SYNC_SKIP_DIVERGENCE_CHECK=1` (emergency only — document why).
- Changing manifest paths or checker semantics.

### Never Do

- Run sync to "fix" drift when siblings are ahead of canonical.
- Open one-file / one-commit PRs per guard file.
- Skip sibling scan because only one target repo is named.

## References

- [`references/divergence-check-reference-card.md`](references/divergence-check-reference-card.md)
  — algorithm, hooks, epic saga context
- [`../git-history-surgery/SKILL.md`](../git-history-surgery/SKILL.md) — tree-twin / re-anchor companion
- `scripts/git/check-guard-sync-divergence.sh` — implementation
- `scripts/git/guard-sync-manifest.sh` — path manifest
