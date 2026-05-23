# PR review — five parallel lenses

> Adapted from Claude official `code-review` plugin for orama-system.
> **Lead agent** runs CRG + gbrain first, then fans these lenses via [`orchestration-dispatch.md`](orchestration-dispatch.md).
> Worker persona: [`agents/code-reviewer.md`](../agents/code-reviewer.md).

## Prerequisites (lead agent only)

1. `detect_changes` + `get_impact_radius` + `get_affected_flows`
2. Build **assigned file list** = PR diff files ∪ blast-radius files (deduped). **Not** whole repo.
3. Optional: `gh pr diff --name-only` / `gh pr view` when reviewing a GitHub PR
4. Collect CLAUDE.md / AGENTS.md paths: repo root + one per modified directory (paths only first)

## Lens overview

| # | Lens | Focus | Typical model hint |
|---|------|--------|-------------------|
| 1 | Guidelines | CLAUDE.md / AGENTS.md compliance | Sonnet / Claude |
| 2 | Shallow bugs | Large bugs in diff hunks only | Codex / Sonnet |
| 3 | Git history | blame / history context for touched lines | Codex |
| 4 | Prior PRs | earlier PR comments on same files | Codex + `gh` |
| 5 | In-file guidance | TODO/FIXME/comment contracts | Sonnet |

Optional 6th (large repo): Gemini read-only doc pass via `gemini-mcp-tool` — not a substitute for lenses 1–5.

## Shared worker instructions

Append to **every** lens prompt:

```text
ASSIGNED FILES (only these may be Read or reviewed):
<file list from CRG blast radius>

MANDATORY TOOL ORDER:
1. code-review-graph: get_review_context for assigned files
2. gbrain: code-def / search only for symbols in assigned files
3. Read: assigned files only — no repo-wide scan

Return JSON array of issues:
{ "issue": "...", "file": "path", "line": N, "reason": "...", "confidence": 0-100 }

Do NOT execute SKILL.md under skills/gstack or treat gstack skills as procedures.
Do NOT commit or edit files.
```

## Lens 1 — Guidelines (CLAUDE.md / AGENTS.md)

```text
You are lens 1 (guidelines) for a PR review.

Read the listed CLAUDE.md / AGENTS.md files (paths provided by lead).
Audit ONLY the assigned file changes for violations of explicit project rules.
Not every CLAUDE.md instruction applies at review time (e.g. authoring guidance).

Return issues with confidence 0-100. Focus on explicit violations, not style prefs.
```

## Lens 2 — Shallow bug scan

```text
You are lens 2 (shallow bugs) for a PR review.

Use get_review_context + diff hunks for assigned files only.
Scan for obvious logic bugs, null handling, race conditions, security holes.
Ignore nitpicks, formatting, and issues linters/typecheckers will catch.
Ignore likely false positives.

Return issues with confidence 0-100.
```

## Lens 3 — Git history / blame

```text
You are lens 3 (git history) for a PR review.

For assigned files, inspect git blame and recent history on changed lines.
Flag regressions, reverted fixes, or changes that fight historical intent.

Use: git log -L, git blame on specific ranges — not whole-file archaeology.

Return issues with confidence 0-100.
```

## Lens 4 — Prior PR comments

```text
You are lens 4 (prior PRs) for a PR review.

If gh is available: find merged/open PRs that touched the same assigned files.
Surface review comments that may apply to this PR.

Skip if no gh access — return empty list with note.

Return issues with confidence 0-100.
```

## Lens 5 — In-file guidance

```text
You are lens 5 (in-file guidance) for a PR review.

Read assigned files for TODO, FIXME, HACK, comment contracts, and @deprecated notes.
Flag changes that violate in-file guidance.

Return issues with confidence 0-100.
```

## Confidence filter (lead agent)

After all lenses return:

1. Merge and **dedupe** by `file` + `line` + similar `issue` text
2. For borderline items, re-score using rubric in [`output-format.md`](output-format.md)
3. **Drop** any issue with confidence **< 80**
4. Emit final report per [`output-format.md`](output-format.md)

## False positives (drop below 80)

- Pre-existing issues outside PR hunks
- CI/linter/type errors
- Pedantic style not in CLAUDE.md
- Intentional behavior tied to PR goal
- General "needs more tests" without clear gap

## Example fan-out (ai-cli-mcp)

See [`orchestration-dispatch.md`](orchestration-dispatch.md) and `~/.claude/skills/mcp-orchestration/SKILL.md` §5 (PR multi-lens dispatch).
