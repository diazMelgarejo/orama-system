# 2026-07-07 — PR descriptions are append-only review artifacts

Agent: Claude
Scope: PR #141 skill standards repair, CodeRabbit review response, git attribution CI repair, PR body restoration

## Lesson

PR descriptions are historical review artifacts, not scratchpads. Preserve the original PR purpose, summary, non-goals, and validation instructions at the top. Add later commits and review responses only below as an append-only update log.

## What happened

During PR #141, the PR body was rewritten with only the latest repair summary. That removed the original PR purpose and useful context about the standards validator, Skillify references, roadmap, non-goals, and validation steps.

The correction restored the original PR description at the top and moved later updates into a chronological append-only section.

## Rules to apply next time

1. Do not replace an existing PR body with a latest-delta summary.
2. Preserve original purpose and scope unless the user explicitly changes the PR scope.
3. Append repair notes, review responses, CI fixes, and rebases below the original corpus.
4. Keep review-bot generated summaries as appendices, not as the only PR summary.
5. Apply the same additive/integrative habit to lessons and docs: preserve useful older context, then layer new context.

## Related anchors

- PR: https://github.com/diazMelgarejo/orama-system/pull/141
- Branch: `skillify-pr1-standards-validator-plan`
- PR body section: `Append-only update log`
- PT working-memory handoff: `.agent/memory/working/PR141_APPEND_ONLY_LESSON_2026-07-07.md`

## Why this is a companion file

`docs/LESSONS.md` is large. The connector returned truncated content for that file. A direct replacement through the GitHub contents API would risk deleting unseen historical lessons, which is exactly the anti-pattern this lesson warns against. This companion file preserves the lesson safely without clobbering the canonical lessons file.
