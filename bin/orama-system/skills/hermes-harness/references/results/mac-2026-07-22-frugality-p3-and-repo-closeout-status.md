# Mac — 2026-07-22 P3 frugality/privacy close-out + repo hygiene status

**Job:** Claude main session (no coord-N fan-out ID — direct work)
**Branch:** `main` (both repos, direct commits with `ALLOW_MAIN_PUSH=1` override, user-confirmed)
**Status:** DONE (frugality gate + Dependabot + exa-path fixes), 1 PARTIAL (orama-system push hanging)

## What landed

- **P3 frugality/privacy single-gate architecture** — `orchestrator/gate.py`
  (new) wires `frugality_router.resolve_route()` as the canonical policy
  gate behind `ModelRegistry.route_task()` and `/orchestrate`'s
  `privacy_critical` branch. 29 new + 120 pre-existing + 1530 full-repo
  tests, independently re-verified. PT `13f09c42`.
- **Exa MCP path-resolution fix** (both repos) — replaced hardcoded
  `$HOME`-relative / workspace-mother-relative paths (which had silently drifted to
  an unrelated `npx mcp-remote` workaround in PT's `.codex/config.toml`)
  with a portable resolver: `orama-system/scripts/exa/resolve-orama-root.sh`
  and inline cache/walk/find bootstraps. orama `2cb1f0f0`, PT `fe66f46e`.
- **Dependabot fixes, all verified non-breaking:** orama `web/`
  brace-expansion 5.0.6→5.0.7 (HIGH, scoped pnpm override, lint verified
  clean) `f225f45a`; PT `local-agents`+`alphaclaw-mcp` body-parser→2.3.0
  (LOW×2, lockfile-only, tests+build verified) `1efe400f`.
- **Cross-repo closure ledger:** every plan surfaced this session now has
  a terminal disposition (implemented / superseded / deferred-to-v2 /
  retired) — see `orama-system/docs/plans/2026-07-22-cross-repo-out-of-
  scope-closure.md` and `references/tiered-model-implementation-
  navigator.md`.

## Open / needs a peer or human

- **orama-system push to `origin/main` is HANGING** — 2 prior pushes
  succeeded (`05eca1d9..c14a02e8`, `2cb1f0f0`, `f225f45a` all landed
  fine), but the latest retry has been stuck 90s+ with zero output (not
  even the pre-push hook's usual immediate banner) — looks like a real
  hang, not slowness. If any peer has push access and sees this before
  it resolves, worth a manual check (`git push origin main` from a clean
  shell) rather than assuming it's just queued.
- **Branch/worktree cleanup still needs a human hand:** `git branch -D`
  is blocked by this session's `dangerous-cmd-block` hook even for
  branches independently verified fully superseded (33 total across both
  repos). Script ready and dry-run-tested:
  workspace-mother `references/2026-07-22-branch-cleanup-verified-superseded.sh`.
  One worktree (`$PERPETUA_TOOLS_PATH/.claude/worktrees/pt-pr258-fixes-20260718`,
  on the confirmed-superseded `pr260-work` branch) is locked and also
  needs a human `git worktree remove --force` after unlocking.

## Not touched / explicitly deferred (per user's standing v2-migration directive)

Periscope L4 (52 open items), skill-upgrade-roadmap PR3-5, tri-repo-
alignment items #2/#3/#8, coordination-module-consolidation Part 2/3,
orama's optimization-priorities L6 schemas — all recorded with named
blocking/deferral reasons in the closure ledger above, not silently
dropped.
